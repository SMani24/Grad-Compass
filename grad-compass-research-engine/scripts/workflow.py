"""Local, evidence-first applicant workflow. No model calls or document uploads."""
import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote as urlquote
from validate import ROOT, require, validate, verify_receipt

VERSION = 'workflow-1.1.0'
MAX_BYTES = 20 * 1024 * 1024

def encode(x):
    return (json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def uid():
    return str(uuid.uuid4())

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def opaque(value):
    require(re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', value) is not None, 'invalid logical identifier')
    return value

class Store:
    """Single-user storage adapter. Private roots are fixed; synthetic roots are explicit."""
    def __init__(self, root, synthetic=False):
        self.root = Path(root).absolute()
        self.synthetic = synthetic
        if not synthetic:
            require(self.root == ROOT/'private', 'unapproved private root')
        require(self.root.is_dir(), 'storage root must already exist')
        self.guard()
        for name in ('intake', 'profiles', 'reviews', 'cache', 'sources', 'candidates', 'frozen'):
            p = self.root/name
            if not p.exists(): p.mkdir(mode=0o700)
        self.guard()

    def guard(self):
        for p in (self.root, *self.root.parents):
            require(not p.is_symlink(), 'symlink storage ancestor')
        # The adjacent CV workspace has its own output policy. Validate only the
        # profile workflow's storage, while still checking every profile input
        # and output before any read or write.
        owned = ('intake', 'profiles', 'reviews', 'cache', 'sources', 'candidates', 'frozen')
        root_stat = self.root.lstat()
        require(stat.S_ISDIR(root_stat.st_mode) and root_stat.st_uid == os.getuid()
                and root_stat.st_mode & 0o077 == 0, 'storage root permissions must be owner-only')
        require(not any(n.startswith('system.posix_acl_') for n in os.listxattr(self.root)), 'unexpected ACL')
        paths = []
        for name in owned:
            path = self.root/name
            if path.exists() or path.is_symlink():
                require(not path.is_symlink(), 'symlink storage object')
                paths.append(path)
        for path in paths:
            for base, dirs, files in os.walk(path, followlinks=False):
                for p in [Path(base), *(Path(base)/n for n in dirs+files)]:
                    s = p.lstat()
                    require(not stat.S_ISLNK(s.st_mode), 'symlink storage object')
                    require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode), 'nonregular storage object')
                    require(s.st_uid == os.getuid() and s.st_mode & 0o077 == 0, 'storage permissions must be owner-only')
                    require(not stat.S_ISREG(s.st_mode) or s.st_nlink == 1, 'hard-linked storage object')
                    if not self.synthetic:
                        # Linux extended/default ACLs are additional grants beyond mode bits.
                        require(not any(n.startswith('system.posix_acl_') for n in os.listxattr(p)), 'unexpected ACL')
        if not self.synthetic:
            git = lambda args: subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, check=True).stdout
            require(not git(['ls-files', '--', 'private']), 'private objects tracked by Git')
            for probe in ('private/intake/.probe', 'private/profiles/nested/.probe'):
                git(['check-ignore', '-q', '--', probe])

    def path(self, rel):
        p = Path(rel)
        require(not p.is_absolute() and '..' not in p.parts, 'unsafe relative path')
        self.guard()
        result = self.root/p
        require(result.resolve().is_relative_to(self.root.resolve()), 'storage escape')
        return result

    def read(self, rel):
        p = self.path(rel)
        require(p.stat().st_size <= MAX_BYTES, 'input exceeds supported size')
        return p.read_bytes()

    def put(self, rel, raw, readonly=False):
        p = self.path(rel)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        if readonly: p.chmod(0o400)
        return p

    def load(self, rel):
        return json.loads(self.read(rel))

    def revision(self, rid):
        return self.load('profiles/'+opaque(rid)+'.json')


def text_units(raw, suffix):
    """Return locatable text; unsupported/scanned files never generate invented text."""
    if suffix.lower() not in ('.txt', '.md'):
        return [], 'unreadable', 'Unsupported format; supply UTF-8 text with verified source references.'
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        return [], 'unreadable', 'Unreadable encoding; supply a readable UTF-8 copy.'
    if not text.strip() or '\x00' in text:
        return [], 'unreadable', 'No usable text; supply a readable copy.'
    return text.splitlines(), 'readable', None


