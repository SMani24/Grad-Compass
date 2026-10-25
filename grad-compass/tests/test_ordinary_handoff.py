"""Ordinary handoff structure, coverage and source metadata use invented material."""
from copy import deepcopy
import json,unittest
from pathlib import Path
from uuid import uuid4
import test_local as fixtures
from report_fixtures import receive_country,package
from web import report_projection as projection,report_packages as reports
from web.local import atomic_json,LocalWorkspace
from web.report_delivery import publish
from web.report_export import markdown
from web.report_pdf import ensure_pdf,page_data


class OrdinaryHandoffTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.LocalTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_received_coverage_and_titles_survive_cache_restart_without_inferred_mapping(self):
        self.f.receive(self.f.ack());value=self.f.result();finding=value['findings'][0]
        finding['sources']=[{'source_id':str(uuid4()),'source_revision':'invented-r1','source_url':'https://example.invalid/costs','title':'Invented national cost guide','publisher':'Invented public authority','locator':'Cost section','observed_at':'2026-10-25T00:00:00Z'}]
        finding['coverage']={'costs':{'state':'investigated_unresolved','detail':'Invented regional ranges conflict.','evidence_refs':['XYZ-03'],'applicable_year':'2027 unknown'}}
        original=deepcopy(value);self.f.receive(value);saved=self.f.store.request(self.f.request['request_id'])
        first=projection.build(saved['request'],saved['results'][0]['envelope'],'CAN');projection.retain(self.f.workspace,first)
        reopened=LocalWorkspace(self.f.workspace.directory);report=reports.get(reopened,first['key'],first['edition'])
        costs=next(x for x in report['model']['coverage'] if x['id']=='costs')
        self.assertEqual(costs['state'],'investigated_unresolved');self.assertEqual(costs['unresolved_evidence_refs'],['XYZ-03'])
        self.assertEqual(report['model']['next_stage']['owner'],'Dave')
        source=report['content']['source_inventory'][0];self.assertIn('Invented national cost guide',source['labels']);self.assertEqual(source['publishers'],['Invented public authority'])
        self.assertNotIn('XYZ-03',report['content']['sources']) # Never assume array position maps to a producer key.
        self.assertIn('Invented national cost guide',markdown(reopened,report).decode())
        ensure_pdf(reopened,report);text=page_data(reopened,report,0)
        self.assertEqual(self.f.store.request(self.f.request['request_id']),saved);self.assertEqual(value,original)
    def test_malformed_coverage_is_unknown_without_manufacturing_prose(self):
        self.f.complete();saved=self.f.store.request(self.f.request['request_id']);result=deepcopy(saved['results'][0]['envelope'])
        result['findings'][0]['coverage']={'funding':{'state':'finished','detail':'Not a contract state','evidence_refs':[]}}
        report=projection.build(saved['request'],result,'CAN')
        self.assertEqual(next(x for x in report['model']['coverage'] if x['id']=='funding')['state'],'unknown');self.assertTrue(report['model']['coverage_notes'])
        self.assertIsNone(report['reader']);self.assertFalse(report['model']['capabilities']['overview'])
    def test_new_country_photo_package_validates_receives_offline_and_replays(self):
        result=receive_country(self.f,code='CHL');root,meta=package(self.f,result,code='CHL')
        from PIL import Image
        photo=root/'photo.jpg';Image.new('RGB',(600,400),(20,80,90)).save(photo)
        meta['assets']=[{'kind':'photo','relative_path':'photo.jpg','sha256':reports.digest(photo.read_bytes()),'media_type':'image/jpeg','alt':'Invented fixture swatch, not a real photograph','caption':'Synthetic image for validation only','credit':'Invented fixture author','creator':'Invented fixture author','source_url':'https://example.invalid/photo','license':'Fixture permission','license_url':'https://example.invalid/license','crop':{'x':.4,'y':.6}}]
        meta['asset_delivery']={'state':'available'};atomic_json(root/'metadata.local.json',meta)
        self.assertTrue(publish(self.f.workspace,root,check_only=True)['valid']);receipt=publish(self.f.workspace,root)
        from web.inbox import InboxReceiver
        receiver=InboxReceiver(self.f.workspace,quiet_seconds=0);self.assertFalse(receiver.check()['errors'])
        report=next(r for r in reports.catalog(self.f.workspace)['reports'] if r['model']['kind']=='prepared_report')
        self.assertEqual(report['visuals']['photo']['creator'],'Invented fixture author');body=Path(report['visuals']['photo']['_local_path']).read_bytes()
        self.assertEqual(reports.digest(body),meta['assets'][0]['sha256'])
        self.assertTrue(ensure_pdf(self.f.workspace,report)['path'].exists())
        photo.unlink();self.assertEqual(Path(reports.get(LocalWorkspace(self.f.workspace.directory),report['key'])['visuals']['photo']['_local_path']).read_bytes(),body)
        self.assertEqual(receiver.check()['received'],0)

    def test_legacy_photo_without_caption_uses_supplied_alt_without_mutating_asset(self):
        self.f.complete();saved=self.f.store.request(self.f.request['request_id'])
        report=projection.build(saved['request'],saved['results'][0]['envelope'],'CAN')
        from PIL import Image
        photo=self.f.workspace.directory/'legacy-fixture.jpg';Image.new('RGB',(400,300),(20,80,100)).save(photo)
        asset={'_local_path':str(photo),'sha256':reports.digest(photo.read_bytes()),'alt':'Invented older photograph description','credit':'Invented fixture author','source_url':'https://example.invalid/photo','license':'Fixture permission'}
        report['visuals']={'photo':asset};before=deepcopy(asset)
        pdf=ensure_pdf(self.f.workspace,report)
        text=' '.join(page_data(self.f.workspace,report,0)['text'].split())
        self.assertIn(asset['alt'],text);self.assertIn(asset['credit'],text)
        self.assertEqual(report['visuals']['photo'],before);self.assertNotIn('caption',asset)
        self.assertTrue(pdf['path'].is_file())
    def test_later_asset_delivery_wins_without_changing_old_metadata_or_replay_order(self):
        result=receive_country(self.f);root,meta=package(self.f,result)
        from web.inbox import InboxReceiver
        publish(self.f.workspace,root);receiver=InboxReceiver(self.f.workspace,quiet_seconds=0);receiver.check()
        old=next(r for r in reports.catalog(self.f.workspace)['reports'] if r['model']['kind']=='prepared_report')
        before=old['metadata_bytes'];old_edition=old['edition'];key=old['key']
        # Same canonical and editorial bytes; only a separately published
        # immutable metadata package gains the actual visual.
        from PIL import Image
        photo=root/'image.jpg';Image.new('RGB',(400,300),(10,80,100)).save(photo)
        meta['assets']=[{'kind':'photo','relative_path':'image.jpg','sha256':reports.digest(photo.read_bytes()),'media_type':'image/jpeg','alt':'Invented fixture','caption':'Invented fixture','credit':'Fixture author','source_url':'https://example.invalid/image','license':'Fixture permission'}]
        atomic_json(root/'metadata.local.json',meta);new=publish(self.f.workspace,root);receiver.check()
        selected=reports.get(self.f.workspace,key)
        self.assertEqual(selected['edition'],new['metadata_sha256']);self.assertIn('photo',selected['visuals'])
        self.assertEqual(reports.get(self.f.workspace,key,old_edition)['metadata_bytes'],before)
        path=self.f.workspace.directory/'report-delivery-order.json';order=path.read_bytes();stamp=path.stat().st_mtime_ns
        receiver.check();self.assertEqual(path.read_bytes(),order);self.assertEqual(path.stat().st_mtime_ns,stamp)
        self.assertEqual(reports.get(LocalWorkspace(self.f.workspace.directory),key)['edition'],new['metadata_sha256'])

    def test_photo_failure_and_malformed_metadata_are_explicit(self):
        result=receive_country(self.f);root,meta=package(self.f,result)
        meta['asset_delivery']={'state':'available'};atomic_json(root/'metadata.local.json',meta)
        with self.assertRaisesRegex(ValueError,'bundled photograph'):publish(self.f.workspace,root,check_only=True)
        meta['asset_delivery']={'state':'unavailable'};atomic_json(root/'metadata.local.json',meta)
        with self.assertRaisesRegex(ValueError,'concrete delivery reason'):publish(self.f.workspace,root,check_only=True)
        meta['asset_delivery']={'state':'unavailable','reason':'Invented retrieval failure; author permission unavailable'};atomic_json(root/'metadata.local.json',meta)
        self.assertTrue(publish(self.f.workspace,root,check_only=True)['valid'])
