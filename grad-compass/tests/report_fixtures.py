"""Invented package fixture; never uses real country research or private reports."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from web import research_envelopes as env
from web.local import atomic_json,private_directory
from web.report_model import PACKAGE,TOPICS
from web.report_packages import digest


def receive_country(case,code='NZL',completion='complete'):
    case.request=case.store.submit(case.submission(countries=[code],scope='country_conditions',bounds={'institutions':0,'programs':0}))['request']
    country=case.country();country['country_code']=code;country['finding_id']='country:'+code+':conditions'
    country['review']['finding_id']=country['finding_id'];country['finding_ref']['finding_id']=country['finding_id']
    country['evidence_status']='supplied';country['finding_ref']['evidence_status']='supplied'
    country['sources']=[{'source_id':str(uuid4()),'source_revision':'invented-source-revision','source_url':'https://example.invalid/invented-evidence','locator':'Invented source; no real factual claim','observed_at':'2026-10-21T00:00:00Z'}]
    result=case.result();result.update(findings=[country],completion=completion)
    inbox=private_directory(case.workspace.directory/'inbox')
    atomic_json(inbox/'ack.json',env.packet(case.ack()));atomic_json(inbox/'result.json',env.packet(result))
    from web.inbox import InboxReceiver
    receipt=InboxReceiver(case.workspace,quiet_seconds=0).check()
    assert not receipt['errors'],receipt
    return case.workspace.research.request(case.request['request_id'])['results'][0]['envelope']


def package(case,result,code='NZL',revision=1):
    root=private_directory(case.root/('invented-package-'+str(uuid4())))
    coverage={key:{'state':'supported_finding','detail':'Invented supplied fixture content; not real country research.','applicable_year':None,'evidence_refs':['TEST-01']} for key,_ in TOPICS}
    coverage['study']={'state':'not_investigated','detail':'This fixture did not investigate study routes.','applicable_year':None,'evidence_refs':[]}
    coverage['funding']={'state':'investigated_unresolved','detail':'Invented unresolved funding question.','applicable_year':None,'evidence_refs':['TEST-01']}
    coverage['timing']={'state':'not_yet_published','detail':'No timing section was delivered.','applicable_year':None,'evidence_refs':[]}
    coverage['questions']={'state':'not_applicable','detail':'No additional fixture questions apply.','applicable_year':None,'evidence_refs':[]}
    canonical='# Invented '+code+' country report\n\nPrepared 21 October 2026. No real country claims.\n\n'+''.join('## '+title+'\n\n'+coverage[key]['detail']+' [TEST-01]\n\n' for key,title in TOPICS)
    reader='# Invented '+code+' concise edition\n\nPrepared 21 October 2026.\n\n## At a glance\n\nAn invented concise passage, separately written for the fixture. [TEST-01]\n'
    (root/'detailed.md').write_text(canonical);(root/'reader.md').write_text(reader)
    finding=next(f for f in result['findings'] if f['kind']=='country' and f['country_code']==code)
    evidence={'schema_version':'grad-compass-private-report-evidence-map-0.2','country_code':code,'citation_scope':'finding_level_with_unreviewed_editorial_topic_mapping','observed_at':'2026-10-21T00:00:00Z','sources':{'TEST-01':deepcopy(finding['sources'][0])},'coverage':coverage,'review_state':'pending'}
    atomic_json(root/'evidence.json',evidence)
    canonical_id=str(uuid4());mapid=str(uuid4());canonical_sha=digest(canonical.encode());mapsha=digest((root/'evidence.json').read_bytes())
    meta={'schema_version':PACKAGE,'report_id':str(uuid4()),'country_code':code,'status':'prepared_pending_factual_review',
      'request':{'id':case.request['request_id'],'revision':case.request['revision'],'sha256':case.request['digest']},
      'producer_result':{'id':result['result_id'],'revision':result['revision'],'body_sha256':result['digest'],'finding_revision':finding['finding_revision']},
      'canonical_document':{'id':str(uuid4()),'revision_id':canonical_id,'revision_number':revision,'relative_path':'detailed.md','sha256':canonical_sha},
      'evidence_map':{'revision_id':mapid,'relative_path':'evidence.json','sha256':mapsha},
      'reader_editorial':{'revision_id':str(uuid4()),'revision_number':revision,'relative_path':'reader.md','sha256':digest(reader.encode()),
        'parent_canonical_revision_id':canonical_id,'parent_canonical_sha256':canonical_sha,'evidence_map_revision_id':mapid,'evidence_map_sha256':mapsha,'factual_review':{'state':'pending'}},
      'coverage':coverage,'source_citation_scope':evidence['citation_scope'],'canonical_factual_review':{'state':'pending'},'human_approval':{'state':'not_requested'},'assets':[]}
    atomic_json(root/'metadata.local.json',meta)
    return root,meta