def normalize_markdown_whitespace(text):
    """Strip balanced inline marker pairs, then collapse whitespace; no semantic edits."""
    for marker, character in (('**', '*'), ('__', '_'), ('`', '`')):
        token = re.escape(marker)
        char = re.escape(character)
        # Adjacent marker runs and unmatched delimiters are retained literally.
        pattern = rf'(?<!{char}){token}(?!{char})([^\n{char}]+?){token}(?!{char})'
        text = re.sub(pattern, lambda match: match[1], text)
    return ' '.join(text.split())


def structured_fragment(value, field):
    """Catch obvious PDF line fragments in narrative experience/teaching claims."""
    narrative = {
        'experience.institution', 'experience.lab_affiliation', 'experience.role', 'experience.personal_work',
        'experience.leadership', 'experience.team_scope', 'experience.intern_supervision',
        'experience.leadership_selection', 'experience.team', 'teaching.course',
        'teaching.duties', 'teaching.selection', 'teaching.courses',
        'teaching.continuation',
    }
    if field not in narrative:
        return False
    words = value.strip().split()
    if not words:
        return True
    if field == 'experience.role' and len(words) > 8:
        return True
    if words[0].lower() in {'to', 'of', 'for', 'such', 'their', 'and', 'an'} and words[0][0].islower():
        return True
    return value.rstrip().endswith(',') or words[-1].lower().strip('.,;:') in {'for', 'of', 'and', 'the', 'to', 'with', 'in'}


def claim(subject, field, kind, value, evidence=None, rationale=None, action=None, related=None, cid=None):
    return dict(id=cid or uid(), subject_id=subject, field=field, kind=kind, value=value,
                context=None, evidence=evidence or [], related_claim_ids=related or [],
                rationale=rationale, next_action=action)


