"""One app report view; publication, coverage and acceptance are independent."""
import re
from web.report_composition import COVERAGE_LABELS,observation_dates

VERSION='grad-compass-country-report-view-1.0'
PACKAGE='grad-compass-private-report-package-0.2'
TOPICS=(('overview','At a glance'),('study','Study routes and language'),('funding','Funding and what it covers'),('costs','Tuition, living and upfront costs'),('work','Work and residence conditions'),('timing','Application timing'),('questions','Questions and next steps'))
STATES={'supported_finding','not_investigated','investigated_unresolved','not_yet_published','not_applicable'}


def topic(field):
    if re.search(r'fund|scholar|award',field):return 'funding'
    if re.search(r'cost|tuition|fee|financial_proof|visa_proof',field):return 'costs'
    if re.search(r'work|residence|permit',field):return 'work'
    if re.search(r'language|study_route|english|admission|degree',field):return 'study'
    if re.search(r'timing|deadline|intake|calendar',field):return 'timing'
    return 'overview'


def validate_coverage(value,content):
    if not isinstance(value,dict) or set(value)!={code for code,_ in TOPICS}:raise ValueError('Report coverage must explicitly describe all seven topics')
    for code,item in value.items():
        if not isinstance(item,dict) or not {'state','detail','evidence_refs','applicable_year'}<=set(item)<={'state','detail','evidence_refs','applicable_year','section_ids'}:raise ValueError('Coverage needs state, explanation, evidence references and applicable year')
        if item['state'] not in STATES or not isinstance(item['detail'],str) or not item['detail'].strip() or len(item['detail'])>6000:raise ValueError('Use an explicit, explained report coverage state')
        refs=item['evidence_refs']
        if not isinstance(refs,list) or any(not isinstance(ref,str) or ref not in content['sources'] for ref in refs) or len(set(refs))!=len(refs):raise ValueError('Coverage evidence reference is not in this report map')
        if item['state']=='supported_finding' and not refs:raise ValueError('Supported coverage needs supplied evidence references')
        if item['applicable_year'] is not None and (not isinstance(item['applicable_year'],str) or len(item['applicable_year'])>160):raise ValueError('Use a supplied applicable year or null')
        sections=item.get('section_ids',[])
        if not isinstance(sections,list) or any(s not in {x['id'] for x in content['sections']} for s in sections):raise ValueError('Coverage section reference is not in this report')
    return value


def supplied_coverage(report):
    """Validate received structured statements, without inventing source bindings."""
    values=(report.get('finding') or {}).get('coverage_topics',[])
    output={};notes=[]
    for value in values:
        for code,item in value.items():
            if code not in dict(TOPICS):continue
            if not isinstance(item,dict) or not {'state','detail','evidence_refs','applicable_year'}<=set(item) or item.get('state') not in STATES or not isinstance(item.get('detail'),str) or not item['detail'].strip():
                notes.append('Invalid supplied coverage structure for '+code);continue
            refs=item.get('evidence_refs',[]);year=item.get('applicable_year')
            if not isinstance(refs,list) or any(not isinstance(ref,str) for ref in refs) or len(set(refs))!=len(refs) or (year is not None and not isinstance(year,str)):
                notes.append('Invalid supplied coverage references/year for '+code);continue
            if item['state']=='supported_finding' and not refs:
                notes.append('Supported coverage lacks supplied evidence references for '+code);continue
            supplied={k:item.get(k) for k in ('state','detail','applicable_year')}
            supplied['evidence_refs']=refs
            supplied['unresolved_evidence_refs']=[ref for ref in refs if ref not in report['content']['sources']]
            if code in output and output[code]!=supplied:
                output[code]={'state':'unknown','detail':'Differing supplied coverage statements; inspect the original findings.','evidence_refs':[],'applicable_year':None}
                notes.append('Conflicting supplied coverage for '+code)
            else:output[code]=supplied
    return output,notes


