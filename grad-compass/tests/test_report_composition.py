"""Composition regressions use invented data through the finalized inbox."""
import json
import re
import unittest
from uuid import uuid4
import test_local as fixtures
from report_fixtures import receive_country,package
from web.report_composition import markdown_sections,sections,source_inventory,observation_dates
from web.report_content import parse_report
from web.report_delivery import publish
from web.report_export import markdown
from web.report_pdf import ensure_pdf,page_data
from web.report_reading import preferences
from web.inbox import InboxReceiver
from web.local import LocalWorkspace,atomic_json
from web import report_packages as reports


class CompositionTests(unittest.TestCase):
    def test_observation_dates_retain_older_and_newer_sources_separately(self):
        report={'metadata':{'source_artifact':{'observed_on':'2026-10-23'}},'finding':{'sources':[{'observed_at':'2026-10-19T10:00:00Z'},{'observed_at':'2026-10-23T11:00:00Z'}]}}
        self.assertEqual(observation_dates(report),['2026-10-19','2026-10-23'])

    def test_unheaded_legacy_content_remains_readable_without_a_fake_summary(self):
        text='# Partial finding\n\nOnly this supplied observation is available.'
        tree=parse_report(text,'')
        self.assertEqual(sections(tree)[0]['items'][0]['block']['text'],'Only this supplied observation is available.')
        self.assertEqual(markdown_sections(text)[0]['role'],'research')

    def test_nested_administration_and_unknown_research_have_consistent_roles(self):
        text='# Fixture\n\nPrepared context\n\n## Seven-topic coverage\n\n| Topic | State |\n|---|---|\n| Study | supported_finding |\n\n### Regional coverage\n\nScope note\n\n## Regional degree routes\n\nKeep this unfamiliar heading.\n\n## Sources and evidence precision\n\n### Source dates\n\nHistorical note\n'
        tree=parse_report(text,'')
        self.assertEqual([s['id'] for s in sections(tree)],['regional-degree-routes'])
        self.assertEqual([c['id'] for c in markdown_sections(text) if c['role']=='research'],['regional-degree-routes'])
        self.assertEqual(tree['composition']['coverage'],['seven-topic-coverage','regional-coverage'])
        self.assertEqual(tree['composition']['sources'],['sources-and-evidence-precision','source-dates'])
        self.assertTrue(any(b['text']=='Scope note' for b in tree['blocks'].values()))

    def test_one_source_inventory_preserves_multiple_mappings_and_source_revisions(self):
        url='https://example.invalid/evidence'
        evidence='|Ref|Topic|Sources|\n|---|---|---|\n|E01|Conditions|[Terms]('+url+')|\n|E02|Questions|[Locator]('+url+')|'
        tree=parse_report('# Fixture\n\n## Questions\n\nOpen. [E01–E02]',evidence)
        records=[{'source_url':url,'source_revision':str(n),'locator':'page '+str(n)} for n in (1,2)]
        inventory=source_inventory({'finding':{'sources':records}},tree)
        self.assertEqual(len(inventory),1);self.assertEqual(inventory[0]['refs'],['E01','E02'])
        self.assertEqual(inventory[0]['records'],records)

    def test_source_qualifications_and_unmapped_public_urls_remain_portable(self):
        case=fixtures.LocalTests();case.setUp();self.addCleanup(case.doCleanups)
        result=receive_country(case);root,meta=package(case,result)
        with (root/'detailed.md').open('a') as f:f.write('''\n## Source guide and evidence precision

- [Invented source](https://example.invalid/invented-evidence), section 3; published July 2026; future applicability unknown.

The [ancillary page](https://example.invalid/ancillary) returned HTTP 403 on 23 October 2026. Retrieval failed; the page is not confirmed broken.

| Reference | Locator | Qualification |
| --- | --- | --- |
| [Invented source](https://example.invalid/invented-evidence) | Page 7, table 2 | Historical 2025 figure; no target-year value |
''')
        meta['canonical_document']['sha256']=reports.digest((root/'detailed.md').read_bytes());meta['reader_editorial']['parent_canonical_sha256']=meta['canonical_document']['sha256'];atomic_json(root/'metadata.local.json',meta)
        publish(case.workspace,root);self.assertFalse(InboxReceiver(case.workspace,quiet_seconds=0).check()['errors'])
        report=next(r for r in reports.catalog(case.workspace)['reports'] if r['model']['kind']=='prepared_report')
        text=markdown(case.workspace,report).decode()
        self.assertEqual(text.count('https://example.invalid/invented-evidence'),1)
        self.assertEqual(text.count('https://example.invalid/ancillary'),1)
        for phrase in ('section 3; published July 2026; future applicability unknown','HTTP 403','not confirmed broken','Page 7, table 2','Historical 2025 figure; no target-year value'):self.assertIn(phrase,text)
        ancillary=next(s for s in report['content']['source_inventory'] if s['url'].endswith('/ancillary'))
        self.assertEqual(ancillary['refs'],[]);self.assertEqual(ancillary['records'],[])
        self.assertIn('Supplied public link; no bound evidence reference',text)
        self.assertEqual(report['content']['composition']['source_list_owner'],'consumer')

    def test_generic_receive_exports_review_and_historical_passages_survive_restart(self):
        case=fixtures.LocalTests();case.setUp();self.addCleanup(case.doCleanups)
        result=receive_country(case);root,meta=package(case,result)
        text='# Invented comparison\n\nPrepared 21 October 2026; awaiting independent review.\n\n## Seven-topic coverage\n\n|Topic|State|\n|---|---|\n|Costs|supported_finding|\n\n## Opportunities and obstacles\n\nInvented useful implication; future eligibility remains unknown. [TEST-01]\n\n## Cost and funding comparison\n\n|Route|Terms|\n|---|---|\n|Invented|10 times 12 is 120; insurance included. [TEST-01]|\n\n## Sources and evidence precision\n\nHistorical review awaiting; source precision is finding-level.\n\n- TEST-01 https://example.invalid/invented-evidence\n'
        for kind,name in [('canonical_document','detailed.md'),('reader_editorial','reader.md')]:
            (root/name).write_text(text);meta[kind]['sha256']=reports.digest(text.encode())
        doc=meta['canonical_document'];editorial=meta['reader_editorial'];editorial['parent_canonical_sha256']=doc['sha256']
        meta['canonical_factual_review']={'state':'pending'}
        editorial['factual_review']={'state':'accepted_with_caveats','review_id':str(uuid4()),'document_revision_id':editorial['revision_id'],'document_sha256':editorial['sha256'],'scope':'Invented reader only, not canonical','reviewed_at':'2026-10-23T00:00:00Z'}
        atomic_json(root/'metadata.local.json',meta);publish(case.workspace,root)
        received=InboxReceiver(case.workspace,quiet_seconds=0).check();self.assertFalse(received['errors'])
        report=reports.catalog(case.workspace)['reports'][0]
        block=next(b for b in report['reader']['content']['blocks'].values() if 'awaiting independent' in b['text'])
        note={'key':report['key'],'id':str(uuid4()),'selector':{'view':'editorial','document':report['reader']['id'],'block_id':block['id'],'start':0,'end':8,'quote':block['text'][:8]},'comment':'Private context annotation'}
        reports.save_annotation(case.workspace,note)
        preferences(case.workspace,{'position':{'key':report['key'],'document':report['reader']['id'],'anchor':block['id'],'offset':12}})
        pdf=ensure_pdf(case.workspace,report);first=page_data(case.workspace,report,0)
        self.assertIn('Invented useful implication',first['text']);self.assertIn('Accepted with caveats',first['text'])
        self.assertNotIn('supported_finding',first['text']);self.assertNotIn('awaiting',first['text']);self.assertNotIn(doc['revision_id'],first['text'])
        pdftext='\n'.join(page_data(case.workspace,report,n)['text'] for n in range(first['pages']))
        self.assertEqual(len(re.findall(r'\bSources\b',pdftext)),1);self.assertIn('Canonical review: pending',' '.join(pdftext.split()))
        md=markdown(case.workspace,report).decode()
        self.assertLess(md.index('Invented useful implication'),md.index('## Sources'))
        self.assertLess(md.index('10 times 12 is 120; insurance included'),md.index('technical appendix'))
        self.assertEqual(md.count('https://example.invalid/invented-evidence'),1)
        self.assertIn('Historical review awaiting',md);self.assertNotIn('Private context annotation',md)
        self.assertIn('Private context annotation',markdown(case.workspace,report,True).decode())
        raw=(case.workspace.directory/'report-annotations.json').read_bytes()
        reopened=LocalWorkspace(case.workspace.directory);again=reports.get(reopened,report['key'])
        self.assertEqual(again['canonical_bytes'],text.encode());self.assertEqual(again['reader']['metadata']['factual_review']['state'],'accepted_with_caveats')
        self.assertEqual(reports.annotations(reopened,report['key'])['annotations'][0]['selector'],note['selector'])
        self.assertEqual(preferences(reopened)['positions'][report['key']+':'+report['reader']['id']]['anchor'],block['id'])
        publish(reopened,root);InboxReceiver(reopened,quiet_seconds=0).check()
        self.assertEqual((reopened.directory/'report-annotations.json').read_bytes(),raw)
        self.assertEqual(ensure_pdf(reopened,again)['sha256'],pdf['sha256'])


if __name__=='__main__':unittest.main()
