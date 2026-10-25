"""Generic finalized private package publication; never invokes research."""
import json
import os
from pathlib import Path
import shutil
from uuid import uuid4
from web import research_envelopes as env
from web.local import private_directory,regular
from web.report_model import PACKAGE,validate_coverage


def validate_extension(workspace,root,report,retained=False):
    from web.report_packages import checked_file,digest,member
    from web.report_editions import validate as editorial
    meta=report['metadata']
    validate_coverage(meta.get('coverage'),report['content'])
    if meta.get('source_citation_scope') not in ('finding','topic','finding_level_with_unreviewed_editorial_topic_mapping'):raise ValueError('State finding-level or editorial-topic evidence precision; claim mappings need a separately agreed format')
    producer=meta.get('producer_result',{})
    if producer.get('finding_id') and report.get('finding',{}).get('finding_id')!=producer['finding_id']:raise ValueError('Report must bind the exact country finding identity')
    if not (meta.get('report_date') or report['content'].get('report_date')):raise ValueError('Report preparation date is required in metadata or supplied report text')
    if meta.get('report_date'):
        from datetime import date
        try:date.fromisoformat(meta['report_date'])
        except (ValueError,TypeError):raise ValueError('Report preparation date must be an ISO calendar date') from None
    if not report['evidence_bytes'].lstrip().startswith(b'{'):raise ValueError('Package 0.2 requires a structured evidence map; Markdown maps remain supported in 0.1')
    if report['evidence_bytes'].lstrip().startswith(b'{'):
        evidence=env.loads(report['evidence_bytes'])
        if evidence.get('country_code')!=meta['country_code'] or evidence.get('coverage')!=meta['coverage'] or evidence.get('citation_scope')!=meta['source_citation_scope']:raise ValueError('Structured evidence country, coverage or precision binding mismatch')
        originals={s['source_id']:s for s in report['finding']['sources']}
        if any(originals.get(s.get('source_id'))!=s for s in evidence['sources'].values()):raise ValueError('Evidence source must match an original bound finding source exactly')
    if not isinstance(meta.get('reader_editorial'),dict):raise ValueError('Ordinary country reports require an exact-bound concise reader editorial reference')
    from web.report_editions import inline_edition
    editions={'reader':inline_edition(workspace,report,root,retained)}
    if not report['content']['blocks'] or not editions['reader']['content']['blocks']:raise ValueError('Supply actual detailed and concise content; empty editions cannot enable reading controls')
    assets=meta.get('assets',[])
    if not isinstance(assets,list) or len(assets)>12:raise ValueError('Use a bounded report asset list')
    delivery=meta.get('asset_delivery')
    if delivery is not None:
        if not isinstance(delivery,dict) or delivery.get('state') not in ('available','unavailable','not_yet_published'):raise ValueError('Declare photo delivery as available, unavailable or not yet published')
        if delivery['state']=='available' and not any(a.get('kind')=='photo' for a in assets if isinstance(a,dict)):raise ValueError('Available photo delivery requires a bundled photograph')
        if delivery['state']!='available' and (not isinstance(delivery.get('reason'),str) or not delivery['reason'].strip()):raise ValueError('A missing photo needs its concrete delivery reason')
    normalized={}
    for asset in assets:
        required={'kind','relative_path','sha256','media_type','alt','caption','credit','source_url','license'}
        if not isinstance(asset,dict) or not required<=set(asset) or asset['kind'] not in ('photo','flag','locator','figure'):raise ValueError('Report visuals need kind, path, hash, alt text, caption, credit, public source and license')
        if asset['media_type'] not in ('image/png','image/jpeg') or any(not isinstance(asset[k],str) or not asset[k].strip() for k in ('alt','caption','credit','source_url','license')) or not asset['source_url'].startswith(('https://','http://')):raise ValueError('Use credited public-source PNG/JPEG visuals; missing imagery is allowed')
        for field in ('creator','license_url'):
            if field in asset and (not isinstance(asset[field],str) or not asset[field].strip()):raise ValueError('Asset creator and license URL must be nonempty when supplied')
        if asset.get('license_url') and not asset['license_url'].startswith('https://'):raise ValueError('Use a public HTTPS license URL')
        crop=asset.get('crop')
        if crop is not None and (not isinstance(crop,dict) or set(crop)!={'x','y'} or any(type(v) not in (int,float) or not 0<=v<=1 for v in crop.values())):raise ValueError('Photo crop uses normalized x/y focal coordinates')
        body=checked_file(root,asset,20_000_000) if not retained else regular(workspace.directory/'report-cache'/report['key']/report['edition']/'assets'/asset['sha256']).read_bytes()
        if digest(body)!=asset['sha256']:raise ValueError('Asset exact bytes mismatch')
        from PIL import Image
        import io
        with Image.open(io.BytesIO(body)) as image:
            if image.format not in ('PNG','JPEG') or image.width>10000 or image.height>10000:raise ValueError('Use a bounded PNG/JPEG report asset')
            image.verify()
        normalized[asset['kind'] if asset['kind']!='figure' else 'figure-'+asset['sha256']]=asset
    for edition in editions.values():
        unknown={r for block in edition['content']['blocks'].values() for r in block['refs']}-set(report['content']['sources'])
        if unknown:raise ValueError('Reader cites evidence references absent from its bound map')
    unknown={r for block in report['content']['blocks'].values() for r in block['refs']}-set(report['content']['sources'])
    if unknown:raise ValueError('Detailed report cites evidence references absent from its bound map')
    report['bundled_editions']=editions;report['assets']=normalized
    return report


