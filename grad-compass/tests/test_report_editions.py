"""Invented editorial documents test exact lineage and private annotation isolation."""
from copy import deepcopy
import json
import shutil
import unittest
from uuid import uuid4
import test_report_packages as report_fixtures
from web import report_packages as packages,report_editions as editions
from web.local import atomic_json
from web.report_reading import preferences
from web.report_export import markdown,filename
from web.report_pdf import ensure_pdf


class EditorialEditionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=report_fixtures.ReportPackageTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.w=self.fixture.workspace;self.report=self.fixture.report
        self.root=self.w.directory/'reports/CAN/editions/reader-one';self.root.mkdir(parents=True)
        self.text='# Invented concise overview\n\n<!-- passage: route-1 -->\n## Useful routes\n\nA rewritten **invented route** with qualifications. [E01]\n'
        self.meta={'schema_version':editions.SCHEMA,'country_code':'CAN','edition':'reader','report_date':'2026-10-20','revision_number':1,
          'document_revision_id':str(uuid4()),'sha256':packages.digest(self.text.encode()),'filename':'reader.md',
          'parent_canonical_revision_id':self.report['metadata']['canonical_document']['revision_id'],'parent_canonical_sha256':self.report['metadata']['canonical_document']['sha256'],
          'evidence_map_revision_id':self.report['metadata']['evidence_map'].get('revision_id'),'evidence_map_sha256':self.report['metadata']['evidence_map']['sha256'],
          'factual_review':{'state':'pending'},'human_approval':{'state':'unknown'}}
        self.write();self.current=packages.catalog(self.w)['reports'][0];self.reader=self.current['reader']

    def write(self):
        (self.root/'reader.md').write_text(self.text);atomic_json(self.root/'metadata.local.json',self.meta)

    def annotation(self):
        b=next(b for b in self.reader['content']['blocks'].values() if b['text'].startswith('A rewritten'))
        return {'key':self.current['key'],'id':str(uuid4()),'selector':{'view':'editorial','document':self.reader['id'],'block_id':b['id'],'start':0,'end':10,'quote':b['text'][:10]},'comment':'Private edition comment'}

    def test_discovery_is_bound_safe_and_public_json_contains_no_bytes(self):
        self.assertEqual(packages.catalog(self.w)['errors'],[])
        self.assertEqual(self.reader['content']['title'],'Invented concise overview')
        self.assertFalse(any('<!--' in b['text'] for b in self.reader['content']['blocks'].values()))
        self.assertEqual(self.current['metadata'],self.report['metadata']);json.dumps(packages.public(self.current))
        from web.report_content import parse_report
        self.assertEqual(parse_report('# Country report\n\n## Routes\n\nA route.\n\n# Evidence map\n\nSources.','')['title'],'Country report')

    def test_wrong_hash_country_parent_evidence_paths_and_duplicate_keys_rejected(self):
        original=deepcopy(self.meta)
        for changes in ({'sha256':'0'*64},{'country_code':'BEL'},{'parent_canonical_revision_id':str(uuid4())},{'parent_canonical_sha256':'0'*64},{'evidence_map_sha256':'0'*64},{'evidence_map_revision_id':str(uuid4())},{'filename':'../reader.md'},{'revision_number':True},{'factual_review':[]},{'human_approval':[]}):
            with self.subTest(changes=changes):
                self.meta={**original,**changes};self.write()
                with self.assertRaises(ValueError):editions.validate(self.w,self.report,self.root/'metadata.local.json')
        (self.root/'metadata.local.json').write_text('{"edition":"reader","edition":"detailed"}')
        with self.assertRaises(ValueError):editions.validate(self.w,self.report,self.root/'metadata.local.json')
        (self.root/'metadata.local.json').write_text('[]')
        self.assertTrue(packages.catalog(self.w)['errors'])

    def test_editorial_review_requires_its_own_exact_bindings(self):
        self.meta['factual_review']={'state':'accepted','review_id':'review-one','scope':'editorial document only','reviewed_at':'2026-10-20T12:00:00Z','document_revision_id':str(uuid4()),'document_sha256':self.meta['sha256']};self.write()
        with self.assertRaisesRegex(ValueError,'exact document'):editions.validate(self.w,self.report,self.root/'metadata.local.json')
        self.meta['factual_review']['document_revision_id']=self.meta['document_revision_id'];self.write();r=packages.catalog(self.w)['reports'][0]
        self.assertEqual(r['reader']['metadata']['factual_review']['state'],'accepted');self.assertEqual(r['metadata']['canonical_factual_review']['state'],'pending');self.assertEqual(r['reader']['metadata']['human_approval']['state'],'unknown')

    def test_new_editorial_text_preserves_earlier_annotations_pdf_and_positions(self):
        a=packages.save_annotation(self.w,self.annotation())['annotations'][0];old=self.reader
        preferences(self.w,{'position':{'key':self.current['key'],'document':old['id'],'anchor':a['selector']['block_id'],'offset':44}})
        pdf=ensure_pdf(self.w,self.current);before=pdf['path'].read_bytes()
        previous=self.root;self.root=previous.parent/'reader-two';self.root.mkdir();self.text=self.text.replace('invented route','changed route');self.meta={**self.meta,'revision_number':2,'document_revision_id':str(uuid4()),'sha256':packages.digest(self.text.encode())};self.write()
        r=packages.catalog(self.w)['reports'][0];self.assertNotEqual(r['reader']['id'],old['id']);self.assertEqual(r['key'],self.current['key'])
        self.assertEqual(packages.annotations(self.w,r['key'])['annotations'],[a]);self.assertEqual(editions.get(self.w,r,old['id'])['document_bytes'],old['document_bytes'])
        self.assertIn(self.current['key']+':'+old['id'],preferences(self.w)['positions']);self.assertNotIn(self.current['key']+':'+r['reader']['id'],preferences(self.w)['positions'])
        self.assertEqual(pdf['path'].read_bytes(),before);self.assertEqual(ensure_pdf(self.w,r,pdf['sha256'])['sha256'],pdf['sha256'])
        bad=self.annotation();bad['selector']['document']=r['reader']['id']
        with self.assertRaises(ValueError):packages.save_annotation(self.w,bad)

    def test_overview_selector_cannot_name_canonical_or_other_document_passages(self):
        a=self.annotation();a['selector']['block_id']=self.fixture.selector()['block_id']
        with self.assertRaises(ValueError):packages.save_annotation(self.w,a)
        a=self.annotation();a['selector']['quote']='rewritten incorrectly'
        with self.assertRaises(ValueError):packages.save_annotation(self.w,a)
        with self.assertRaises(ValueError):preferences(self.w,{'position':{'key':self.current['key'],'document':self.reader['id'],'anchor':self.fixture.selector()['block_id'],'offset':0}})

    def test_pinned_exports_keep_old_edition_after_new_delivery(self):
        old=self.current;original=ensure_pdf(self.w,old)
        self.meta['revision_number']=2;self.meta['document_revision_id']=str(uuid4());self.text+='\nAnother invented detail.\n';self.meta['sha256']=packages.digest(self.text.encode());self.write()
        current=packages.catalog(self.w)['reports'][0];pinned=editions.select(self.w,current,self.reader['id'],None)
        self.assertEqual(ensure_pdf(self.w,pinned)['sha256'],original['sha256']);self.assertNotEqual(ensure_pdf(self.w,current)['path'],original['path'])
        with self.assertRaises(ValueError):editions.select(self.w,current,'0'*64,None)
        with self.assertRaises(ValueError):editions.select(self.w,current,None,self.reader['id'])

    def test_offline_backup_and_restore_keep_editorial_bytes(self):
        from web.recovery import restore_backup
        packages.save_annotation(self.w,self.annotation());backup=self.w.backup();shutil.rmtree(self.w.directory/'reports/CAN/editions')
        self.assertEqual(packages.catalog(self.w)['reports'][0]['reader']['document_bytes'],self.reader['document_bytes'])
        restored=restore_backup(self.w.directory/'backups'/backup['name'],self.fixture.fixture.root/'restored-editorial')
        self.assertEqual(packages.catalog(restored)['reports'][0]['reader']['id'],self.reader['id'])

    def test_detailed_export_includes_actual_editorial_context_and_is_private_by_default(self):
        previous=self.root;self.root=previous.parent/'detailed-one';self.root.mkdir();self.text='# Invented detailed research\n\n## Calculations\n\n10 times 12 is 120; qualified invented arithmetic. [E01]\n';self.meta={**self.meta,'edition':'detailed','document_revision_id':str(uuid4()),'sha256':packages.digest(self.text.encode())};self.write()
        report=packages.catalog(self.w)['reports'][0];text=markdown(self.w,report).decode();self.assertIn(self.text,text);self.assertIn('E01 · Invented test topic',text);self.assertEqual(text.count('https://example.org/evidence'),1)
        packages.save_annotation(self.w,self.annotation());self.assertNotIn('Private edition comment',markdown(self.w,report).decode());self.assertIn('Private edition comment',markdown(self.w,report,True).decode())
        self.assertIn('-detailed-r1-',filename(report,'-detailed.md'));self.assertIn('pending',text);self.assertIn(self.meta['parent_canonical_sha256'],text)

    def test_new_map_keeps_old_editorial_context_annotations_and_pinned_exports(self):
        old=self.current;old_reader=self.reader;oldmap=old['metadata']['evidence_map']['sha256']
        packages.save_annotation(self.w,self.annotation());old_pdf=ensure_pdf(self.w,old)
        parent=self.fixture.root.parent/'new-map';shutil.copytree(self.fixture.root,parent)
        meta=deepcopy(self.fixture.meta);mapping=self.fixture.evidence.replace('Invented test topic','Revised test topic')
        (parent/'map.md').write_text(mapping);meta['evidence_map'].update(sha256=packages.digest(mapping.encode()),revision_id=str(uuid4()))
        doc=meta['canonical_document'];meta['canonical_factual_review']={'state':'pass','review_id':str(uuid4()),'canonical_revision_id':doc['revision_id'],'canonical_sha256':doc['sha256'],'scope':'Invented exact map revision','reviewed_at':'2026-10-22'}
        atomic_json(parent/'metadata.local.json',meta)
        self.root=self.root.parent/'reader-new-map';self.root.mkdir();self.text+='\nA distinct new-map edition.\n'
        self.meta={**self.meta,'revision_number':2,'document_revision_id':str(uuid4()),'sha256':packages.digest(self.text.encode()),'evidence_map_revision_id':meta['evidence_map']['revision_id'],'evidence_map_sha256':meta['evidence_map']['sha256']};self.write()
        catalog=packages.catalog(self.w);self.assertEqual(catalog['errors'],[])
        current=catalog['reports'][0];self.assertNotEqual(current['edition'],old['edition'])
        self.assertEqual(current['reader']['metadata']['revision_number'],2)
        prior=editions.get(self.w,current,old_reader['id'])
        self.assertEqual(prior['content']['sources']['E01']['topic'],'Invented test topic')
        pinned=editions.select(self.w,current,old_reader['id'],None)
        self.assertEqual(pinned['metadata']['evidence_map']['sha256'],oldmap)
        self.assertEqual(ensure_pdf(self.w,pinned)['sha256'],old_pdf['sha256'])
        self.assertEqual(packages.annotations(self.w,current['key'])['annotations'][0]['selector']['document'],old_reader['id'])
        # Historical classification must still reject corrupt retained bytes.
        cached=self.w.directory/'editorial-cache'/old['key']/old_reader['id']/'document.md'
        cached.write_bytes(cached.read_bytes()+b'\nCorrupt test bytes')
        self.assertTrue(any('digest' in e['error'] for e in packages.catalog(self.w)['errors']))

    def test_map_sidecar_is_validated_as_an_artifact_not_a_report(self):
        meta=deepcopy(self.fixture.meta);revision=str(uuid4());meta['evidence_map']['revision_id']=revision
        atomic_json(self.fixture.root/'metadata.local.json',meta)
        root=self.w.directory/'reports/CAN/maps/map-three';root.mkdir(parents=True)
        (root/'map.md').write_text(self.fixture.evidence)
        sidecar={'country_code':'CAN','revision_number':3,'document_revision_id':revision,'filename':'map.md','sha256':meta['evidence_map']['sha256'],'parent_canonical_revision_id':meta['canonical_document']['revision_id'],'parent_canonical_sha256':meta['canonical_document']['sha256'],'factual_review':{'state':'pending'}}
        atomic_json(root/'metadata.local.json',sidecar)
        catalog=packages.catalog(self.w);self.assertEqual(catalog['errors'],[])
        self.assertEqual(catalog['artifacts'][0]['status'],'validated_reference_only')
        self.assertEqual(catalog['artifacts'][0]['factual_review']['state'],'pending')
        sidecar['sha256']='0'*64;atomic_json(root/'metadata.local.json',sidecar)
        self.assertTrue(any('digest' in e['error'] for e in packages.catalog(self.w)['errors']))


if __name__=='__main__':unittest.main()
