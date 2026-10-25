"""Coverage compatibility uses invented responses and disposable private storage."""
from copy import deepcopy
import json
import unittest
from uuid import uuid4
import test_local as fixtures
from web import report_projection as projection, report_packages as reports
from web.local import LocalWorkspace
from web.report_pdf import ensure_pdf


class CoverageProjectionTests(unittest.TestCase):
    def test_accepted_json_coverage_preserves_text_and_review(self):
        fixture=fixtures.LocalTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.complete()
        detail=fixture.store.request(fixture.request['request_id'])
        request=detail['request'];result=detail['results'][0]['envelope']
        original=deepcopy(result)
        for value in ({'study':{'state':'unknown','notes':['Invented',True,3]}}, ['Invented',{'unknown':False}], True, 3, ''):
            with self.subTest(value=value):
                candidate=deepcopy(result);candidate['findings'][0]['coverage']=value
                report=projection.build(request,candidate,'CAN')
                expected=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)
                self.assertEqual(report['model']['scope'],expected+'\nUnknown test coverage')
                self.assertEqual(report['metadata']['finding_reviews'][0]['factual_review'],candidate['findings'][0]['review'])
                self.assertEqual(report['metadata']['finding_reviews'][0]['human_approval'],candidate['findings'][0]['human_approval'])
                self.assertTrue(all(c['state']=='unknown' for c in report['model']['coverage']))
        self.assertEqual(result,original)

    def test_receipt_history_reopen_read_and_pdf_with_structured_revision(self):
        fixture=fixtures.LocalTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.receive(fixture.ack())
        first=fixture.result();first['completion']='partial';fixture.receive(first)
        before=fixture.store.request(fixture.request['request_id'])['results'][0]['envelope']
        second=deepcopy(first);second.update(result_revision=2,previous_result_revision=1,previous_result_digest=before['digest'],completion='complete')
        second['findings'][0]['coverage']={'study':'Invented scope','costs':['unknown']}
        finding=second['findings'][0];revision=str(uuid4())
        finding['finding_revision']=revision
        finding['finding_ref']['finding_revision']=revision
        finding['review']['finding_revision']=revision
        fixture.receive(second)
        saved=deepcopy(fixture.store.request(fixture.request['request_id']))
        reopened=LocalWorkspace(fixture.workspace.directory)
        catalog=reports.catalog(reopened)
        self.assertEqual(catalog['errors'],[])
        self.assertEqual({r['metadata']['producer_result']['revision'] for r in catalog['reports']},{1,2})
        for report in catalog['reports']:
            read=reports.get(reopened,report['key'],report['edition'])
            self.assertTrue(reports.public(read)['content']['blocks'])
            self.assertTrue(ensure_pdf(reopened,read)['path'].read_bytes().startswith(b'%PDF'))
        self.assertEqual(reopened.research.request(fixture.request['request_id']),saved)
        self.assertEqual(projection.catalog(reopened)['errors'],[])
