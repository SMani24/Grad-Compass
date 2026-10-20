"""Private report/annotation checks use invented documents in disposable storage."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import unittest
from uuid import uuid4
from unittest.mock import patch
import test_local as fixtures
import test_profiles as profile_fixtures
from web import report_packages as reports
from web import research_envelopes as env
from web.local import LocalWorkspace,atomic_json
from web.profiles import LocalProfiles
from web.recovery import restore_backup
from web.report_content import parse_report
from web.report_pdf import ensure_pdf,page_data
from web.inbox import InboxReceiver


class ReportPackageTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.LocalTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.workspace=self.fixture.workspace;self.ack,self.result=self.fixture.complete()
        result=self.workspace.research.request(self.fixture.request['request_id'])['results'][0]['envelope']
        self.root=self.workspace.directory/'reports/CAN/report-test/revision-0001';self.root.mkdir(parents=True)
        self.markdown='# Invented test country report\n\n**Prepared:** 20 October 2026\n\n## Overview\n\nAn **invented passage** for testing only. [E01]\n\n## Costs\n\n| Route | Terms |\n| --- | --- |\n| Example | €1,234 historical guide; future terms unknown. [E01] |\n'
        self.evidence='| Ref | Topic | Sources |\n|---|---|---|\n| E01 | Invented test topic | [Example](https://example.org/evidence) |\n'
        (self.root/'report.md').write_text(self.markdown);(self.root/'map.md').write_text(self.evidence)
        self.meta={'schema_version':reports.SCHEMA,'report_id':str(uuid4()),'country_code':'CAN',
          'request':{'id':self.fixture.request['request_id'],'revision':self.fixture.request['revision'],'sha256':self.fixture.request['digest']},
          'canonical_document':{'id':str(uuid4()),'revision_id':str(uuid4()),'revision_number':1,'relative_path':'report.md','sha256':reports.digest(self.markdown.encode())},
          'evidence_map':{'relative_path':'map.md','sha256':reports.digest(self.evidence.encode())},
          'producer_result':{'id':result['result_id'],'revision':result['revision'],'body_sha256':result['digest'],'finding_revision':result['findings'][0]['finding_revision']},
          'canonical_factual_review':{'state':'pending'},'human_approval':{'state':'unknown'},'pdf':None,'attachments':[]}
        self.write();self.report=reports.catalog(self.workspace)['reports'][0]

    def write(self):atomic_json(self.root/'metadata.local.json',self.meta)
    def selector(self):
        block=next(b for b in self.report['content']['blocks'].values() if b['text'].startswith('An invented'))
        return {'view':'report','block_id':block['id'],'start':3,'end':19,'quote':block['text'][3:19]}
    def annotate(self,**changes):
        value={'key':self.report['key'],'id':str(uuid4()),'selector':self.selector(),'comment':'Private test comment'};value.update(changes)
        return reports.save_annotation(self.workspace,value)['annotations'][-1]

    def test_exact_bytes_duplicate_keys_paths_and_request_bindings_rejected(self):
        self.meta['request']['sha256']='0'*64;self.write()
        with self.assertRaisesRegex(ValueError,'request'):reports.validate(self.workspace,self.root/'metadata.local.json')
        self.meta['request']['sha256']=self.fixture.request['digest'];self.meta['canonical_document']['relative_path']='../report.md';self.write()
        with self.assertRaises(ValueError):reports.validate(self.workspace,self.root/'metadata.local.json')
        self.meta['canonical_document']['relative_path']='report.md';self.write();(self.root/'report.md').write_text(self.markdown+' ')
        with self.assertRaisesRegex(ValueError,'digest'):reports.validate(self.workspace,self.root/'metadata.local.json')
        (self.root/'metadata.local.json').write_text('{"schema_version":"x","schema_version":"y"}')
        with self.assertRaises(ValueError):reports.validate(self.workspace,self.root/'metadata.local.json')

    def test_exact_review_and_producer_result_bindings_rejected(self):
        self.meta['canonical_factual_review']={'state':'accepted','review_id':'test-review','canonical_revision_id':str(uuid4()),'canonical_sha256':self.meta['canonical_document']['sha256'],'scope':'canonical report','reviewed_at':'2026-10-20T12:00:00Z'};self.write()
        with self.assertRaisesRegex(ValueError,'exact canonical'):reports.validate(self.workspace,self.root/'metadata.local.json')
        self.meta['canonical_factual_review']={'state':'pending'};self.meta['producer_result']['body_sha256']='0'*64;self.write()
        with self.assertRaisesRegex(ValueError,'producer-result'):reports.validate(self.workspace,self.root/'metadata.local.json')
        result=self.workspace.research.request(self.fixture.request['request_id'])['results'][0]['envelope']
        self.meta['producer_result']['body_sha256']=result['digest'];self.meta['producer_result']['finding_revision']=str(uuid4());self.write()
        with self.assertRaisesRegex(ValueError,'finding revision'):reports.validate(self.workspace,self.root/'metadata.local.json')

    def test_safe_single_tree_preserves_words_evidence_and_dates(self):
        content=parse_report(self.markdown,self.evidence)
        self.assertEqual(content['report_date'],'2026-10-20');self.assertIn('E01',content['sources'])
        self.assertEqual(content['sources']['E01']['links'][0]['url'],'https://example.org/evidence')
        unsafe=parse_report('# Test\n\n<script>alert(1)</script>\n\n[Bad](javascript:alert) **Good**','')
        html=''.join(b['html'] for b in unsafe['blocks'].values());self.assertNotIn('<script>',html);self.assertNotIn('href="javascript:',html);self.assertIn('<b>Good</b>',html)

    def test_annotations_reject_wrong_quotes_and_are_editable_deletable(self):
        bad=self.selector();bad['quote']='Fabricated quote'
        with self.assertRaisesRegex(ValueError,'Quoted passage'):self.annotate(selector=bad)
        a=self.annotate();saved=reports.save_annotation(self.workspace,{'key':self.report['key'],'id':a['id'],'comment':'Edited'})
        self.assertEqual(saved['annotations'][0]['comment'],'Edited');self.assertEqual(saved['annotations'][0]['selector'],a['selector'])
        reopened=LocalWorkspace(self.workspace.directory);self.assertEqual(reports.annotations(reopened,self.report['key'])['annotations'][0]['comment'],'Edited')
        reports.save_annotation(self.workspace,{'key':self.report['key'],'id':a['id'],'delete':True});self.assertEqual(reports.annotations(self.workspace,self.report['key'])['annotations'],[])

    def test_annotations_backup_restore_and_local_profile_isolation(self):
        a=self.annotate();backup=self.workspace.backup();restored=restore_backup(self.workspace.directory/'backups'/backup['name'],self.fixture.root/'restored-report')
        self.assertEqual(reports.annotations(restored,self.report['key'])['annotations'],[a])
        profiles=LocalProfiles(self.workspace.directory);other=profiles.create('Report tests')['profile']['id'];profiles.switch(other)
        self.assertEqual(reports.catalog(profiles.workspace)['reports'],[])
        with self.assertRaises(ValueError):reports.annotations(profiles.workspace,self.report['key'])

    def test_new_version_retains_unreconciled_earlier_annotations_and_pdf(self):
        a=self.annotate();first=ensure_pdf(self.workspace,self.report);before=first['path'].read_bytes()
        old=self.root;self.root=old.parent/'revision-0002';self.root.mkdir();(self.root/'report.md').write_text(self.markdown+'\nNew invented detail.');(self.root/'map.md').write_text(self.evidence)
        self.meta['canonical_document']={**self.meta['canonical_document'],'revision_id':str(uuid4()),'revision_number':2,'sha256':reports.digest((self.markdown+'\nNew invented detail.').encode())};self.write()
        current=reports.catalog(self.workspace)['reports'][0];self.assertNotEqual(current['key'],self.report['key'])
        self.assertEqual(reports.annotations(self.workspace,current['key'])['unreconciled'],[a]);self.assertEqual(first['path'].read_bytes(),before)
        self.assertEqual(reports.get(self.workspace,self.report['key'])['content'],self.report['content'])

    def test_pdf_shared_text_links_geometry_and_digest(self):
        pdf=ensure_pdf(self.workspace,self.report);page=page_data(self.workspace,self.report,0)
        self.assertEqual(pdf['filename'],'can-country-report-2026-10-20-v1.pdf');self.assertEqual(pdf['sha256'],reports.digest(pdf['path'].read_bytes()))
        texts='';links=[]
        for n in range(page['pages']):
            data=page_data(self.workspace,self.report,n);texts+=data['text'];links+=data['links']
            self.assertTrue(all(w['x']>=0 and w['y']>=0 and w['x']+w['width']<=data['width']+1 and w['y']+w['height']<=data['height']+1 for w in data['words']))
        self.assertIn('invented passage',texts);self.assertIn('€1,234',texts);self.assertTrue(any(l.get('url')=='https://example.org/evidence' for l in links))
        self.assertTrue(any(l.get('page',0)>0 for l in links),'Internal evidence destinations must survive page numbering')
        self.assertEqual(ensure_pdf(self.workspace,self.report)['sha256'],pdf['sha256'])

    def test_pdf_annotation_binds_exact_page_digest_and_passage(self):
        data=page_data(self.workspace,self.report,1);word=next(w for w in data['words'] if len(w['text'])>3)
        selector={'view':'pdf','edition':self.report['edition'],'pdf_sha256':data['pdf_sha256'],'page':1,'start':word['start'],'end':word['end'],'quote':data['text'][word['start']:word['end']]}
        a=self.annotate(selector=selector);self.assertEqual(a['selector'],selector)
        selector['pdf_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'exact saved PDF'):self.annotate(selector=selector)

    def test_feedback_draft_quotes_exact_version_without_sending_or_changing_preferences(self):
        before=self.workspace.research.snapshot();choices=self.workspace.country_decisions();a=self.annotate()
        draft=reports.prepare_draft(self.workspace,{'key':self.report['key'],'annotation_ids':[a['id']]})
        self.assertIn(a['selector']['quote'],draft['comment']);self.assertIn(self.meta['canonical_document']['sha256'],draft['comment']);self.assertIn('Private test comment',draft['comment'])
        self.assertEqual(self.workspace.research.snapshot(),before);self.assertEqual(self.workspace.country_decisions(),choices)
        self.assertEqual(self.workspace.research.request(self.fixture.request['request_id'])['feedback'],[])
        self.assertEqual(reports.annotations(LocalWorkspace(self.workspace.directory),self.report['key'])['draft'],draft)

    def test_notice_replay_and_invalid_notice_preserve_history(self):
        notice={'schema_version':reports.NOTICE,'request_id':self.fixture.request['request_id'],'request_revision':self.fixture.request['revision'],'request_sha256':self.fixture.request['digest'],
                'metadata_path':str((self.root/'metadata.local.json').relative_to(self.workspace.directory)),'metadata_sha256':reports.digest((self.root/'metadata.local.json').read_bytes())}
        before=self.workspace.research.request(self.fixture.request['request_id']);inbox=self.workspace.directory/'inbox';inbox.mkdir(exist_ok=True)
        atomic_json(inbox/'report-ready.json',env.packet(notice));receiver=InboxReceiver(self.workspace,quiet_seconds=0);first=receiver.check();self.assertEqual(first['errors'],[])
        self.assertEqual(receiver.check()['received'],0);self.assertEqual(InboxReceiver(self.workspace,quiet_seconds=0).check()['errors'],[])
        self.assertEqual(self.workspace.research.request(self.fixture.request['request_id']),before)
        notice['metadata_sha256']='0'*64;atomic_json(inbox/'invalid-report.json',env.packet(notice));self.assertTrue(receiver.check()['errors'])

    def test_conflicting_canonical_revision_does_not_replace_retained_report(self):
        (self.root/'report.md').write_text(self.markdown+' Changed under the same identity.')
        self.meta['canonical_document']['sha256']=reports.digest((self.markdown+' Changed under the same identity.').encode());self.write()
        catalog=reports.catalog(self.workspace)
        self.assertTrue(catalog['errors']);self.assertEqual(len(catalog['reports']),1)
        self.assertEqual(catalog['reports'][0]['key'],self.report['key'])

    def test_offline_retention_survives_original_sidecar_being_unavailable(self):
        shutil.rmtree(self.workspace.directory/'reports')
        report=reports.get(self.workspace,self.report['key'])
        self.assertEqual(report['content'],self.report['content']);self.assertTrue(ensure_pdf(self.workspace,report)['path'].is_file())

    def test_annotations_keep_the_old_pdf_after_renderer_update(self):
        data=page_data(self.workspace,self.report,1);word=data['words'][0]
        selector={'view':'pdf','edition':self.report['edition'],'pdf_sha256':data['pdf_sha256'],'page':1,'start':word['start'],'end':word['end'],'quote':word['text']}
        a=self.annotate(selector=selector)
        with patch('web.report_pdf.RENDERER','country-print-next-test'):
            ensure_pdf(self.workspace,self.report)
            reports.save_annotation(self.workspace,{'key':self.report['key'],'id':a['id'],'comment':'Still on the retained PDF'})
            self.assertEqual(page_data(self.workspace,self.report,1,pdf_sha256=data['pdf_sha256'])['text'],data['text'])

    def test_pdf_corruption_is_rejected_against_its_inventory(self):
        pdf=ensure_pdf(self.workspace,self.report);pdf['path'].write_bytes(pdf['path'].read_bytes()+b' changed')
        with self.assertRaisesRegex(ValueError,'inventory'):ensure_pdf(self.workspace,self.report)

    def test_annotation_http_endpoint_requires_current_profile_context(self):
        helper=object.__new__(profile_fixtures.ProfileTests);helper.profiles=LocalProfiles(self.workspace.directory)
        value={'key':self.report['key'],'id':str(uuid4()),'selector':self.selector(),'comment':'Managed HTTP check'}
        self.assertEqual(helper.http('/api/reports/annotate',value,**{'X-Grad-Compass-Workspace':''})['status'],403)
        self.assertEqual(helper.http('/api/reports/annotate',value)['status'],200)

    def test_exact_bound_review_updates_disposition_without_reapproving_the_finding(self):
        annotation=self.annotate();original=self.report;old_pdf=ensure_pdf(self.workspace,original)
        previous=self.root;self.root=previous.parent/'reviewed-delivery';self.root.mkdir()
        (self.root/'report.md').write_text(self.markdown);(self.root/'map.md').write_text(self.evidence)
        self.meta['canonical_factual_review']={'state':'accepted_with_caveats','review_id':str(uuid4()),'canonical_revision_id':self.meta['canonical_document']['revision_id'],
          'canonical_sha256':self.meta['canonical_document']['sha256'],'scope':'exact canonical report and editorial evidence map','reviewed_at':'2026-10-20T12:00:00Z'};self.write()
        reviewed=reports.catalog(self.workspace)['reports'][0]
        self.assertEqual(reviewed['key'],original['key']);self.assertNotEqual(reviewed['edition'],original['edition'])
        self.assertEqual(reviewed['metadata']['human_approval']['state'],'unknown')
        self.assertEqual(reports.annotations(self.workspace,reviewed['key'])['annotations'],[annotation])
        self.assertEqual(reports.get(self.workspace,original['key'],original['edition'])['metadata']['canonical_factual_review']['state'],'pending')
        current=self.workspace.research.request(self.fixture.request['request_id'])
        self.assertEqual(current['results'][0]['envelope']['findings'][0]['review_status'],'pending')
        self.assertTrue(old_pdf['path'].is_file())


if __name__=='__main__':unittest.main()
