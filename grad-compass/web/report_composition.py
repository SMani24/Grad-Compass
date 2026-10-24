"""Presentation roles, not editorial judgments. Original passages stay immutable."""
import re

VERSION='grad-compass-report-composition-1.0'
COVERAGE_LABELS={'supported_finding':'Supported finding','not_investigated':'Not investigated',
    'investigated_unresolved':'Investigated, unresolved','not_yet_published':'Not yet published',
    'not_applicable':'Not applicable','unknown':'Coverage not supplied'}


def role(identity):
    # Conventional headings are the compatible template contract. Unknown titles
    # remain substantive: an unfamiliar country/region is never hidden by a guess.
    if re.fullmatch(r'(?:seven-topic-|research-)?coverage(?:-and-missing-content)?',identity):return 'coverage'
    if identity in ('sources','source-guide','sources-and-evidence-precision','source-guide-and-evidence-precision','sources-and-evidence-map','evidence-map-binding'):return 'sources'
    if identity in ('introduction','report-context','technical-provenance','technical-details','version-and-review-provenance','report-details'):return 'context'
    return 'research'


def attach(tree):
    groups={key:[] for key in ('research','coverage','sources','context')}
    stack=[]
    for section in tree['sections']:
        level=section.get('level',2)
        if level==0:level=7  # Unheaded preamble does not own later sections.
        while stack and stack[-1][0]>=level:stack.pop()
        own=role(section['id'])
        section['role']=stack[-1][1] if own=='research' and stack and stack[-1][1]!='research' else own
        stack.append((level,section['role']));groups[section['role']].append(section['id'])
    if not groups['research']:
        for section in tree['sections']:
            if section['id']=='introduction' and section['items']:
                section['role']='research';groups['research'].append(section['id']);groups['context'].remove(section['id'])
    tree['composition']={'schema_version':VERSION,**groups,'source_list_owner':'consumer'}
    tree['source_inventory']=source_inventory({},tree)
    assigned={identity for source in tree['source_inventory'] for identity in source['note_ids']}
    tree['composition']['source_context']=[block['id'] for block in source_notes(tree) if block['id'] not in assigned]
    tree['composition']['source_context'] += [block['id'] for table in source_tables(tree) for row in table['rows'] for block in row]
    return tree


def sections(tree,kind='research'):
    return [section for section in tree['sections'] if section.get('role',role(section['id']))==kind]


def markdown_sections(markdown):
    """Keep substantive Markdown bytes/formatting; don't reserialize its AST."""
    chunks=[];identity='introduction';lines=[];title_seen=False;fence=None;section_role='context';stack=[]
    def flush():
        if lines:chunks.append({'id':identity,'role':section_role,'markdown':''.join(lines).strip()})
    for line in markdown.splitlines(keepends=True):
        marker=re.match(r'^\s{0,3}(`{3,}|~{3,})',line)
        if marker:
            if fence is None:fence=marker[1][0]
            elif marker[1][0]==fence:fence=None
        heading=None if fence else re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$',line)
        if heading:
            if len(heading[1])==1 and not title_seen:
                title_seen=True;continue
            flush();lines=[];identity=re.sub('[^a-z0-9]+','-',heading[2].lower()).strip('-')
            level=len(heading[1])
            while stack and stack[-1][0]>=level:stack.pop()
            own=role(identity);section_role=stack[-1][1] if own=='research' and stack and stack[-1][1]!='research' else own
            stack.append((level,section_role))
        lines.append(line)
    flush()
    if not any(chunk['role']=='research' for chunk in chunks):
        for chunk in chunks:
            if chunk['id']=='introduction' and chunk['markdown']:chunk['role']='research'
    return chunks


def source_notes(tree):
    # Legacy writers embedded a second full inventory. Keep their precision and
    # historical context paragraphs, while the consumer renders the inventory.
    notes=[]
    for section in sections(tree,'sources'):
        for item in section['items']:
            if item['type']=='table':continue  # Preserve row relationships separately.
            blocks=[item['block']]
            for block in blocks:
                # Only elide the exact old inventory sentence when every field is
                # already represented by the bound record. Rich or unfamiliar
                # source notes retain their complete qualifiers and locators.
                redundant=False
                for ref,source in tree['sources'].items():
                    record=source.get('source_record',{})
                    if len(source['links'])==1 and record:
                        expected=f"{ref} — {source['links'][0]['label']}; observed {record.get('observed_at')}; source ID {record.get('source_id')}."
                        if block['text']==expected:redundant=True;break
                if not redundant:notes.append(block)
    return notes


def source_tables(tree):
    return [item for section in sections(tree,'sources') for item in section['items'] if item['type']=='table']


def review(report,edition=None):
    value=(edition['metadata']['factual_review'] if edition else report['metadata'].get('canonical_factual_review',{'state':'unknown'}))
    return {**value,'label':value.get('state','unknown').replace('_',' ').capitalize(),
            'document':'Reader edition' if edition and edition['metadata']['edition']=='reader' else 'Detailed edition' if edition else 'Canonical report'}


def observation_dates(report):
    values=[source.get('observed_at') for source in (report.get('finding') or {}).get('sources',[])]
    artifact=report['metadata'].get('source_artifact')
    if isinstance(artifact,dict):values.append(artifact.get('observed_on'))
    return sorted({value[:10] for value in values if isinstance(value,str) and re.match(r'^\d{4}-\d{2}-\d{2}',value)})


def source_inventory(report,tree):
    """One public URL entry, retaining distinct records/locators and ref mappings."""
    inventory={}
    def entry(url):return inventory.setdefault(url,{'url':url,'labels':[],'refs':[],'records':[],'note_ids':[]})
    for ref,source in tree['sources'].items():
        for link in source['links']:
            item=entry(link['url'])
            if ref not in item['refs']:item['refs'].append(ref)
            if link['label'] not in item['labels']:item['labels'].append(link['label'])
        record=source.get('source_record')
        if record:
            item=entry(record['source_url'])
            if record not in item['records']:item['records'].append(record)
    for record in (report.get('finding') or {}).get('sources',[]):
        url=record.get('source_url')
        if not url:continue
        item=entry(url)
        if record not in item['records']:item['records'].append(record)
    # Narrative links are public supplied content too. They remain explicitly
    # unmapped unless the evidence map supplies a reference; no support is inferred.
    for block in tree['blocks'].values():
        for link in block.get('links',[]):
            item=entry(link['url'])
            if link['label'] not in item['labels']:item['labels'].append(link['label'])
    for block in source_notes(tree):
        urls=[link['url'] for link in block.get('links',[])] or [url for url in inventory if url in block['text']]
        if urls:entry(urls[0])['note_ids'].append(block['id'])
    return list(inventory.values())