def build(store, manifest_name, parent_id=None):
    """Manifest observations are agent proposals, checked against exact source ranges."""
    manifest = store.load('intake/'+manifest_name)
    require(manifest['synthetic'] is store.synthetic, 'synthetic/private mismatch')
    parent = store.revision(parent_id) if parent_id else None
    if parent: require(parent['synthetic'] is store.synthetic, 'lineage mode mismatch')
    p = dict(schema_version='1.0.0', profile_id=parent['profile_id'] if parent else uid(),
             revision_id=uid(), parent_revision_id=parent_id, version_name='draft-'+uid(),
             status='draft', synthetic=store.synthetic, sources=[], claims=[], issues=[], approval=None)
    stats = dict(reused=0, parsed=0)
    mappings = {}
    sources_by_file = {}
    seen = set()
    derived_originals = {item.get('derived_from') for item in manifest['sources'] if item.get('derived_from')}
    authority_files = {c.get('authority_file') for c in manifest.get('corrections', []) if c.get('source_file')}
    def uncertain(subject, field, reason, action, kind='missing', evidence=None):
        c = claim(subject, field, 'unknown', None, evidence, reason, action)
        p['claims'].append(c)
        p['issues'].append(dict(id=uid(), kind=kind, claim_ids=[c['id']], detail=reason, next_action=action))
    for item in manifest['sources']:
        name = item['file']
        require(name not in seen, 'duplicate source file')
        seen.add(name)
        require(item['kind'] in ('document', 'clarification'), 'invalid source kind')
        raw = store.read('intake/'+name)
        content_hash = digest(raw)
        # Observations and format participate in the cache: corrected mappings invalidate only this source.
        key = digest(encode([VERSION, '1.0.0', name, content_hash, Path(name).suffix, item['kind'], item.get('observations', []), store.synthetic]))
        cache_rel = 'cache/'+key+'.json'
        if store.path(cache_rel).exists():
            parsed = store.load(cache_rel)
            stats['reused'] += 1
        else:
            lines, readability, limitation = text_units(raw, Path(name).suffix)
            sid = uid()
            source = dict(id=sid, kind=item['kind'], label=sid, sha256=content_hash,
                          readability=readability, captured_at=now(), synthetic=store.synthetic)
            parsed = dict(source=source, claims=[], limitation=limitation)
            for o in item.get('observations', []):
                require(readability == 'readable', 'cannot assert from unreadable source')
                line = o['line']
                require(type(line) is int and 1 <= line <= len(lines), 'invalid evidence line')
                end_line = o.get('end_line', line)
                require(type(end_line) is int and line <= end_line <= len(lines), 'invalid evidence end line')
                quote = o['quote']
                require(isinstance(quote, str) and quote.strip() and quote in '\n'.join(lines[line-1:end_line]), 'quote not present at locator')
                normalization = o.get('normalization')
                require(normalization in (None, 'markdown_whitespace'), 'unsupported normalization')
                checked_quote = normalize_markdown_whitespace(quote) if normalization else quote
                value = o['value']
                require(isinstance(value, str) and value.strip() and value in checked_quote, 'value must match verified quote text')
                require(not structured_fragment(value, o['field']), 'structured claim appears to be a sentence fragment')
                context = o.get('context')
                require(context is None or isinstance(context, str) and context.strip(), 'invalid observation context')
                if normalization:
                    context = ' '.join(filter(None, [context, 'Formatting normalization: markdown_whitespace; balanced inline markers removed and whitespace collapsed. Textual presence does not establish semantic entailment.']))
                field = o['field']
                choice = field.startswith(('preferences.', 'goals.'))
                require(not choice or item['kind'] == 'clarification', 'documents cannot establish preferences')
                kind = 'preference' if choice else ('documented_fact' if item['kind']=='document' else 'user_report')
                locator = 'line '+str(line) if line == end_line else f'lines {line}-{end_line}'
                evidence = [dict(source_id=sid, locator_kind='answer' if item['kind']=='clarification' else 'section', locator=locator)]
                extracted = claim(opaque(o['subject_id']), field, kind, value, evidence)
                extracted['context'] = context
                parsed['claims'].append(extracted)
            store.put('sources/'+sid+'.bin', raw, readonly=True)
            store.put(cache_rel, encode(parsed), readonly=True)
            stats['parsed'] += 1
        source = parsed['source']
        sources_by_file[name] = source
        p['sources'].append(source)
        mappings[source['id']] = dict(snapshot='sources/'+source['id']+'.bin', original='intake/'+name)
        if item.get('derived_from'):
            original = item['derived_from']
            require(original in seen and original != name, 'derived source must follow its original')
            require(Path(original).suffix.lower() == '.pdf' and Path(name).suffix.lower() == '.txt', 'unsupported source derivation')
            store.read('intake/'+original)
            mappings[source['id']]['derived_from'] = 'intake/'+original
        if item.get('transcription_of'):
            original = item['transcription_of']
            require(original in seen and original != name, 'transcription must follow its original')
            require(item['kind'] == 'clarification' and Path(name).suffix.lower() in ('.txt', '.md'), 'transcription must be a text clarification')
            store.read('intake/'+original)
            mappings[source['id']]['transcription_of'] = 'intake/'+original
        p['claims'].extend(parsed['claims'])
        if (parsed['limitation'] or not parsed['claims'] and name not in authority_files) and name not in derived_originals:
            uncertain(source['id'], 'sources.extraction', parsed['limitation'] or 'Readable source has no verified observations.',
                      'Review source locally and provide verified observations or a readable copy.',
                      'unreadable' if source['readability']=='unreadable' else 'ambiguous',
                      [dict(source_id=source['id'], locator_kind='unavailable', locator='No verified extraction')])
    # A manifest cannot silently omit documents from intake. Control JSON files live outside documents/.
    documents = store.root/'intake'/'documents'
    if documents.exists():
        inventory = {str(f.relative_to(store.root/'intake')) for f in documents.rglob('*') if f.is_file()}
        require(inventory <= seen, 'intake documents missing from manifest inventory')
    repeatable = {(opaque(x['subject_id']), x['field']) for x in manifest.get('repeatable_fields', [])}
    groups = {}
    for c in p['claims']:
        if c['kind'] != 'unknown': groups.setdefault((c['subject_id'], c['field']), []).append(c)
    for (subject, field), cs in groups.items():
        if (subject, field) not in repeatable and len({encode(c['value']) for c in cs}) > 1:
            c = claim(subject, field, 'conflict', None, rationale='Sources report different values.',
                      action='Clarify the competing evidence; preserve all alternatives until resolved.', related=[c['id'] for c in cs])
            p['claims'].append(c)
            p['issues'].append(dict(id=uid(), kind='conflict', claim_ids=[c['id']], detail=c['rationale'], next_action=c['next_action']))
    required_by_key = {}
    for required in manifest.get('required', []):
        required_by_key[(opaque(required['subject_id']), required['field'])] = required
    for required in required_by_key.values():
        key = (opaque(required['subject_id']), required['field'])
        if key not in groups:
            reason = required.get('rationale', 'No supplied evidence or explicit answer.')
            action = required.get('next_action', 'Provide evidence or an explicit answer; unknown is acceptable.')
            require(isinstance(reason, str) and reason.strip() and isinstance(action, str) and action.strip(), 'required gap needs rationale and next action')
            uncertain(*key, reason, action)
    if not p['claims']:
        uncertain('applicant', 'profile.evidence', 'No supplied claims.', 'Supply applicant evidence.')
    # Immutable record of resolved alternatives is the parent revision. A correction must cite a clarification.
    correction_targets = set()
    for correction in manifest.get('corrections', []):
        require(parent is not None, 'correction needs parent revision')
        subject, field = correction['subject_id'], correction['field']
        require((subject, field) not in correction_targets, 'duplicate correction target')
        correction_targets.add((subject, field))
        require(any(c['subject_id']==subject and c['field']==field for c in parent['claims']), 'correction target missing from parent')
        selection = correction.get('source_file')
        if selection:
            require(selection in sources_by_file and sources_by_file[selection]['kind']=='document', 'selection requires a manifest document')
            sid = sources_by_file[selection]['id']
            matches = [c for c in p['claims'] if c['subject_id']==subject and c['field']==field and c['kind']=='documented_fact' and c['value']==correction['value'] and any(r['source_id']==sid for r in c['evidence'])]
            authority = sources_by_file.get(correction.get('authority_file'))
            require(authority is not None and authority['kind']=='clarification', 'selection requires a manifest clarification authority')
            lines, readability, _ = text_units(store.read(mappings[authority['id']]['snapshot']), Path(correction['authority_file']).suffix)
            line, quote = correction['authority_line'], correction['authority_quote']
            require(readability=='readable' and type(line) is int and 1 <= line <= len(lines), 'invalid authority line')
            require(isinstance(quote, str) and quote.strip() and quote in lines[line-1], 'authority quote not present at locator')
        else:
            matches = [c for c in p['claims'] if c['subject_id']==subject and c['field']==field and c['kind'] in ('user_report','preference') and c['value']==correction['value']]
        require(len(matches)==1, 'correction requires one verified assertion')
        selected = matches[0]
        removed = {c['id'] for c in p['claims'] if c['subject_id']==subject and c['field']==field and c['id']!=selected['id']}
        p['claims'] = [c for c in p['claims'] if c['id'] not in removed]
        p['issues'] = [i for i in p['issues'] if not set(i['claim_ids']) & removed]
        selected['context'] = ' '.join(filter(None, [selected['context'], 'Human correction; prior evidence and alternatives retained in parent revision.']))
        if selection:
            choice = claim(subject, 'review.source_selection', 'user_report', quote,
                           [dict(source_id=authority['id'], locator_kind='answer', locator='line '+str(line))], related=[selected['id']])
            choice['context'] = f'Human selected the documented value for {field} from source {sid}. This records the clarification choice, not an independent documentary fact. Prior evidence and alternatives remain in the parent revision.'
            p['claims'].append(choice)
    validate(p)
    supersede_candidates(store, p['profile_id'])
    store.put('profiles/'+p['revision_id']+'.json', encode(p), readonly=True)
    store.put('profiles/'+p['revision_id']+'.manifest.json', encode(mappings), readonly=True)
    store.put('reviews/'+p['revision_id']+'.html', render(p, parent, mappings).encode(), readonly=True)
    return p, stats


