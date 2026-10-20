"""One safe content tree for the screen reader and generated PDF. No research here."""
import hashlib
import html
import re
import mistune
from datetime import datetime


PARSER=mistune.create_markdown(renderer='ast',plugins=['table'])


def plain(tokens):
    return ''.join(t.get('raw','') if t['type'] in ('text','codespan','inline_html') else '\n' if t['type'] in ('softbreak','linebreak') else plain(t.get('children',[])) for t in tokens)


def inline(tokens, pdf=False):
    """Allow formatting and public links only; producer HTML is always escaped."""
    out=[]
    for t in tokens:
        kind=t['type'];child=inline(t.get('children',[]),pdf);raw=html.escape(t.get('raw',''))
        if kind in ('text','inline_html','codespan'):out.append(raw)
        elif kind in ('strong','emphasis'):out.append(('<b>' if kind=='strong' else '<i>')+child+('</b>' if kind=='strong' else '</i>'))
        elif kind in ('linebreak','softbreak'):out.append('<br/>' if pdf else '\n')
        elif kind=='link':
            url=t.get('attrs',{}).get('url','')
            out.append(('<a href="'+html.escape(url,quote=True)+'"'+(' color="#08647c"' if pdf else ' target="_blank" rel="noopener noreferrer"')+'>'+child+'</a>') if re.match(r'^https?://',url,re.I) else child)
        else:out.append(child or raw)
    return ''.join(out)


def refs(text):
    result=[]
    for group in re.findall(r'\[(E\d{2}[^\]]*)\]',text):
        for first,last in re.findall(r'E(\d{2})(?:[–—-]E?(\d{2}))?',group):
            for n in range(int(first),int(last or first)+1):
                if n<100 and 'E%02d'%n not in result:result.append('E%02d'%n)
    return result


def parse_report(markdown,evidence):
    sections=[];blocks={};counts={};title='Country report';title_seen=False;section=None
    def block(tokens):
        text=plain(tokens)
        digest=hashlib.sha256(text.encode()).hexdigest()[:12]
        count=counts.get(digest,0);counts[digest]=count+1
        identity=(section['id'] if section else 'introduction')+'/'+digest+'/'+str(count)
        item={'id':identity,'text':text,'html':inline(tokens),'pdf':inline(tokens,True),'refs':refs(text)}
        blocks[identity]=item;return item
    def ensure():
        nonlocal section
        if section is None:
            section={'id':'introduction','title':'Report context','items':[]};sections.append(section)
    for token in PARSER(markdown):
        kind=token['type']
        if kind=='heading':
            text=plain(token['children'])
            if token['attrs']['level']==1 and not title_seen:title=text;title_seen=True;continue
            identity=re.sub('[^a-z0-9]+','-',text.lower()).strip('-')
            section={'id':identity,'title':text,'items':[]};sections.append(section)
        elif kind in ('paragraph','block_text'):
            ensure();section['items'].append({'type':'paragraph','block':block(token['children'])})
        elif kind=='list':
            ensure()
            for index,item in enumerate(token['children']):
                tokens=[t for p in item.get('children',[]) for t in p.get('children',[])]
                section['items'].append({'type':'list_item','number':index+1 if token.get('attrs',{}).get('ordered') else None,'block':block(tokens)})
        elif kind=='table':
            ensure();rows=[]
            for part in token['children']:
                source=[part['children']] if part['type']=='table_head' else [r['children'] for r in part['children']]
                rows.extend([[block(c['children']) for c in row] for row in source])
            section['items'].append({'type':'table','rows':rows})
        elif kind in ('block_html','block_code'):
            if kind=='block_html' and re.fullmatch(r'\s*<!--[\s\S]*?-->\s*',token.get('raw','')):continue
            ensure();section['items'].append({'type':'paragraph','block':block([{'type':'text','raw':token.get('raw','')}])})
    sources={}
    for token in PARSER(evidence):
        if token['type']!='table':continue
        for part in token['children']:
            if part['type']!='table_body':continue
            for row in part['children']:
                cells=row['children'];ref=plain(cells[0]['children']).strip()
                if not re.fullmatch(r'E\d{2}',ref):continue
                links=[]
                def walk(tokens):
                    for t in tokens:
                        if t['type']=='link' and re.match(r'^https?://',t.get('attrs',{}).get('url',''),re.I):links.append({'label':plain(t['children']),'url':t['attrs']['url']})
                        walk(t.get('children',[]))
                walk(cells[-1]['children'])
                sources[ref]={'id':ref,'topic':plain(cells[1]['children']),'text':plain(cells[-1]['children']),'links':links}
    prepared=re.search(r'\*\*Prepared:\*\*\s*(\d{1,2} \w+ \d{4})',markdown)
    try:report_date=datetime.strptime(prepared[1],'%d %B %Y').date().isoformat() if prepared else None
    except ValueError:report_date=None
    text='\n'.join(b['text'] for b in blocks.values())
    historical=re.search(r'Published figures below concern\s+(\d{4}[–-]\d{2,4})',text)
    labels=[]
    if historical:labels.append({'kind':'historical','text':historical[1]+' · published figures, not target-year terms'})
    target=[]
    for b in blocks.values():
        if re.search(r'unknown|unconfirmed|under review|need.*refresh',b['text'],re.I):
            target.extend(p for p in re.findall(r'\b\d{4}[–-]\d{2,4}\b',b['text']) if not historical or p!=historical[1])
    if target:labels.append({'kind':'unknown','text':', '.join(dict.fromkeys(target))+' · terms require confirmation'})
    if re.search(r'competitive',text,re.I):labels.append({'kind':'conditional','text':'Funding is competitive and conditional; no award or full support is established'})
    return {'title':title,'report_date':report_date,'labels':labels,'sections':sections,'blocks':blocks,'sources':sources}
