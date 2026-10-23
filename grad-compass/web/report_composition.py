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
    return [item['block'] for section in sections(tree,'sources') for item in section['items']
            if item['type']=='paragraph' or (item['type']=='list_item' and not re.search(r'https?://|href=',item['block']['html']))]


def review(report,edition=None):
    value=(edition['metadata']['factual_review'] if edition else report['metadata'].get('canonical_factual_review',{'state':'unknown'}))
    return {**value,'label':value.get('state','unknown').replace('_',' ').capitalize(),
            'document':'Reader edition' if edition and edition['metadata']['edition']=='reader' else 'Detailed edition' if edition else 'Canonical report'}


def source_inventory(report,tree):
    """One public URL entry, retaining distinct records/locators and ref mappings."""
    inventory={}
    def entry(url):return inventory.setdefault(url,{'url':url,'labels':[],'refs':[],'records':[]})
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
    return list(inventory.values())