def render(p, parent=None, mappings=None):
    esc = lambda x: html.escape(str(x), quote=True)
    old = {c['id']:c for c in parent['claims']} if parent else {}
    current = {c['id']:c for c in p['claims']}
    sources = {s['id']:s for s in p['sources']}
    source_names = {sid:f'Source {i}' for i, sid in enumerate(sources, 1)}
    if parent:
        for i,source in enumerate(parent['sources'], 1):
            source_names.setdefault(source['id'], f'Earlier source {i}')
    anchors = {c['id']:f'claim-{i}' for i,c in enumerate(p['claims'], 1)}
    def humanize(text):
        words = re.sub(r'[._-]+', ' ', text).split()
        label = ' '.join(w.upper() if w.lower() in ('gpa', 'doi', 'url', 'id') else w for w in words)
        return label[:1].upper()+label[1:]
    def field_label(c):
        return ' / '.join(humanize(part) for part in c['field'].split('.'))
    titles = {}
    for c in p['claims']:
        if c['field'].endswith('.title') and c['kind'] in ('documented_fact', 'user_report') and isinstance(c['value'], str):
            titles.setdefault(c['subject_id'], set()).add(c['value'])
    def subject_label(subject):
        if len(titles.get(subject, ())) == 1:
            return next(iter(titles[subject]))
        return source_names.get(subject, humanize(subject))
    def claim_link(cid):
        c = current[cid]
        return '<a href="#'+anchors[cid]+'">'+esc(subject_label(c['subject_id'])+' · '+field_label(c))+'</a>'
    def local_link(path, label):
        # Mapping metadata is also treated as untrusted; only contained local references link.
        if not isinstance(path, str): return esc(label)
        parts = Path(path).parts
        if not parts or Path(path).is_absolute() or '..' in parts or parts[0] not in ('sources','intake') or '\\' in path:
            return esc(label)
        return '<a href="../'+esc(urlquote(path, safe='/'))+'">'+esc(label)+'</a>'
    groups = {}
    for c in p['claims']: groups.setdefault(c['subject_id'], []).append(c)
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Private applicant review</title>',
           '<style>body{font:16px/1.55 system-ui,sans-serif;color:#182532;background:#f5f7fa;max-width:1050px;margin:auto;padding:24px}a{color:#174e85}h1,h2,h3{line-height:1.25}section,.panel{background:white;border:1px solid #ccd5de;border-radius:8px;padding:20px;margin:20px 0}article{border-top:1px solid #dce2e8;padding:16px 0}article:first-of-type{border-top:0}h3{margin:0 0 8px}.kind{font-size:.85em;color:#45586a}.value{font-size:1.08em;white-space:pre-wrap;overflow-wrap:anywhere}.note{color:#45586a}.warning{border-left:4px solid #986311;padding-left:12px}summary{cursor:pointer}details{margin:10px 0}code,dd{overflow-wrap:anywhere}dt{font-weight:600}dd{margin:0 0 8px}li{margin:8px 0}nav ul{display:flex;flex-wrap:wrap;gap:8px 20px;list-style:none;padding:0}@media print{body{background:white}section,article{break-inside:avoid}}</style></head><body>',
           '<h1>Private applicant profile review</h1>',
           '<p>'+str(len(p['claims']))+' claims · '+str(len(p['sources']))+' sources · '+str(len(p['issues']))+' unresolved items · '+esc(humanize(p['status']))+'</p>',
           '<p class="warning">Frozen candidates are UNAPPROVED until a matching receipt and explicit human acceptance verify.</p>',
           '<details><summary>Exact version identifiers</summary><dl>']
    for key in ('schema_version','profile_id','revision_id','parent_revision_id','version_name','status'):
        out.append('<dt>'+esc(humanize(key))+'</dt><dd><code>'+esc(p.get(key) or 'None')+'</code></dd>')
    out += ['</dl></details><div class="panel"><h2>Changes from previous revision</h2>']
    changes = [('Added', [c for cid,c in current.items() if cid not in old]),
               ('Removed', [c for cid,c in old.items() if cid not in current]),
               ('Updated', [c for cid,c in current.items() if cid in old and c != old[cid]])]
    out.append('<p>'+' · '.join(f'{len(cs)} {label.lower()}' for label,cs in changes)+'</p>')
    if not parent: out.append('<p class="note">Initial review; no earlier revision to compare.</p>')
    for label,cs in changes:
        if cs:
            labels = list(dict.fromkeys(subject_label(c['subject_id'])+' · '+field_label(c) for c in cs))
            text = '; '.join(labels[:8]) + (f'; and {len(labels)-8} more fields' if len(labels)>8 else '')
            out.append('<p><strong>'+label+':</strong> '+esc(text)+'</p>')
    out += ['</div><section id="unresolved"><h2>Unresolved issues and consolidated questions</h2>']
    if not p['issues']: out.append('<p>No unresolved items recorded.</p>')
    else:
        out.append('<ul>')
        for i in p['issues']:
            out.append('<li><strong>'+esc(humanize(i['kind']))+':</strong> '+esc(i['detail'])+'<br><strong>Next action:</strong> '+esc(i['next_action'])+'<br>'+', '.join(claim_link(cid) for cid in i['claim_ids'])+'</li>')
        out.append('</ul>')
    out += ['</section><nav aria-label="Profile subjects"><ul>']
    for index,subject in enumerate(groups, 1):
        out.append('<li><a href="#subject-'+str(index)+'">'+esc(subject_label(subject))+'</a></li>')
    out.append('</ul></nav>')
    for index,(subject,claims) in enumerate(groups.items(), 1):
        out.append('<section id="subject-'+str(index)+'"><h2>'+esc(subject_label(subject))+'</h2>')
        for c in claims:
            value = c['value'] if isinstance(c['value'], str) else json.dumps(c['value'], ensure_ascii=False)
            if c['value'] is None: value = 'Conflicting evidence' if c['kind']=='conflict' else 'Unknown'
            out += ['<article id="'+anchors[c['id']]+'"><h3>'+esc(field_label(c))+'</h3>',
                    '<div class="kind">'+esc(humanize(c['kind']))+'</div><div class="value">'+esc(value)+'</div>']
            for key,label in (('context','Context'),('rationale','Reason'),('next_action','Next action')):
                if c[key]: out.append('<p class="note"><strong>'+label+':</strong> '+esc(c[key])+'</p>')
            if c['related_claim_ids']:
                out.append('<p><strong>Related evidence:</strong> '+', '.join(claim_link(cid) for cid in c['related_claim_ids'])+'</p>')
            out.append('<details><summary>Evidence and claim metadata ('+str(len(c['evidence']))+' references)</summary>')
            for r in c['evidence']:
                sid = r['source_id']; mapping = (mappings or {}).get(sid, {})
                out.append('<p><strong>'+esc(source_names[sid]+' · '+r['locator'])+'</strong> ('+esc(r['locator_kind'])+')')
                if mapping: out.append(' · '+local_link(mapping.get('snapshot'), 'Open immutable source snapshot'))
                if mapping.get('derived_from'):
                    out.append('<br>Text extracted locally from '+local_link(mapping['derived_from'], 'original PDF')+'; verify against original.')
                if mapping.get('transcription_of'):
                    out.append('<br>User-supplied transcription; original not independently verified. '+local_link(mapping['transcription_of'], 'Open original'))
                out.append('<br>Source ID: <code>'+esc(sid)+'</code><br>Source kind: '+esc(sources[sid]['kind'])+'<br>SHA-256: <code>'+esc(sources[sid]['sha256'])+'</code></p>')
            out.append('<p>Claim ID: <code>'+esc(c['id'])+'</code><br>Subject: <code>'+esc(c['subject_id'])+'</code><br>Field: <code>'+esc(c['field'])+'</code></p></details></article>')
        out.append('</section>')
    out += ['<p>Answer sensitive questions in private local clarification files. Review each missing choice explicitly; documents do not establish preferences. Approval covers this profile only and authorizes no discovery or later stage.</p></body></html>']
    return '\n'.join(out)


