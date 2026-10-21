"""Self-contained detailed Markdown; original evidence precision is preserved."""
import json


def filename(report,suffix):
    meta=report['metadata'];tree=report['content']
    from web.report_assets import country_name
    import re
    country=re.sub('[^a-z0-9]+','-',country_name(meta['country_code']).lower()).strip('-')
    for kind in ('reader','detailed'):
        edition=report.get(kind)
        if edition and suffix.startswith('-'+kind):suffix=suffix.replace('-'+kind,'-'+kind+'-r'+str(edition['metadata']['revision_number'])+'-'+edition['id'][:8],1)
    if report.get('model',{}).get('kind')=='received_findings':
        return f"{country}-received-findings-{meta.get('report_date') or 'undated'}-result-r{meta['producer_result']['revision']}{suffix}"
    return f"{country}-country-report-{meta.get('report_date') or tree['report_date'] or 'undated'}-v{meta['canonical_document']['revision_number']}{suffix}"


def markdown(workspace,report,include_annotations=False):
    meta=report['metadata'];doc=meta['canonical_document'];review=meta.get('canonical_factual_review',{'state':'pending'})
    detailed=report.get('detailed')
    lines=['# Detailed country report — portable edition','',
      f"{report.get('model',{}).get('version_label') or ('Canonical report v'+str(doc['revision_number']))} · {meta['country_code']} · {meta.get('report_date') or report['content']['report_date'] or 'Report date unknown'}",'',
      'This file contains all available delivered content and its evidence references. It is a bounded report, not exhaustive country coverage. Preparation, original finding review, report review and personal decisions are separate.','',
      f"Factual review: **{review.get('state','pending')}**. Review date: {review.get('reviewed_at') or review.get('time') or 'not supplied'}. Review scope: {review.get('scope') or 'not supplied'}.",
      f"Human approval: **{meta.get('human_approval',{}).get('state','unknown')}**.",
      f"Evidence observed: {meta.get('source_artifact',{}).get('observed_on') or 'see source records below'}. Report date, observation dates and applicable academic years are distinct.",
      'Historical figures, regional categories, conditional awards, unresolved conflicts and calculations retain their original qualifications. Missing target-year terms remain unknown.','',
      ]
    if report.get('model'):
        lines += ['## Delivery, preparation and research coverage','', '```json',json.dumps(report['model'],ensure_ascii=False,indent=2),'```','']
    if detailed:
        dm=detailed['metadata'];lines += [f"Detailed editorial edition r{dm['revision_number']} · factual review **{dm['factual_review']['state']}** · human approval **{dm['human_approval']['state']}**.",
          'The reader PDF is an intentionally shorter rendition of the same canonical origin. Its editorial revision and review are separate from this detailed edition.','',
          '## Complete delivered detailed edition','',detailed['document_bytes'].decode('utf-8'),'']
    else:lines+=['## Canonical report (complete)','',report['canonical_bytes'].decode('utf-8'),'']
    if not detailed or report['evidence_bytes'].decode('utf-8') not in detailed['document_bytes'].decode('utf-8'):
        lines+=['## Editorial evidence map (complete)','',
      'E references preserve the producer’s editorial topic mappings. Original inbox sources remain finding-level; this export does not invent claim-level support or turn an earlier source-artifact review into approval of this report.','',
      (('```json\n'+report['evidence_bytes'].decode('utf-8')+'\n```') if report['evidence_bytes'].lstrip().startswith(b'{') else report['evidence_bytes'].decode('utf-8')),'']
    lines+=['## Public source records from the bound country finding','']
    finding=report.get('finding') or {}
    # Include all public fields rather than silently dropping observation dates or
    # locators when producer metadata evolves. No private workspace file is needed.
    for source in finding.get('sources',[]):
        lines+=['```json',json.dumps(source,ensure_ascii=False,indent=2),'```','']
    if not finding.get('sources'):lines+=['No additional finding-level source records were supplied.','']
    lines+=['## Stable passage locators','',
      'These locators identify exact passages in the canonical revision below. They identify content, not independently verified claim-to-source bindings. Offsets in private annotations count Unicode code points.','']
    tree=detailed['content'] if detailed else report['content']
    for section in tree['sections']:
        lines+=['### '+section['title'],'']
        for item in section['items']:
            blocks=[b for row in item['rows'] for b in row] if item['type']=='table' else [item['block']]
            for block in blocks:lines+=['- `'+block['id']+'` — '+block['text'][:100].replace('\n',' ')+'…']
    lines+=['## Exact version and review provenance','',
      'Canonical report version and transport result revision are independent identifiers. A result r2 may supply a report v1 or v2. The canonical revision/hash below identify the content in this export.','',
      '```json',json.dumps({'report_id':meta['report_id'],'canonical_document':{k:v for k,v in doc.items() if k not in ('relative_path','media_type')},
        'evidence_map_sha256':meta['evidence_map']['sha256'],'producer_result':meta.get('producer_result'),
        'canonical_factual_review':review,'human_approval':meta.get('human_approval',{'state':'unknown'}),'request':meta['request'],
        'source_artifact':meta.get('source_artifact'),'source_citation_scope':meta.get('source_citation_scope'),
        'editorial_editions':{kind:{'metadata_sha256':report[kind]['id'],**report[kind]['metadata']} for kind in ('reader','detailed') if report.get(kind)}},ensure_ascii=False,indent=2),'```','']
    if include_annotations:
        from web.report_packages import annotations
        lines+=['## Personal annotations (explicitly included)','',
          'Private comments are personal observations, not research findings or factual acceptance. PDF annotations retain their exact PDF hash and page; these can differ from a newly generated reader edition.','']
        for a in annotations(workspace,report['key'])['annotations']:
            selector=a['selector'];lines+=['### Annotation '+a['id'],'','> '+selector['quote'].replace('\n','\n> '),'',a['comment'],'',
              'Location: `'+json.dumps(selector,ensure_ascii=False)+'`','']
    else:lines+=['Personal annotations are not included.','']
    lines+=['Internal review/lineage links and old sibling filenames are historical identifiers. The public source records, detailed research and evidence map are embedded here; no local workspace file is required.','']
    # Producer narrative can mention a local sibling filename. The full report and
    # map are included above; no operational/local path from metadata is exported.
    return ('\n'.join(lines).rstrip()+'\n').encode('utf-8')
