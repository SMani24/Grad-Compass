"""Validated private canonical reports and exact-version personal annotations."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from uuid import uuid4

from web import research_envelopes as env
from web.local import atomic_json,private_directory,regular
from web.report_content import parse_report

SCHEMA='grad-compass-private-report-package-0.1'
NOTICE='grad-compass-report-delivery-0.1'


def digest(body):return hashlib.sha256(body).hexdigest()


def member(root,name):
    if not isinstance(name,str):raise ValueError('Report file path is required')
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or path.as_posix()!=name:raise ValueError('Report files must stay in their private package')
    target=root/path
    if any(p.is_symlink() for p in (target,*target.parents)):raise ValueError('Report storage cannot use links')
    return regular(target)


def checked_file(root,ref,limit=2_000_000):
    path=member(root,ref.get('relative_path'))
    if not path.is_file() or path.stat().st_size>limit:raise ValueError('Report file is missing or too large')
    body=path.read_bytes()
    if digest(body)!=ref.get('sha256'):raise ValueError('Report file digest does not match exact delivered bytes')
    return body


def validate(workspace,path,retained=False,expected_metadata_sha=None):
    raw=member(workspace.directory,str(path.relative_to(workspace.directory))).read_bytes()
    if len(raw)>100_000:raise ValueError('Report metadata is too large')
    if expected_metadata_sha is not None and digest(raw)!=expected_metadata_sha:raise ValueError('Report delivery metadata digest mismatch')
    meta=env.loads(raw)
    if not isinstance(meta,dict) or meta.get('schema_version') not in (SCHEMA,'grad-compass-private-report-package-0.2'):raise ValueError('Unknown private report package version')
    if any(not isinstance(meta.get(k),dict) for k in ('request','canonical_document','evidence_map')):raise ValueError('Report request, canonical document and evidence map must be objects')
    env.identifier(meta.get('report_id'));request_ref=meta['request'];doc=meta['canonical_document']
    request=workspace.research.request(request_ref['id'])['request']
    if request['revision']!=request_ref['revision'] or request['digest']!=request_ref['sha256'] or meta['country_code'] not in request['countries']:raise ValueError('Report must bind its saved country/request revision and exact digest')
    env.identifier(doc['id']);env.identifier(doc['revision_id'])
    if type(doc['revision_number']) is not int or doc['revision_number']<1:raise ValueError('Report revision must be a positive integer')
    if retained:
        canonical=regular(path.parent/'canonical.md').read_bytes();evidence=regular(path.parent/'evidence.md').read_bytes()
        if digest(canonical)!=doc['sha256'] or digest(evidence)!=meta['evidence_map']['sha256']:raise ValueError('Retained canonical report digest mismatch')
    else:canonical=checked_file(path.parent,doc);evidence=checked_file(path.parent,meta['evidence_map'])
    review=meta.get('canonical_factual_review',{'state':'pending'})
    if not isinstance(review,dict):raise ValueError('Report factual review must be an object')
    state=review.get('state','pending')
    if state not in ('pending','unknown','accepted','accepted_with_caveats','pass','pass_with_caveats','rejected','needs_correction'):raise ValueError('Unrecognized canonical report review disposition')
    if state not in ('pending','unknown'):
        if review.get('canonical_revision_id')!=doc['revision_id'] or review.get('canonical_sha256')!=doc['sha256'] or not review.get('review_id') or not review.get('scope') or not (review.get('reviewed_at') or review.get('time')):raise ValueError('Factual review must name the exact canonical revision/hash, reviewer record, time and scope')
    human=meta.get('human_approval',{'state':'unknown'})
    if not isinstance(human,dict):raise ValueError('Report human approval must be an object')
    if human.get('state') not in ('unknown','not_requested'):
        if human.get('canonical_revision_id')!=doc['revision_id'] or human.get('canonical_sha256')!=doc['sha256'] or not human.get('approval_id'):raise ValueError('Human approval must bind this exact canonical report separately')
    producer=meta.get('producer_result');finding=None
    if producer is not None and not isinstance(producer,dict):raise ValueError('Report producer-result binding must be an object')
    if meta['schema_version']=='grad-compass-private-report-package-0.2' and not producer:raise ValueError('Ordinary reports require an exact received producer-result binding')
    if producer:
        detail=workspace.research.request(request['request_id'])
        result=next((r['envelope'] for r in detail['results'] if r['envelope']['result_id']==producer['id'] and r['envelope']['revision']==producer['revision'] and r['envelope']['digest']==producer['body_sha256']),None)
        if result is None:raise ValueError('Report producer-result binding is not recorded in this profile')
        finding=next((f for f in result['findings'] if f['kind']=='country' and f['country_code']==meta['country_code'] and f['finding_revision']==producer['finding_revision'] and ('finding_id' not in producer or f['finding_id']==producer['finding_id'])),None)
        if finding is None:raise ValueError('Report finding revision is not bound to its producer result')
    if not retained:
        for asset in meta.get('attachments',[]):checked_file(path.parent,asset,20_000_000)
        if meta.get('pdf'):checked_file(path.parent,meta['pdf'],25_000_000)
    if producer and sum(1 for f in result['findings'] if f.get('kind')=='country' and f['country_code']==meta['country_code'] and f['finding_revision']==producer['finding_revision'])!=1:raise ValueError('Report producer finding binding is ambiguous')
    key=digest((meta['report_id']+':'+doc['revision_id']+':'+doc['sha256']).encode())
    content=parse_report(canonical.decode('utf-8'),evidence.decode('utf-8'))
    if 'coverage' in meta:
        from web.report_model import validate_coverage
        validate_coverage(meta['coverage'],content)
    report={'key':key,'edition':digest(raw),'metadata':meta,'content':content,'finding':finding,
            'metadata_bytes':raw,'canonical_bytes':canonical,'evidence_bytes':evidence,'delivery':{'completion':result.get('completion'),'result_revision':result['revision'],'issued_at':result.get('issued_at')} if producer else {}}
    if meta['schema_version']=='grad-compass-private-report-package-0.2':
        from web.report_delivery import validate_extension
        validate_extension(workspace,path.parent,report,retained)
    if finding:report['finding_reviews']=[{'finding_id':finding['finding_id'],'finding_revision':finding['finding_revision'],'factual_review':finding.get('review',{'decision':finding.get('review_status','unknown')}),'human_approval':finding.get('human_approval',{'state':'unknown'})}]
    report['_source_root']=str(path.parent.relative_to(workspace.directory))
    return report


def immutable(path,body):
    private_directory(path.parent);regular(path)
    if path.exists():
        if path.read_bytes()!=body:raise ValueError('A retained report file cannot be overwritten')
        return
    # Publish complete bytes exclusively; an interrupted write never has a final name.
    temporary=path.with_name('.'+path.name+'-'+str(uuid4()))
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
        try:os.link(temporary,path)
        except FileExistsError:
            if path.read_bytes()!=body:raise ValueError('Conflicting retained report bytes')
    finally:
        if temporary.exists():temporary.unlink()


def retain(workspace,report):
    target=workspace.directory/'report-cache'/report['key']/report['edition']
    immutable(target/'canonical.md',report['canonical_bytes']);immutable(target/'evidence.md',report['evidence_bytes'])
    for asset in report.get('assets',{}).values():
        if not (target/'assets'/asset['sha256']).exists():
            source=member(workspace.directory,report['_source_root']+'/'+asset['relative_path'])
            immutable(target/'assets'/asset['sha256'],source.read_bytes())
    from web.report_editions import retain as retain_edition
    for edition in report.get('bundled_editions',{}).values():retain_edition(workspace,report,edition)
    immutable(target/'metadata.local.json',report['metadata_bytes'])


def _cached(workspace,path):
    # Retained metadata references original names: rehydrate with the same validated
    # bytes in memory, never relax source/request/review checks for a cache hit.
    report=validate(workspace,path,retained=True)
    if path.parent.parent.name!=report['key'] or path.parent.name!=report['edition']:raise ValueError('Retained report identity mismatch')
    return report


def _catalog(workspace,request_id=None):
    if not getattr(workspace,'operational',False):
        from web.report_projection import catalog as projections
        return projections(workspace,request_id)
    with workspace.state_lock,closing(workspace.connect()):
        found={};errors=[];bindings={}
        cache=workspace.directory/'report-cache'
        if cache.exists():
            for path in cache.glob('*/*/metadata.local.json'):
                try:
                    report=_cached(workspace,path);doc=report['metadata']['canonical_document'];identity=(doc['id'],doc['revision_id'])
                    if identity in bindings and bindings[identity]!=doc['sha256']:raise ValueError('Retained canonical revision has conflicting bytes')
                    bindings[identity]=doc['sha256'];found[(report['key'],report['edition'])]=report
                except (OSError,ValueError,KeyError,TypeError,UnicodeError) as error:errors.append({'file':'Retained report','error':str(error)})
        root=workspace.directory/'reports'
        if root.exists():
            for path in sorted(root.rglob('metadata.local.json')):
                if any(p.startswith('.') for p in path.relative_to(root).parts):continue
                if 'editions' in path.relative_to(root).parts:continue
                try:
                    candidate=env.loads(path.read_bytes())
                    if not isinstance(candidate,dict):raise ValueError('Report metadata must be an object')
                    if candidate.get('schema_version')=='grad-compass-private-report-package-0.2' and not (workspace.directory/'report-receipts'/(digest(path.read_bytes())+'.json')).is_file():continue
                    report=validate(workspace,path);doc=report['metadata']['canonical_document'];identity=(doc['id'],doc['revision_id'])
                    if identity in bindings and bindings[identity]!=doc['sha256']:raise ValueError('Canonical revision has conflicting bytes')
                    bindings[identity]=doc['sha256'];retain(workspace,report);found[(report['key'],report['edition'])]=report
                except (OSError,ValueError,KeyError,TypeError,UnicodeError) as error:errors.append({'file':str(path.relative_to(workspace.directory)),'error':str(error)})
        reports=list(found.values())
        reports.sort(key=lambda r:(r['metadata']['canonical_document']['revision_number'],r['metadata'].get('canonical_factual_review',{}).get('reviewed_at') or r['metadata'].get('canonical_factual_review',{}).get('time') or '',r['edition']),reverse=True)
        # Same canonical content can acquire an exact-bound review delivery. Keep all
        # PDF editions on disk while showing that content version once in navigation.
        versions={}
        for report in reports:
            if request_id is None or report['metadata']['request']['id']==request_id:versions.setdefault(report['key'],report)
        from web.report_editions import attach
        parents={r['metadata']['canonical_document']['revision_id'] for r in reports}
        for report in versions.values():attach(workspace,report,errors,parents)
        from web.report_projection import catalog as projections
        legacy=projections(workspace,request_id);errors.extend(legacy['errors'])
        prepared=list(versions.values())
        covered={(r['metadata']['request']['id'],r['metadata']['country_code'],r['metadata'].get('producer_result',{}).get('revision')) for r in prepared}
        combined=prepared+[r for r in legacy['reports'] if (r['metadata']['request']['id'],r['metadata']['country_code'],r['metadata']['producer_result']['revision']) not in covered]
        from web.report_model import normalize
        from web.report_assets import attach as assets
        for report in combined:normalize(assets(workspace,report))
        combined.sort(key=lambda r:(r['delivery'].get('result_revision',0),r['model']['kind']=='prepared_report',r['metadata']['canonical_document']['revision_number']),reverse=True)
        return {'reports':combined,'errors':errors}


def _fingerprint(workspace):
    paths=[]
    for name in ('reports','report-cache','editorial-cache','report-projections','report-receipts'):
        root=workspace.directory/name
        if root.exists():
            for path in root.rglob('*'):
                if path.is_file() and not any(part.startswith('.') for part in path.relative_to(root).parts) and (name in ('reports','report-receipts') or path.suffix in ('.md','.json') or 'assets' in path.relative_to(root).parts):
                    if path.name.endswith('.manifest.json'):continue
                    stat=path.lstat();paths.append((str(path),stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns))
    for suffix in ('','-wal','-journal'):
        path=workspace.directory/('research.sqlite'+suffix)
        if path.exists():
            stat=path.lstat();paths.append((str(path),stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns))
    return tuple(sorted(paths))


def catalog(workspace,request_id=None):
    # Validation is shared by workspace/cards, inbox, reader and image/PDF routes.
    # Every relevant file/receipt/DB change invalidates; exports do not cause a
    # complete reparse. The marker/path guard still runs for cache hits.
    with workspace.state_lock,closing(workspace.connect()):
        signature=_fingerprint(workspace);cached=getattr(workspace,'_validated_report_catalog',None)
        if cached is None or cached[0]!=signature:
            value=_catalog(workspace)
            workspace._validated_report_catalog=(_fingerprint(workspace),value)
        else:value=cached[1]
        return {'reports':[r for r in value['reports'] if request_id is None or r['metadata']['request']['id']==request_id], 'errors':value['errors']}


def public(report):
    def safe(value):
        if isinstance(value,dict):return {k:safe(v) for k,v in value.items() if not k.endswith('_bytes') and not k.startswith('_') and k!='bundled_editions'}
        if isinstance(value,list):return [safe(v) for v in value]
        return value
    return safe(report)


def get(workspace,key,edition=None):
    if not re.fullmatch('[a-f0-9]{64}',key):raise ValueError('Choose a saved report version')
    current=next((r for r in catalog(workspace)['reports'] if r['key']==key and (edition is None or r['edition']==edition)),None)
    if current is not None:return current
    if edition is not None:
        if not re.fullmatch('[a-f0-9]{64}',edition):raise ValueError('Choose a saved PDF edition')
        path=workspace.directory/'report-cache'/key/edition/'metadata.local.json'
        if not path.is_file():
            from web.report_projection import cached
            projection=workspace.directory/'report-projections'/key/edition/'metadata.local.json'
            if projection.is_file():
                from web.report_assets import attach as assets
                return assets(workspace,cached(workspace,projection))
            raise ValueError('Saved report edition not found')
        from web.report_editions import attach
        from web.report_model import normalize
        from web.report_assets import attach as assets
        return normalize(assets(workspace,attach(workspace,_cached(workspace,path),[])))
    report=next((r for r in catalog(workspace)['reports'] if r['key']==key),None)
    if report is None:raise ValueError('Saved report version not found in this profile')
    return report


def receive_notice(workspace,value):
    if set(value)!={'schema_version','request_id','request_revision','request_sha256','metadata_path','metadata_sha256'} or value['schema_version']!=NOTICE:raise ValueError('Invalid finalized report delivery notice')
    path=member(workspace.directory,value['metadata_path'])
    if not value['metadata_path'].startswith('reports/'):raise ValueError('Report delivery must name private report storage')
    report=validate(workspace,path,expected_metadata_sha=value['metadata_sha256']);request=report['metadata']['request']
    if (request['id'],request['revision'],request['sha256'])!=(value['request_id'],value['request_revision'],value['request_sha256']):raise ValueError('Report delivery request binding mismatch')
    retain(workspace,report)
    immutable(workspace.directory/'report-receipts'/(report['edition']+'.json'),(env.compact(value)+'\n').encode())
    return report['key']


def state(workspace):
    path=regular(workspace.directory/'report-annotations.json')
    return env.loads(path.read_bytes()) if path.exists() else {'annotations':[],'drafts':{}}


def annotations(workspace,key):
    with workspace.state_lock:
        report=get(workspace,key);saved=state(workspace)
        return {'annotations':[a for a in saved['annotations'] if a['report_key']==key],
                'unreconciled':[a for a in saved['annotations'] if a['report_key']!=key and (a['report_id']==report['metadata']['report_id'] or a.get('country_code')==report['metadata']['country_code'])],
                'draft':saved['drafts'].get(key)}


def save_annotation(workspace,payload):
    with workspace.state_lock:
        if not isinstance(payload,dict) or set(payload)-{'key','id','selector','comment','delete'} or not {'key','id'}<=set(payload):raise ValueError('Review the annotation fields')
        env.identifier(payload['id']);report=get(workspace,payload['key']);saved=state(workspace)
        if report['metadata'].get('archived'):raise ValueError('Archived invented reports are read-only; annotations stay in the original archive')
        existing=next((a for a in saved['annotations'] if a['id']==payload['id']),None)
        if existing and existing['report_key']!=payload['key']:raise ValueError('Annotation belongs to another report version')
        if payload.get('delete') is True:
            saved['annotations']=[a for a in saved['annotations'] if a['id']!=payload['id']]
        else:
            selector=payload.get('selector',existing['selector'] if existing else None)
            if not isinstance(selector,dict):raise ValueError('Select a passage before annotating')
            start=selector.get('start');end=selector.get('end')
            if type(start) is not int or type(end) is not int or start<0 or not start<end:raise ValueError('Invalid passage range')
            if selector.get('view') in ('report','editorial'):
                editorial=selector['view']=='editorial'
                if set(selector)!=({'view','block_id','start','end','quote','document'} if editorial else {'view','block_id','start','end','quote'}):raise ValueError('Invalid report passage fields')
                if editorial:
                    from web.report_editions import get as get_edition
                    tree=get_edition(workspace,report,selector['document'])['content']
                else:tree=report['content']
                block=tree['blocks'].get(selector.get('block_id'))
                if block is None:raise ValueError('Passage is not in this canonical report')
                text=block['text']
            elif selector.get('view')=='pdf':
                if set(selector)!={'view','edition','pdf_sha256','page','start','end','quote'}:raise ValueError('Invalid PDF passage fields')
                from web.report_pdf import ensure_pdf,page_data
                edition=get(workspace,payload['key'],selector['edition']);pdf=ensure_pdf(workspace,edition,selector['pdf_sha256'])
                if selector['pdf_sha256']!=pdf['sha256'] or type(selector.get('page')) is not int:raise ValueError('PDF annotation must bind the exact saved PDF/page')
                text=page_data(workspace,edition,selector['page'],pdf_sha256=selector['pdf_sha256'])['text']
            else:raise ValueError('Select text in the report or PDF')
            quote=selector.get('quote')
            if end>len(text) or text[start:end]!=quote or not isinstance(quote,str) or not quote.strip() or not 1<=len(quote)<=1800:raise ValueError('Quoted passage does not match this exact report version (maximum 1800 characters)')
            comment=payload.get('comment',existing['comment'] if existing else '')
            if not isinstance(comment,str) or len(comment)>2000:raise ValueError('Comments must be at most 2000 characters')
            item={'id':payload['id'],'report_key':report['key'],'report_id':report['metadata']['report_id'],'country_code':report['metadata']['country_code'],'request_id':report['metadata']['request']['id'],'canonical_sha256':report['metadata']['canonical_document']['sha256'],
                  'selector':selector,'comment':comment,'created_at':existing['created_at'] if existing else env.now(),'updated_at':env.now()}
            saved['annotations']=[a for a in saved['annotations'] if a['id']!=item['id']]+[item]
        atomic_json(workspace.directory/'report-annotations.json',saved)
        return annotations(workspace,payload['key'])


def prepare_draft(workspace,payload):
    with workspace.state_lock:
        if not isinstance(payload,dict) or set(payload)!={'key','annotation_ids'} or not isinstance(payload['annotation_ids'],list) or not payload['annotation_ids']:raise ValueError('Choose annotations for a feedback draft')
        report=get(workspace,payload['key'])
        if report['metadata'].get('archived'):raise ValueError('Archived invented reports are read-only; annotations stay in the original archive')
        saved=state(workspace);ids=payload['annotation_ids']
        selected=[a for a in saved['annotations'] if a['report_key']==payload['key'] and a['id'] in ids]
        if len(selected)!=len(set(ids)):raise ValueError('Annotations must belong to this report version')
        meta=report['metadata'];doc=meta['canonical_document'];producer=meta.get('producer_result')
        if not producer:raise ValueError('This report has no received finding binding for feedback yet; Marry owns that handoff')
        request=workspace.research.request(meta['request']['id']);result=next(r['envelope'] for r in request['results'] if r['envelope']['digest']==producer['body_sha256'])
        finding=next(f for f in result['findings'] if f['kind']=='country' and f['country_code']==meta['country_code'] and f['finding_revision']==producer['finding_revision'] and ('finding_id' not in producer or f['finding_id']==producer['finding_id']))
        if meta.get('schema_version')=='grad-compass-received-report-projection-1.0' and len(meta.get('finding_reviews',[]))>1:
            origins=[]
            for annotation in selected:
                origin=meta.get('passage_origins',{}).get(annotation['selector'].get('block_id'))
                if origin is None:raise ValueError('Select an original finding passage for feedback; use Advanced finding feedback for PDF or shared context')
                origins.append(origin)
            if any(origin!=origins[0] for origin in origins):raise ValueError('Select annotations from one original finding at a time; no feedback was sent')
            finding=next(f for f in result['findings'] if f['finding_id']==origins[0]['finding_id'] and f['finding_revision']==origins[0]['finding_revision'])
        lines=[report['content']['title'],f"Canonical report v{doc['revision_number']} · {doc['revision_id']} · SHA-256 {doc['sha256']}"]
        for a in selected:
            s=a['selector'];location=('PDF page '+str(s['page']+1)+' · PDF SHA-256 '+s['pdf_sha256']) if s['view']=='pdf' else s['block_id']+(' · editorial edition '+s['document'] if s['view']=='editorial' else '')
            lines.extend(['',location,'“'+s['quote']+'”',a['comment'] or '(Highlight; no comment)'])
        comment='\n'.join(lines)
        if len(comment)>4000:raise ValueError('Selected passages exceed the 4000-character feedback limit. Select fewer annotations; none were sent.')
        draft={'comment':comment,'feedback':{'request_id':request['request']['request_id'],'request_revision':request['request']['revision'],'request_digest':request['request']['digest'],
              'result_id':result['result_id'],'result_digest':result['digest'],'revision':result['revision'],'finding_id':finding['finding_id'],'finding_revision':finding['finding_revision']},
              'annotation_ids':ids,'created_at':env.now()}
        saved['drafts'][payload['key']]=draft;atomic_json(workspace.directory/'report-annotations.json',saved);return draft