def supersede_candidates(store, profile_id):
    for path in (store.root/'candidates').glob('*.json'):
        if path.name.endswith('.request.json'): continue
        prior = store.load('candidates/'+path.name)
        marker = 'candidates/'+prior['revision_id']+'.superseded'
        if prior['profile_id']==profile_id and not store.path('frozen/'+prior['revision_id']+'/COMPLETE').exists() and not store.path(marker).exists():
            store.put(marker, b'superseded\n', readonly=True)


def candidate(store, rid, actor):
    p = copy.deepcopy(store.revision(rid))
    require(p['status']=='draft', 'candidate requires draft')
    parent = copy.deepcopy(p)
    p.update(revision_id=uid(), parent_revision_id=rid, version_name='profile-'+uid(), status='frozen',
             approval=dict(receipt_id=uid(), actor_type='human', actor_id=actor, approved_at=now(), reliable_for_discovery=True, scope='profile_only'))
    validate(p)
    supersede_candidates(store, p['profile_id'])
    raw = encode(p)
    target = dict(type='custom', key=p['revision_id'], revisionId=digest(raw))
    request = dict(kind='request_confirmation', resolverPolicy='human_only', addresseeUserId=actor,
        continuationPolicy='wake_assignee', idempotencyKey='profile:'+p['revision_id']+':'+digest(raw),
        title='Approve exact private applicant profile', payload=dict(version=1,
        prompt='I have reviewed this exact local profile, including unresolved items, and approve it as reliable enough for discovery. Approval covers the profile only; no later stage is authorized.',
        target=target, supersedeOnUserComment=True, acceptLabel='Approve exact version', rejectLabel='Request corrections', rejectRequiresReason=True, allowDeclineReason=True,
        detailsMarkdown='Schema: '+p['schema_version']+'; profile: '+p['profile_id']+'; revision: '+p['revision_id']+'; version: '+p['version_name']+'; SHA-256: '+digest(raw)))
    store.put('candidates/'+p['revision_id']+'.json', raw, readonly=True)
    store.put('candidates/'+p['revision_id']+'.request.json', encode(request), readonly=True)
    mapping = store.load('profiles/'+rid+'.manifest.json')
    store.put('reviews/'+p['revision_id']+'.html', render(p, parent, mapping).encode(), readonly=True)
    return p, request


