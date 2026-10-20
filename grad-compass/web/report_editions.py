"""Read immutable producer editorial sidecars without rewriting canonical packages."""
import re
from web import research_envelopes as env
from web.local import regular
from web.report_content import parse_report

SCHEMA='grad-compass-private-editorial-edition-0.1'
REVIEW_STATES=('pending','unknown','accepted','accepted_with_caveats','pass','pass_with_caveats','rejected','needs_correction')


def validate(workspace,report,path,retained=False):
    from web.report_packages import member,checked_file,digest
    raw=member(workspace.directory,str(path.relative_to(workspace.directory))).read_bytes()
    if len(raw)>100_000:raise ValueError('Editorial metadata is too large')
    meta=env.loads(raw);parent=report['metadata'];canonical=parent['canonical_document'];evidence=parent['evidence_map']
    if not isinstance(meta,dict):raise ValueError('Editorial metadata must be a JSON object')
    if meta.get('schema_version')!=SCHEMA or meta.get('edition') not in ('reader','detailed'):raise ValueError('Unknown editorial edition')
    env.identifier(meta.get('document_revision_id'))
    if type(meta.get('revision_number')) is not int or meta['revision_number']<1:raise ValueError('Editorial revision must be a positive integer')
    if (meta.get('country_code'),meta.get('parent_canonical_revision_id'),meta.get('parent_canonical_sha256'),meta.get('evidence_map_revision_id'),meta.get('evidence_map_sha256'))!=(parent['country_code'],canonical['revision_id'],canonical['sha256'],evidence.get('revision_id'),evidence['sha256']):raise ValueError('Editorial edition must bind the exact country, canonical parent and evidence map')
    body=regular(path.parent/'document.md').read_bytes() if retained else checked_file(path.parent,{'relative_path':meta.get('filename'),'sha256':meta.get('sha256')})
    if digest(body)!=meta.get('sha256'):raise ValueError('Editorial digest does not match exact document bytes')
    review=meta.get('factual_review',{})
    if not isinstance(review,dict):raise ValueError('Editorial factual review must be an object')
    state=review.get('state')
    if state not in REVIEW_STATES:raise ValueError('Unknown editorial factual-review state')
    if state not in ('pending','unknown') and (review.get('document_revision_id')!=meta['document_revision_id'] or review.get('document_sha256')!=meta['sha256'] or not review.get('review_id') or not review.get('scope') or not (review.get('reviewed_at') or review.get('time'))):raise ValueError('Editorial factual review must bind its exact document, review record, time and scope')
    approval=meta.get('human_approval',{})
    if not isinstance(approval,dict):raise ValueError('Editorial human approval must be an object')
    if approval.get('state')!='unknown' and (approval.get('document_revision_id')!=meta['document_revision_id'] or approval.get('document_sha256')!=meta['sha256'] or not approval.get('approval_id')):raise ValueError('Editorial human approval must bind its exact document separately')
    return {'id':digest(raw),'metadata':meta,'content':parse_report(body.decode('utf-8'),report['evidence_bytes'].decode('utf-8')),'document_bytes':body,'metadata_bytes':raw}


def retain(workspace,report,edition):
    from web.report_packages import immutable
    root=workspace.directory/'editorial-cache'/report['key']/edition['id']
    immutable(root/'document.md',edition['document_bytes']);immutable(root/'metadata.local.json',edition['metadata_bytes'])


def get(workspace,report,identity):
    if not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{64}',identity):raise ValueError('Choose an exact editorial edition')
    path=workspace.directory/'editorial-cache'/report['key']/identity/'metadata.local.json'
    if not path.is_file():raise ValueError('Saved editorial edition is unavailable for this canonical version')
    edition=validate(workspace,report,path,retained=True)
    if edition['id']!=identity:raise ValueError('Retained editorial identity mismatch')
    return edition


def attach(workspace,report,errors,known_parents=None):
    from web.report_packages import member
    found={};bindings={}
    cache=workspace.directory/'editorial-cache'/report['key']
    candidates=[(p,True) for p in sorted(cache.glob('*/metadata.local.json'))] if cache.exists() else []
    root=workspace.directory/'reports'/report['metadata']['country_code']/'editions'
    if root.exists():candidates += [(p,False) for p in sorted(root.rglob('metadata.local.json')) if not any(part.startswith('.') for part in p.relative_to(root).parts)]
    for path,retained in candidates:
        try:
            # A valid different canonical version belongs to its own catalog entry.
            meta=env.loads(member(workspace.directory,str(path.relative_to(workspace.directory))).read_bytes())
            if not isinstance(meta,dict):raise ValueError('Editorial metadata must be a JSON object')
            if meta.get('parent_canonical_revision_id')!=report['metadata']['canonical_document']['revision_id']:
                if known_parents is not None and meta.get('parent_canonical_revision_id') not in known_parents:raise ValueError('Editorial edition names an unavailable canonical parent')
                continue
            edition=validate(workspace,report,path,retained);identity=(meta['edition'],meta['document_revision_id'])
            if identity in bindings and bindings[identity]!=meta['sha256']:raise ValueError('Editorial revision has conflicting document bytes')
            bindings[identity]=meta['sha256'];retain(workspace,report,edition);found[edition['id']]=edition
        except (OSError,ValueError,KeyError,TypeError,UnicodeError) as error:errors.append({'file':str(path.relative_to(workspace.directory)),'error':str(error)})
    ordered=sorted(found.values(),key=lambda e:(e['metadata']['revision_number'],e['metadata']['factual_review'].get('reviewed_at') or e['metadata']['factual_review'].get('time') or '',e['id']),reverse=True)
    report['editorial_editions']=[public(e) for e in ordered]
    for kind in ('reader','detailed'):report[kind]=next((e for e in ordered if e['metadata']['edition']==kind),None)
    return report


def select(workspace,report,reader=None,detailed=None):
    # Omitted pins mean explicitly no editorial edition. UI exports always carry
    # their selected pins; a concurrent arrival cannot change a displayed export.
    result=dict(report)
    for kind,identity in [('reader',reader),('detailed',detailed)]:
        result[kind]=get(workspace,report,identity) if identity else None
        if result[kind] and result[kind]['metadata']['edition']!=kind:raise ValueError('Choose the matching editorial edition type')
    return result


def public(edition):return {k:v for k,v in edition.items() if not k.endswith('_bytes')}