def normalize(report):
    from web.report_composition import enrich_sources
    enrich_sources(report,report['content'])
    for kind in ('reader','detailed'):
        if report.get(kind):enrich_sources(report,report[kind]['content'])
    meta=report['metadata'];projection=meta.get('schema_version')=='grad-compass-received-report-projection-1.0'
    reader=report.get('reader');prepared=not projection
    supplied,coverage_notes=supplied_coverage(report) if projection else ({},[])
    coverage=meta.get('coverage') or {code:supplied.get(code,{'state':'unknown','detail':'Explicit research coverage was not supplied. See the available '+('received findings' if projection else 'report text')+'; missing text does not establish that research was performed.','evidence_refs':[],'applicable_year':None}) for code,_ in TOPICS}
    result=report.get('delivery',{})
    report['model']={'schema_version':VERSION,'kind':'received_findings' if projection else 'prepared_report',
      'version_label':('Received findings · result r'+str(meta['producer_result']['revision'])) if projection else 'Report v'+str(meta['canonical_document']['revision_number']),
      'preparation':{'detailed':'received_findings' if projection else 'published','overview':'published' if reader else 'not_yet_published',
        'overview_reason':None if reader else 'A producer-written concise edition has not been published for this exact version. Read the available findings and existing request progress. Dave’s team owns preparation, review and publication; no duplicate request is needed.'},
      'delivery':result,'coverage':[{'id':code,'title':title,**coverage[code],'label':COVERAGE_LABELS.get(coverage[code]['state'],'Coverage not supplied')} for code,title in TOPICS],
      'review':{'report':meta.get('canonical_factual_review',{'state':'unknown'}),'human':meta.get('human_approval',{'state':'unknown'}),
        'findings':report.get('finding_reviews') or meta.get('finding_reviews',[]),'overview':reader['metadata']['factual_review'] if reader else None},
      'capabilities':{'overview':bool(reader),'content':bool(report['content']['blocks']),'pdf':bool(report['content']['blocks']),
        'pdf_kind':'concise_reader' if reader else 'available_findings' if projection else 'full_report','markdown':True,'annotations':not meta.get('archived',False)},
      'delivery_checks':{'detailed_content':bool(report['content']['blocks']),'concise_content':bool(reader),'coverage_supplied':bool(meta.get('coverage')) or bool(supplied),'photo': 'available' if report.get('visuals',{}).get('photo') or report.get('assets',{}).get('photo') else meta.get('asset_delivery',{}).get('state','not_yet_published'),'photo_reason':meta.get('asset_delivery',{}).get('reason') or ('Country photograph has not been delivered' if not report.get('visuals',{}).get('photo') and not report.get('assets',{}).get('photo') else None)},
      'coverage_notes':coverage_notes,'next_stage':None if reader and prepared else {'owner':'Dave','action':'Prepare, review and publish the bound detailed and concise report editions'},
      'source_precision':meta.get('source_citation_scope','finding'),'observation_dates':observation_dates(report),'assets':report.get('assets',{}),
      'scope':meta.get('research_scope') or (report.get('finding') or {}).get('coverage') or 'Bounded request; exhaustive country coverage is not established.'}
    return report


def research_snapshot(workspace):
    """UI availability is derived separately; research envelopes stay untouched."""
    from web.report_packages import catalog
    snapshot=workspace.research.snapshot();preparation={};available=catalog(workspace)['reports']
    for report in available:
        meta=report['metadata'];values=preparation.setdefault(meta['request']['id'],{})
        values.setdefault(meta['country_code'],{'kind':report['model']['kind'],'version':report['model']['version_label'],
          'date':meta.get('report_date') or report['content']['report_date'],'review':report['model']['review']['report']['state'],'overview':report['model']['preparation']['overview']})
    requests={r['request_id']:r for r in snapshot['requests']}
    prepared=[r for r in available if r['model']['kind']=='prepared_report' and r['metadata']['request']['id'] in requests and not r['metadata'].get('archived')]
    prepared.sort(key=lambda r:(r['metadata'].get('report_date') or r['content']['report_date'] or '',requests[r['metadata']['request']['id']]['created_at'],r['metadata']['canonical_document']['revision_number']),reverse=True)
    preferred={}
    for report in prepared:
        meta=report['metadata'];summary=preparation[meta['request']['id']][meta['country_code']]
        preferred.setdefault(meta['country_code'],{**summary,'request_id':meta['request']['id'],'key':report['key'],'edition':report['edition']})
    if getattr(workspace,'operational',False):
        from web.dispatch import Dispatch
        receipts={entry['request']['id']:{k:entry.get(k) for k in ('id','status','task','error')} for entry in Dispatch(workspace).read()['entries'] if entry.get('request')}
        for request in snapshot['requests']:request['dispatch_receipt']=receipts.get(request['request_id'])
    snapshot['report_preparation']=preparation;snapshot['preferred_country_reports']=preferred
    from web import batch_progress
    for request in snapshot['requests']:
        selected={}
        for report in prepared:
            if report['metadata']['request']['id']==request['request_id']:
                selected.setdefault(report['metadata']['country_code'],report)
        request['country_progress']=batch_progress.countries(request['countries'],selected,request['scope']=='country_conditions' or bool(selected))
        request['batch_progress']=batch_progress.summary(request['country_progress'],request['completion'])
    return snapshot