def receipt_from_interaction(raw, request, interaction, company, issue):
    p = json.loads(raw)
    require(interaction['companyId']==company and interaction['issueId']==issue, 'approval boundary mismatch')
    require(interaction['kind']=='request_confirmation' and interaction['status']=='accepted', 'approval not accepted')
    require(interaction['effectiveResolverPolicy']=='human_only', 'human-only approval required')
    require(interaction['resolvedByUserId']==p['approval']['actor_id'] and not interaction.get('resolvedByAgentId'), 'wrong approval actor')
    payload = copy.deepcopy(interaction['payload'])
    # Paperclip persists this UI default on older requests that omitted it.
    # Recognize only that exact boolean; approval terms and target stay exact.
    if 'allowDeclineReason' not in request['payload'] and payload.get('allowDeclineReason') is True:
        del payload['allowDeclineReason']
    if encode(payload)==encode(request['payload']):
        require(payload['target']['revisionId']==digest(raw), 'candidate digest mismatch')
    else:
        # An earlier board card used a text-bound exact version and digest instead
        # of Paperclip's structured target. Accept only that complete form.
        expected = dict(
            version=1,
            prompt=('After reviewing the private candidate, do you approve freezing '
                    'Applicant Profile version '+p['version_name']+' with SHA-256 '
                    +digest(raw)+' as reliable for the profile stage?'),
            acceptLabel='Approve exact profile', rejectLabel='Request corrections',
            rejectRequiresReason=True, rejectReasonLabel='What should be corrected?',
            allowDeclineReason=True, supersedeOnUserComment=True,
            detailsMarkdown=('Private review: grad-compass-research-engine/private/reviews/'
                'applicant-profile-board-correction-review-v3.md. This freezes only '
                'the Applicant Profile; it does not approve a CV or authorize discovery '
                'or outreach. The earlier frozen profile remains unchanged.'))
        require(encode(payload)==encode(expected), 'confirmation payload changed')
    require(interaction['result']['outcome']=='accepted', 'explicit acceptance required')
    receipt = {k:p[k] for k in ('schema_version','profile_id','revision_id','version_name','synthetic')}
    receipt.update(p['approval'])
    receipt.update(sha256=digest(raw), decision='accepted', interaction_id=interaction['id'], resolved_at=interaction['resolvedAt'])
    verify_receipt(raw, receipt)
    return receipt


