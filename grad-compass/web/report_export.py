"""Portable research first, one source inventory, exact provenance in an appendix."""
import json
from web.report_composition import markdown_sections,source_inventory,source_notes,source_tables,review


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
    meta=report['metadata'];doc=meta['canonical_document'];detailed=report.get('detailed')
    tree=detailed['content'] if detailed else report['content']
    raw=(detailed['document_bytes'] if detailed else report['canonical_bytes']).decode('utf-8')
    chunks=markdown_sections(raw);current=review(report,detailed)
    lines=['# '+tree['title'],'']
    # Preserve original substantive Markdown, including all regional qualifications,
    # tables and calculations. Selection is structural, never a generated summary.
    for section in chunks:
        if section['role']=='research':lines.extend([section['markdown'],''])
    if not any(c['role']=='research' for c in chunks):
        lines.extend(['No separate substantive sections were supplied. The retained report context is in the appendix.',''])
    lines+=['## Sources','',
      'References retain the supplied evidence precision. Finding-level records and editorial topic mappings do not establish audited claim-level support. Public URLs and available source records are included below.','']
    inventory=source_inventory(report,tree)
    links={entry['url']:f'S{index:02d}' for index,entry in enumerate(inventory,1)}
    def portable(text):
        for url,key in sorted(links.items(),key=lambda item:len(item[0]),reverse=True):text=text.replace(url,key)
        return text
    for index,source in enumerate(inventory,1):
        refs=', '.join(source['refs']) or ('Finding-level source' if source['records'] else 'Supplied public link; no bound evidence reference')
        lines += [f"### S{index:02d} · {refs}",'',source['url'],'']
        labels=list(dict.fromkeys(source['labels']))
        if labels:lines+=['Source / locator: '+'; '.join(labels),'']
        for record in source['records']:
            # URL has one owner above; distinct source revisions/locators remain.
            record={k:v for k,v in record.items() if k!='source_url'}
            lines+=['```json',json.dumps(record,ensure_ascii=False,indent=2),'```','']
        for identity in source['note_ids']:
            block=tree['blocks'][identity]
            related=', '.join(dict.fromkeys(links[link['url']] for link in block.get('links',[])))
            lines+=['Supplied source note'+(' (links '+related+')' if related else '')+': '+portable(block['text']),'']
    if not inventory:lines+=['No public source records were supplied.','']
    lines+=['## Evidence references and qualifications','']
    for ref,source in tree['sources'].items():
        mapped=', '.join(dict.fromkeys(links[link['url']] for link in source['links'])) or 'No public source link supplied'
        # Keep the complete supplied map qualification/locator, replacing repeated
        # URLs with references to the inventory, not dropping their relationships.
        text=source['text']
        for url,key in sorted(links.items(),key=lambda item:len(item[0]),reverse=True):text=text.replace(url,key)
        lines += ['### '+ref+' · '+source['topic'],'',mapped+' · '+text,'']
    for table in source_tables(tree):
        lines+=['### Supplied source qualifications','']
        for index,row in enumerate(table['rows']):
            cells=[]
            for block in row:
                related=', '.join(dict.fromkeys(links[link['url']] for link in block.get('links',[])))
                cells.append(portable(block['text']).replace('|',r'\|').replace('\n','<br>')+(' ('+related+')' if related else ''))
            lines+=['| '+' | '.join(cells)+' |']
            if index==0:lines+=['| '+' | '.join('---' for _ in cells)+' |']
        lines+=['']
    assigned={identity for source in inventory for identity in source['note_ids']}
    notes=[block for block in source_notes(tree) if block['id'] not in assigned]
    if notes:
        lines+=['### Retained source-context statements','',
          'The following statements are immutable document text. Any review-time wording is historical; the exact-version receipt below records the selected document’s current disposition.','']
        for block in notes:
            text=block['text']
            for url,key in sorted(links.items(),key=lambda item:len(item[0]),reverse=True):text=text.replace(url,key)
            lines+=[text,'']
    lines+=['## Report details and technical appendix','',
      f"Shared origin: canonical report v{doc['revision_number']} · {meta['country_code']} · report date {meta.get('report_date') or tree['report_date'] or 'unknown'}.",
      f"Selected detailed content review: **{current['label']}**. Scope: {current.get('scope') or 'not supplied'}. Review date: {current.get('reviewed_at') or current.get('time') or 'not supplied'}.",
      'The reader PDF is a separately supplied concise rendition of this canonical origin. Delivery, research coverage, content review and human approval are independent. Result revisions and report/edition versions are different identifiers.','']
    model=report.get('model',{})
    for item in model.get('coverage',[]):
        from web.report_composition import COVERAGE_LABELS
        lines+=['- '+item['title']+': '+COVERAGE_LABELS.get(item['state'],item['state'])+' (`'+item['state']+'`) — '+item['detail']+' Evidence: '+(', '.join(item.get('evidence_refs',[])) or 'none supplied')+'. Applicable year: '+str(item.get('applicable_year') or 'not supplied')+'.']
    lines+=['']
    for chunk in chunks:
        if chunk['role']=='context' and chunk['markdown']:lines+=['### Retained document context (historical)','',chunk['markdown'],'']
    evidence=report['evidence_bytes'].decode('utf-8')
    if evidence.lstrip().startswith('{'):
        # Additional supplied precision/date fields stay portable; source records
        # and seven-topic coverage already have one home above.
        value=json.loads(evidence)
        extra={k:v for k,v in value.items() if k not in ('sources','coverage')}
        lines+=['### Evidence-map context','', '```json',json.dumps(extra,ensure_ascii=False,indent=2),'```','']
    else:
        from web.report_content import parse_report
        evidence_tree=parse_report(evidence,'')
        lines+=['### Retained evidence-map context (historical)','']
        for section in evidence_tree['sections']:
            for item in section['items']:
                if item['type']=='table':continue  # The exact ref/topic/source relationships are above.
                block=item['block'];text=block['text']
                for url,key in sorted(links.items(),key=lambda item:len(item[0]),reverse=True):text=text.replace(url,key)
                lines+=[text,'']
    lines+=['### Stable passage locators','',
      'These identify exact original passages, including secondary context, without claiming independent evidence verification. Annotation offsets count Unicode code points.','']
    for section in tree['sections']:
        for item in section['items']:
            blocks=[b for row in item['rows'] for b in row] if item['type']=='table' else [item['block']]
            lines.extend('- `'+block['id']+'`' for block in blocks)
    # Public exact identity/bindings only. Do not export local paths, private briefs,
    # intake, profiles or runtime filenames. Source records have a single home above.
    def public_ref(value):return {k:v for k,v in value.items() if k not in ('relative_path','media_type','filename')}
    provenance={'report_id':meta['report_id'],'canonical_document':public_ref(doc),'evidence_map_sha256':meta['evidence_map']['sha256'],
      'request':meta['request'],'producer_result':meta.get('producer_result'),'canonical_factual_review':meta.get('canonical_factual_review',{'state':'unknown'}),
      'human_approval':meta.get('human_approval',{'state':'unknown'}),'source_artifact':meta.get('source_artifact'),
      'source_citation_scope':meta.get('source_citation_scope'),'scope':model.get('scope'),'bound_result_delivery':model.get('delivery'),
      'preparation':model.get('preparation'),'editorial_editions':{kind:{'metadata_sha256':report[kind]['id'],**public_ref(report[kind]['metadata'])} for kind in ('reader','detailed') if report.get(kind)}}
    latest=[] if meta.get('archived') else workspace.research.request(meta['request']['id'])['results']
    if latest:
        value=latest[-1]['envelope']
        provenance['latest_request_response_at_export']={k:value.get(k) for k in ('result_id','revision','digest','issued_at','completion')}
    lines+=['### Exact version and review receipts','',
      'Bound-result delivery records the historical response used by this immutable package. The latest request response below is a separate delivery snapshot at export; neither implies exhaustive research or human approval.','',
      '```json',json.dumps(provenance,ensure_ascii=False,indent=2),'```','']
    if include_annotations:
        from web.report_packages import annotations
        lines+=['## Personal annotations (explicitly included)','',
          'Private comments are personal observations, not research findings or factual acceptance. PDF notes retain their original PDF hash and page.','']
        for a in annotations(workspace,report['key'])['annotations']:
            selector=a['selector'];lines+=['### Annotation '+a['id'],'','> '+selector['quote'].replace('\n','\n> '),'',a['comment'],'',
              'Location: `'+json.dumps(selector,ensure_ascii=False)+'`','']
    else:lines+=['Personal annotations are not included.','']
    lines+=['All delivered substantive research, public sources, evidence qualifications and exact version receipts needed to read this file are embedded. Historical internal identifiers require no local workspace access.','']
    return ('\n'.join(lines).rstrip()+'\n').encode('utf-8')
