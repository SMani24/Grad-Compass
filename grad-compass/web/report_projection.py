"""Immutable compatibility views of original result bytes; never producer reports."""
from contextlib import closing
import json
from uuid import uuid5,NAMESPACE_URL
from web import research_envelopes as env
from web.report_content import parse_report
from web.report_model import TOPICS,topic,normalize

SCHEMA='grad-compass-received-report-projection-1.0'


def _id(text):return str(uuid5(NAMESPACE_URL,'grad-compass:received-report:'+text))


def detail(workspace,identity):
    try:return workspace.research.request(identity)
    except ValueError:
        archived=workspace.archived_requests(identity) if hasattr(workspace,'archived_requests') else None
        if archived is None:raise
        return archived


def build(request,result,code):
    from web.report_packages import digest
    findings=[f for f in result['findings'] if f.get('kind')=='country' and f['country_code']==code]
    if not findings:raise ValueError('No received country finding in this result')
    groups={key:[] for key,_ in TOPICS};sources={};reviews=[]
    # Keep all public source metadata and original finding scope; do not manufacture
    # a claim-to-source relation or extract new claims from narrative text.
    for f in findings:
        reviews.append({'finding_id':f['finding_id'],'finding_revision':f['finding_revision'],'factual_review':f.get('review',{'decision':f.get('review_status','unknown')}),'human_approval':f.get('human_approval',{'state':'unknown'})})
        for source in f.get('sources',[]):sources.setdefault(env.fingerprint(source),source)
        field=f.get('field','summary');groups[topic(field)].append((f,field,f['summary']))
        for field in ('study_routes','language','funding_routes','costs','work_rules','application_timing'):
            if isinstance(f.get(field),str) and f[field].strip():groups[topic(field)].append((f,field,f[field]))
        for i,text in enumerate(f.get('uncertainties',[])):
            if isinstance(text,str):groups['questions'].append((f,'uncertainty-'+str(i+1),text))
    source_refs={key:'E'+str(i+1).zfill(2) for i,key in enumerate(sources)}
    lines=['# '+code+' — received country findings','', '**Issued:** '+str(result.get('issued_at') or 'Date not supplied'),'','This is an app compatibility view of received findings, not a producer-prepared report or a concise editorial edition. Original response bytes and review states are retained.','']
    # JSON-escaped text is rendered as literal Markdown text, preserving the exact
    # supplied words while avoiding producer HTML/Markdown injection from fields.
    def literal(text):
        import re
        return re.sub(r'([\\`*_{}\[\]<>#+!|])',r'\\\1',text)
    for key,title in TOPICS:
        lines+=['## '+title,'']
        if not groups[key]:lines+=['Not separately published in this response. Research coverage for this topic is unknown; request the missing report section from Dave.',''];continue
        for finding,field,text in groups[key]:
            lines += [literal(text),'']
            refs=[source_refs[env.fingerprint(s)] for s in finding.get('sources',[])]
            lines += ['Finding field: '+literal(field)+'. Finding-level references: '+('['+', '.join(refs)+']' if refs else 'none supplied')+'.','']
    evidence=['| Ref | Topic | Sources |','| --- | --- | --- |']
    for key,source in sources.items():
        ref=source_refs[key];evidence.append('| '+ref+' | '+source.get('locator',key).replace('|','\\|').replace('\n',' ')+' | [Public source]('+source['source_url']+') · observed '+str(source.get('observed_at','unknown'))+' |')
    canonical=('\n'.join(lines)+'\n').encode();evidence=('\n'.join(evidence)+'\n').encode();docsha=digest(canonical)
    reportid=_id(request['request_id']+':'+code);revisionid=_id(result['digest']+':'+code)
    metadata={'schema_version':SCHEMA,'report_id':reportid,'country_code':code,'report_date':str(result.get('issued_at') or '')[:10] or None,
      'request':{'id':request['request_id'],'revision':request['revision'],'sha256':request['digest']},
      'canonical_document':{'id':reportid,'revision_id':revisionid,'revision_number':result['revision'],'sha256':docsha},
      'evidence_map':{'sha256':digest(evidence)},'producer_result':{'id':result['result_id'],'revision':result['revision'],'body_sha256':result['digest'],'finding_revision':findings[0]['finding_revision']},
      'archived':bool(request.get('_archived')),'synthetic':request.get('synthetic',False),'finding_reviews':reviews,'canonical_factual_review':{'state':'unknown','scope':'No producer-prepared report review exists; original finding reviews are listed separately.'},'human_approval':{'state':'unknown'},'source_citation_scope':'finding'}
    content=parse_report(canonical.decode(),evidence.decode())
    metadata['passage_origins']={b['id']:{'finding_id':f['finding_id'],'finding_revision':f['finding_revision']} for b in content['blocks'].values() for entries in groups.values() for f,field,text in entries if b['text']==text}
    raw=(env.compact(metadata)+'\n').encode();key=digest((reportid+':'+revisionid+':'+docsha).encode())
    combined={'sources':list(sources.values()),'coverage':'\n'.join(f.get('coverage','') for f in findings),'finding_id':findings[0]['finding_id'],'finding_revision':findings[0]['finding_revision']}
    return normalize({'key':key,'edition':digest(raw),'metadata':metadata,'content':parse_report(canonical.decode(),evidence.decode()),'finding':combined,'metadata_bytes':raw,'canonical_bytes':canonical,'evidence_bytes':evidence,'reader':None,'detailed':None,'editorial_editions':[],
      'delivery':{'completion':result.get('completion'),'result_revision':result['revision'],'issued_at':result.get('issued_at')},'assets':{}})