def freeze(store, rid, issue, interaction_id, synthetic_interaction=None):
    require(not store.path('candidates/'+opaque(rid)+'.superseded').exists(), 'candidate superseded')
    raw = store.read('candidates/'+opaque(rid)+'.json')
    request = store.load('candidates/'+rid+'.request.json')
    if synthetic_interaction is not None:
        require(store.synthetic and json.loads(raw)['synthetic'], 'synthetic approval forbidden for private profile')
        interaction = synthetic_interaction
        company = 'synthetic-company'
    else:
        require(not store.synthetic, 'real approvals only for private mode')
        company = os.environ['PAPERCLIP_COMPANY_ID']
        # Only the run-authenticated local Paperclip API is contacted; only metadata is retrieved.
        url = os.environ['PAPERCLIP_API_URL'].rstrip('/')+'/api/issues/'+opaque(issue)+'/interactions'
        req = Request(url, headers={'Authorization':'Bearer '+os.environ['PAPERCLIP_API_KEY']})
        with urlopen(req, timeout=20) as response: interactions = json.load(response)
        matches = [i for i in interactions if i['id']==interaction_id]
        require(len(matches)==1, 'approval interaction not found')
        interaction = matches[0]
    receipt = receipt_from_interaction(raw, request, interaction, company, issue)
    # Directory reservation provides one atomic winner; incomplete directories are never authoritative.
    folder = store.path('frozen/'+rid)
    folder.mkdir(mode=0o700, exist_ok=False)
    store.put('frozen/'+rid+'/profile.json', raw, readonly=True)
    store.put('frozen/'+rid+'/receipt.json', encode(receipt), readonly=True)
    # Keep candidate lineage addressable for subsequent corrections.
    store.put('profiles/'+rid+'.json', raw, readonly=True)
    parent_id = json.loads(raw)['parent_revision_id']
    store.put('profiles/'+rid+'.manifest.json', store.read('profiles/'+parent_id+'.manifest.json'), readonly=True)
    store.put('frozen/'+rid+'/COMPLETE', b'complete\n', readonly=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(ROOT/'private'))
    parser.add_argument('--synthetic', action='store_true', help='Only invented fixtures; never pass private inputs')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check-storage')
    b = sub.add_parser('build'); b.add_argument('manifest'); b.add_argument('--parent')
    c = sub.add_parser('candidate'); c.add_argument('revision'); c.add_argument('--actor', required=True)
    f = sub.add_parser('freeze'); f.add_argument('revision'); f.add_argument('--issue', required=True); f.add_argument('--interaction', required=True)
    args = parser.parse_args()
    try:
        os.umask(0o077)
        s = Store(args.root, args.synthetic)
        if args.command=='build':
            p, stats = build(s, args.manifest, args.parent)
            print(json.dumps(dict(revision_id=p['revision_id'], stats=stats)))
        elif args.command=='candidate':
            p, request = candidate(s, args.revision, args.actor)
            print(json.dumps(dict(revision_id=p['revision_id'], sha256=request['payload']['target']['revisionId'])))
        elif args.command=='freeze':
            r = freeze(s, args.revision, args.issue, args.interaction)
            print(json.dumps(dict(revision_id=r['revision_id'], receipt_id=r['receipt_id'])))
        else: print('PASS: storage permissions, containment and Git checks')
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        # Exception messages can contain paths or document text. No content-bearing logging.
        print('Workflow stopped; inspect the local inputs and storage contract. No approval inferred.', file=sys.stderr)
        return 1
    return 0

if __name__=='__main__': sys.exit(main())
