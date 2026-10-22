"""All report types use one model and the finalized inbox path."""
from copy import deepcopy
import json
import shutil
from pathlib import Path
from uuid import uuid4
import unittest
import test_local as fixtures
from report_fixtures import receive_country,package
from web.local import LocalWorkspace,atomic_json
from web.inbox import InboxReceiver
from web import report_packages as reports
from web.report_delivery import publish
from web.report_export import markdown
from web.report_pdf import ensure_pdf,page_data
from web.recovery import restore_backup


class SharedReportTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.LocalTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.ws=self.case.workspace;self.result=receive_country(self.case)
        self.root,self.meta=package(self.case,self.result)

    def publish(self):
        value=publish(self.ws,self.root);receipt=InboxReceiver(self.ws,quiet_seconds=0).check();self.assertFalse(receipt['errors'],receipt)
        return next(r for r in reports.catalog(self.ws,self.case.request['request_id'])['reports'] if r['model']['kind']=='prepared_report'),value

    def rewrite(self):atomic_json(self.root/'metadata.local.json',self.meta)

    def test_unconfigured_country_complete_receive_model_sources_exports_and_restart(self):
        before=self.ws.research.request(self.case.request['request_id'])
        # A prepared directory alone is not publication, including under reports/.
        staged=self.ws.directory/'reports/NZL/staged';staged.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(self.root,staged)
        view=reports.catalog(self.ws,self.case.request['request_id'])['reports'][0]
        self.assertEqual(view['model']['kind'],'received_findings');self.assertFalse(view['model']['capabilities']['overview'])
        prepared,receipt=self.publish();self.assertTrue(receipt['published'])
        self.assertEqual(prepared['model']['schema_version'],'grad-compass-country-report-view-1.0')
        self.assertEqual(prepared['model']['delivery']['completion'],'complete');self.assertEqual(prepared['model']['preparation']['overview'],'published')
        self.assertEqual(prepared['metadata']['human_approval']['state'],'not_requested');self.assertEqual(prepared['reader']['metadata']['factual_review']['state'],'pending')
        self.assertEqual(prepared['model']['coverage'][2]['state'],'investigated_unresolved')
        self.assertEqual(prepared['visuals'],{})
        source=prepared['content']['sources']['TEST-01'];self.assertEqual(source['source_record'],self.result['findings'][0]['sources'][0])
        self.assertTrue(any('TEST-01' in block['refs'] for block in prepared['reader']['content']['blocks'].values()))
        text=markdown(self.ws,prepared).decode();self.assertIn('https://example.invalid/invented-evidence',text);self.assertIn('not_investigated',text);self.assertIn('not_requested',text)
        pdf=ensure_pdf(self.ws,prepared);page=page_data(self.ws,prepared,0);self.assertIn('Invented NZL',page['text']);self.assertTrue(pdf['path'].exists())
        reopened=LocalWorkspace(self.ws.directory);again=reports.get(reopened,prepared['key'],prepared['edition'])
        self.assertEqual(again['metadata_bytes'],prepared['metadata_bytes']);self.assertEqual(reopened.research.request(self.case.request['request_id']),before)

    def test_replay_keeps_bytes_history_and_exact_annotation_version(self):
        prepared,first=self.publish();block=next(b for b in prepared['reader']['content']['blocks'].values() if 'separately written' in b['text'])
        note={'key':prepared['key'],'id':str(uuid4()),'selector':{'view':'editorial','document':prepared['reader']['id'],'block_id':block['id'],'start':0,'end':12,'quote':block['text'][:12]},'comment':'Private invented comment'}
        reports.save_annotation(self.ws,note);before=(self.ws.directory/'report-annotations.json').read_bytes()
        metadata=next((self.ws.directory/'reports/NZL/deliveries').glob('*/metadata.local.json'));stamp=metadata.stat().st_mtime_ns
        second=publish(self.ws,self.root);InboxReceiver(self.ws,quiet_seconds=0).check()
        self.assertFalse(second['published']);self.assertEqual(first['metadata_sha256'],second['metadata_sha256']);self.assertEqual(metadata.stat().st_mtime_ns,stamp)
        self.assertEqual((self.ws.directory/'report-annotations.json').read_bytes(),before)
        backup=self.ws.backup();restored=restore_backup(self.ws.directory/'backups'/backup['name'],self.case.root/'restored')
        self.assertEqual(reports.annotations(restored,prepared['key'])['annotations'][0]['comment'],'Private invented comment')

    def test_partial_findings_remain_readable_without_inventing_preparation_or_review(self):
        case=fixtures.LocalTests();case.setUp();self.addCleanup(case.doCleanups)
        result=receive_country(case,code='FRA',completion='partial')
        report=reports.catalog(case.workspace,case.request['request_id'])['reports'][0]
        self.assertEqual(report['model']['delivery']['completion'],'partial');self.assertEqual(report['model']['review']['report']['state'],'unknown')
        self.assertEqual(report['model']['preparation']['overview'],'not_yet_published');self.assertIsNone(report['reader'])
        self.assertTrue(all(c['state']=='unknown' for c in report['model']['coverage']))
        self.assertIn('Invented test finding',report['canonical_bytes'].decode())
        text=markdown(case.workspace,report).decode();self.assertIn('not_yet_published',text)
        self.assertIn('-findings.pdf',ensure_pdf(case.workspace,report)['filename'])

    def test_malformed_packages_never_publish_notice_or_promote_scope(self):
        original=deepcopy(self.meta)
        variants=[{'coverage':{}},{'reader_editorial':{**original['reader_editorial'],'parent_canonical_sha256':'0'*64}},
          {'producer_result':{**original['producer_result'],'finding_revision':str(uuid4())}},
          {'canonical_factual_review':{'state':'pass'}},
          {'canonical_factual_review':[]},
          {'human_approval':{'state':'approved'}},
          {'canonical_document':{**original['canonical_document'],'relative_path':'../outside.md'}},
          {'reader_editorial':{**original['reader_editorial'],'sha256':'0'*64}},
          {'source_citation_scope':'claim'}]
        for change in variants:
            self.meta={**deepcopy(original),**change};self.rewrite()
            with self.assertRaises((ValueError,FileNotFoundError)):publish(self.ws,self.root)
        self.assertEqual(list((self.ws.directory/'inbox').glob('report-*.json')),[])
        self.assertEqual(self.ws.research.request(self.case.request['request_id'])['results'][0]['envelope']['digest'],self.result['digest'])
        self.meta=deepcopy(original);(self.root/'reader.md').write_bytes(b'')
        self.meta['reader_editorial']['sha256']=reports.digest(b'');self.rewrite()
        with self.assertRaisesRegex(ValueError,'empty editions'):publish(self.ws,self.root)

    def test_wrong_sources_coverage_refs_duplicate_keys_and_staged_paths_rejected(self):
        self.meta['coverage']['costs']['evidence_refs']=['MISSING-01'];self.rewrite()
        with self.assertRaises(ValueError):publish(self.ws,self.root)
        self.root,self.meta=package(self.case,self.result)
        path=self.root/'evidence.json';evidence=json.loads(path.read_text());evidence['sources']['TEST-01']['source_url']='https://example.invalid/different';atomic_json(path,evidence)
        self.meta['evidence_map']['sha256']=reports.digest(path.read_bytes());self.meta['reader_editorial']['evidence_map_sha256']=self.meta['evidence_map']['sha256'];self.rewrite()
        with self.assertRaisesRegex(ValueError,'original bound'):publish(self.ws,self.root)
        (self.root/'metadata.local.json').write_text('{"schema_version":"a","schema_version":"b"}')
        with self.assertRaises(ValueError):publish(self.ws,self.root)

    def test_exact_report_acceptance_does_not_approve_original_finding_or_human(self):
        doc=self.meta['canonical_document'];reader=self.meta['reader_editorial']
        self.meta['canonical_factual_review']={'state':'pass','review_id':str(uuid4()),'canonical_revision_id':doc['revision_id'],'canonical_sha256':doc['sha256'],'scope':'Exact invented report','reviewed_at':'2026-10-21T00:00:00Z'}
        reader['factual_review']={'state':'pass','review_id':str(uuid4()),'document_revision_id':reader['revision_id'],'document_sha256':reader['sha256'],'scope':'Exact invented reader','reviewed_at':'2026-10-21T00:00:00Z'}
        self.rewrite();report,_=self.publish()
        self.assertEqual(report['model']['review']['report']['state'],'pass')
        self.assertEqual(report['model']['review']['overview']['state'],'pass')
        self.assertEqual(report['model']['review']['findings'][0]['factual_review']['decision'],'pending')
        self.assertEqual(report['model']['review']['human']['state'],'not_requested')

    def test_conflicting_revision_unreferenced_members_and_symlinks_never_publish(self):
        checked=publish(self.ws,self.root,check_only=True);self.assertTrue(checked['valid'])
        self.assertEqual(list((self.ws.directory/'inbox').glob('report-*.json')),[])
        extra=self.root/'unreferenced.txt';extra.write_text('Invented unexpected member')
        with self.assertRaisesRegex(ValueError,'unreferenced'):publish(self.ws,self.root)
        extra.unlink();extra.symlink_to(self.root/'detailed.md')
        with self.assertRaisesRegex(ValueError,'links'):publish(self.ws,self.root)
        extra.unlink();old,_=self.publish();before=list((self.ws.directory/'inbox').glob('report-*.json'))
        path=self.root/'detailed.md';path.write_text(path.read_text()+'\nChanged under the same immutable revision.\n')
        sha=reports.digest(path.read_bytes());self.meta['canonical_document']['sha256']=sha;self.meta['reader_editorial']['parent_canonical_sha256']=sha;self.rewrite()
        with self.assertRaisesRegex(ValueError,'Conflicting immutable'):publish(self.ws,self.root)
        self.assertEqual(list((self.ws.directory/'inbox').glob('report-*.json')),before)
        self.assertEqual(reports.get(self.ws,old['key'])['canonical_bytes'],old['canonical_bytes'])

    def test_new_revision_retains_old_annotations_and_selects_new_content(self):
        old,_=self.publish();block=next(iter(old['content']['blocks'].values()))
        reports.save_annotation(self.ws,{'key':old['key'],'id':str(uuid4()),'selector':{'view':'report','block_id':block['id'],'start':0,'end':8,'quote':block['text'][:8]},'comment':'Keep exact old version'})
        original_root=self.root;self.root,self.meta=package(self.case,self.result,revision=2)
        self.meta['report_id']=old['metadata']['report_id'];self.meta['canonical_document']['id']=old['metadata']['canonical_document']['id'];self.rewrite()
        new,_=self.publish();self.assertNotEqual(new['key'],old['key'])
        self.assertEqual(reports.catalog(self.ws,self.case.request['request_id'])['reports'][0]['key'],new['key'])
        self.assertEqual(reports.annotations(self.ws,new['key'])['unreconciled'][0]['comment'],'Keep exact old version')
        self.assertEqual(reports.get(self.ws,old['key'],old['edition'])['canonical_bytes'],old['canonical_bytes'])

    def test_review_metadata_arrival_invalidates_catalog_without_rewriting_history(self):
        old,_=self.publish();raw=(self.root/'metadata.local.json').read_bytes()
        block=next(iter(old['content']['blocks'].values()))
        reports.save_annotation(self.ws,{'key':old['key'],'id':str(uuid4()),'selector':{'view':'report','block_id':block['id'],'start':0,'end':8,'quote':block['text'][:8]},'comment':'Exact unchanged text'})
        annotations=(self.ws.directory/'report-annotations.json').read_bytes()
        doc=self.meta['canonical_document'];reader=self.meta['reader_editorial']
        self.meta['canonical_factual_review']={'state':'accepted','review_id':str(uuid4()),'canonical_revision_id':doc['revision_id'],'canonical_sha256':doc['sha256'],'scope':'Invented exact report','reviewed_at':'2026-10-21T01:00:00Z'}
        reader['factual_review']={'state':'accepted','review_id':str(uuid4()),'document_revision_id':reader['revision_id'],'document_sha256':reader['sha256'],'scope':'Invented exact reader','reviewed_at':'2026-10-21T01:00:00Z'}
        self.rewrite();new,_=self.publish()
        self.assertEqual(new['key'],old['key']);self.assertNotEqual(new['edition'],old['edition'])
        self.assertEqual(new['reader']['metadata']['factual_review']['state'],'accepted')
        self.assertEqual(new['model']['review']['human']['state'],'not_requested')
        self.assertEqual(new['model']['review']['findings'][0]['factual_review']['decision'],'pending')
        self.assertEqual(reports.get(self.ws,old['key'],old['edition'])['metadata_bytes'],raw)
        self.assertEqual((self.ws.directory/'report-annotations.json').read_bytes(),annotations)
        reopened=LocalWorkspace(self.ws.directory)
        self.assertEqual(reports.get(reopened,new['key'])['edition'],new['edition'])
        # Cache hits may not hide malformed newly-arrived metadata.
        bad=self.ws.directory/'reports/NZL/broken/metadata.local.json';bad.parent.mkdir(parents=True);atomic_json(bad,{'schema_version':'broken'})
        self.assertTrue(any('Unknown private report' in e['error'] for e in reports.catalog(self.ws)['errors']))

    def test_generic_image_is_retained_offline_and_profile_isolation_remains(self):
        from PIL import Image
        asset=self.root/'photo.png';Image.new('RGB',(32,24),(20,90,110)).save(asset)
        self.meta['assets']=[{'kind':'photo','relative_path':'photo.png','sha256':reports.digest(asset.read_bytes()),'media_type':'image/png','alt':'Invented fixture image','caption':'Synthetic test asset','credit':'Test fixture','source_url':'https://example.invalid/fixture-image','license':'CC0'}]
        self.rewrite();report,_=self.publish()
        self.assertEqual(report['visuals']['photo']['credit'],'Test fixture')
        cached=Path(report['visuals']['photo']['_local_path']);self.assertEqual(cached.read_bytes(),asset.read_bytes())
        asset.unlink();again=reports.get(LocalWorkspace(self.ws.directory),report['key'],report['edition'])
        self.assertEqual(again['visuals']['photo']['sha256'],self.meta['assets'][0]['sha256'])
        other=LocalWorkspace(self.case.root/'other-private-profile')
        self.assertEqual(reports.catalog(other)['reports'],[])
        with self.assertRaises(ValueError):reports.get(other,report['key'],report['edition'])

    def test_legacy_findings_preserve_distinct_source_revisions(self):
        from web.report_projection import build
        result=deepcopy(self.result);first=result['findings'][0];second=deepcopy(first)
        second['finding_id']='country:NZL:costs';second['finding_revision']=str(uuid4());second['field']='costs'
        second['sources'][0]['source_revision']='another-invented-revision'
        second['sources'][0]['source_url']='https://example.invalid/another-revision'
        result['findings'].append(second)
        report=build(self.case.request,result,'NZL')
        self.assertEqual(len(report['finding']['sources']),2)
        self.assertEqual(len(report['content']['sources']),2)
        self.assertIn('https://example.invalid/another-revision',markdown(self.ws,report).decode())

    def test_country_navigation_uses_prepared_request_without_rebinding_newer_findings(self):
        from web.report_model import research_snapshot
        prepared,_=self.publish();original=prepared['metadata']['request']['id']
        receive_country(self.case,code='NZL',completion='partial');new_id=self.case.request['request_id']
        self.assertNotEqual(new_id,original)
        view=research_snapshot(self.ws)
        self.assertEqual(view['preferred_country_reports']['NZL']['request_id'],original)
        self.assertEqual(view['preferred_country_reports']['NZL']['key'],prepared['key'])
        self.assertEqual(view['report_preparation'][new_id]['NZL']['kind'],'received_findings')
        self.assertFalse(any(r['model']['kind']=='prepared_report' for r in reports.catalog(self.ws,new_id)['reports']))


if __name__=='__main__':unittest.main()