def publish(workspace,package,check_only=False):
    """Validate outside storage, exclusively finalize, then announce through inbox."""
    from web.report_packages import validate,digest,immutable,NOTICE
    package=Path(package).absolute()
    if any(p.is_symlink() for p in (package,*package.parents)):raise ValueError('Package directory cannot use links')
    metadata=regular(package/'metadata.local.json');raw=metadata.read_bytes();meta=env.loads(raw)
    # Validation paths stay in a private staging directory within this profile.
    staging=private_directory(workspace.directory/'.report-staging')
    temporary=staging/str(uuid4());private_directory(temporary)
    try:
        count=0;size=0
        for path in package.rglob('*'):
            if path.is_symlink():raise ValueError('Package members cannot use links')
            if not path.is_file():continue
            regular(path);count+=1;size+=path.stat().st_size
            if count>40 or size>60_000_000:raise ValueError('Report package is too large')
            target=temporary/path.relative_to(package);private_directory(target.parent)
            with path.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
            target.chmod(0o600)
        report=validate(workspace,temporary/'metadata.local.json')
        meta=report['metadata'];country=meta['country_code'];identity=report['edition']
        # Reject conflicting identities before any finalized path or notice exists.
        for cached in (workspace.directory/'report-cache').glob('*/*/metadata.local.json'):
            old=env.loads(regular(cached).read_bytes());a=old['canonical_document'];b=meta['canonical_document']
            if (a['id'],a['revision_id'])==(b['id'],b['revision_id']) and a['sha256']!=b['sha256']:raise ValueError('Conflicting immutable canonical revision')
        if meta['schema_version']==PACKAGE:
            allowed={'metadata.local.json',meta['canonical_document']['relative_path'],meta['evidence_map']['relative_path'],meta['reader_editorial']['relative_path']}
            allowed.update(x['relative_path'] for x in meta.get('assets',[]));allowed.update(x['relative_path'] for x in meta.get('attachments',[]))
            if meta.get('pdf'):allowed.add(meta['pdf']['relative_path'])
            actual={str(p.relative_to(temporary)) for p in temporary.rglob('*') if p.is_file()}
            if actual!=allowed:raise ValueError('Package contains missing or unreferenced files; only named report members may be published')

        if check_only:return {'valid':True,'metadata_sha256':identity,'country_code':country}
        parent=private_directory(workspace.directory/'reports'/country/'deliveries');target=parent/identity
        created=not target.exists()
        if target.exists():
            old={str(p.relative_to(target)):digest(p.read_bytes()) for p in target.rglob('*') if p.is_file()}
            new={str(p.relative_to(temporary)):digest(p.read_bytes()) for p in temporary.rglob('*') if p.is_file()}
            if old!=new:raise ValueError('Finalized report package conflicts with existing bytes')
        else:
            os.rename(temporary,target)
        request=meta['request'];notice={'schema_version':NOTICE,'request_id':request['id'],'request_revision':request['revision'],'request_sha256':request['sha256'],
          'metadata_path':str((target/'metadata.local.json').relative_to(workspace.directory)),'metadata_sha256':identity}
        packet=env.packet(notice);inbox=private_directory(workspace.directory/'inbox');immutable(inbox/('report-'+identity+'.json'),(env.compact(packet)+'\n').encode())
        return {'published':created,'metadata_sha256':identity,'notice':'report-'+identity+'.json','country_code':country}
    finally:
        if temporary.exists():shutil.rmtree(temporary)