def retain(workspace,report):
    from web.report_packages import immutable
    root=workspace.directory/'report-projections'/report['key']/report['edition']
    for name,body in [('canonical.md',report['canonical_bytes']),('evidence.md',report['evidence_bytes']),('metadata.local.json',report['metadata_bytes'])]:immutable(root/name,body)


def cached(workspace,path):
    from web.report_packages import member,digest
    raw=member(workspace.directory,str(path.relative_to(workspace.directory))).read_bytes();meta=env.loads(raw)
    if meta.get('schema_version')!=SCHEMA:raise ValueError('Unknown compatibility view version')
    request=detail(workspace,meta['request']['id'])
    saved={**request['request'],'_archived':request.get('archive',False)};producer=meta['producer_result']
    if (saved['revision'],saved['digest'])!=(meta['request']['revision'],meta['request']['sha256']):raise ValueError('Compatibility request binding mismatch')
    result=next((r['envelope'] for r in request['results'] if (r['envelope']['result_id'],r['envelope']['revision'],r['envelope']['digest'])==(producer['id'],producer['revision'],producer['body_sha256'])),None)
    if result is None:raise ValueError('Compatibility result binding mismatch')
    # Validate retained bytes against their immutable source-bound inventory.
    canonical=member(path.parent,'canonical.md').read_bytes();evidence=member(path.parent,'evidence.md').read_bytes();doc=meta['canonical_document']
    key=digest((meta['report_id']+':'+doc['revision_id']+':'+doc['sha256']).encode())
    if digest(canonical)!=doc['sha256'] or digest(evidence)!=meta['evidence_map']['sha256'] or path.parent.name!=digest(raw) or path.parent.parent.name!=key:raise ValueError('Retained compatibility view digest mismatch')
    live=build(saved,result,meta['country_code']);live.update(key=key,edition=digest(raw),metadata=meta,metadata_bytes=raw,canonical_bytes=canonical,evidence_bytes=evidence,content=parse_report(canonical.decode(),evidence.decode()))
    return normalize(live)


def catalog(workspace,request_id=None):
    reports={};errors=[]
    cache=workspace.directory/'report-projections'
    for path in sorted(cache.glob('*/*/metadata.local.json')):
        try:
            report=cached(workspace,path)
            if request_id is None or report['metadata']['request']['id']==request_id:reports[report['key']]=report
        except (ValueError,OSError,KeyError,TypeError) as error:errors.append({'file':'Retained received-findings view','error':str(error)})
    requests=workspace.research.snapshot()['requests']
    if request_id is None and hasattr(workspace,'archived_requests'):
        active={r['request_id'] for r in requests}
        requests=requests+[r for r in workspace.archived_requests()['requests'] if r['request_id'] not in active]
    if request_id and not any(r['request_id']==request_id for r in requests) and hasattr(workspace,'archived_requests') and workspace.archived_requests(request_id):requests=[{'request_id':request_id}]
    for item in requests:
        if request_id and item['request_id']!=request_id:continue
        saved_detail=detail(workspace,item['request_id'])
        for row in saved_detail['results']:
            result=row['envelope']
            for code in sorted({f['country_code'] for f in result['findings'] if f.get('kind')=='country'}):
                report=build({**saved_detail['request'],'_archived':saved_detail.get('archive',False)},result,code)
                if report['key'] not in reports:retain(workspace,report);reports[report['key']]=report
    return {'reports':list(reports.values()),'errors':errors}
