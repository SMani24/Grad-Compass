"""Same-request country corrections are append-only; all data here is invented."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from uuid import uuid4
import test_local as fixtures
from report_fixtures import receive_country
from web import research_envelopes as env
from web.inbox import InboxReceiver
from web.local import LocalWorkspace,atomic_json
from web import report_packages as reports


class CountryResultRevisionTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.LocalTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.w=self.case.workspace;self.first=receive_country(self.case)
        self.raw=json.loads(self.first['_transport']['body'])

    def next_result(self,prior=None):
        prior=prior or self.first
        raw=json.loads(prior['_transport']['body']);raw['result_revision']=prior['revision']+1
        raw['previous_result_revision']=prior['revision'];raw['previous_result_digest']=prior['digest']
        finding=raw['findings'][0];finding['finding_revision']=str(uuid4());finding['record_revision']=str(uuid4())
        finding['summary']='Invented updated research with a new source; no factual acceptance'
        finding['sources'].append({'source_id':str(uuid4()),'source_revision':'invented-later-source','source_url':'https://example.invalid/new-source','locator':'Invented later locator','observed_at':'2026-10-23T00:00:00Z'})
        finding['finding_ref']={k:finding[k] for k in ('country_record_id','record_revision','finding_id','finding_revision','evidence_status','review_status')}
        for key in ('country_record_id','record_revision','finding_id','finding_revision'):finding['review'][key]=finding[key]
        return raw

    def test_complete_country_revisions_preview_receive_replay_restart_and_bind_package(self):
        from report_fixtures import package
        from web.report_delivery import publish
        receiver=InboxReceiver(self.w,quiet_seconds=0)
        original=self.w.research.request(self.case.request['request_id'])['results'][0]['envelope']['_transport']
        prior=self.first
        for n in (2,3):
            raw=self.next_result(prior);packet=env.packet(raw)
            self.assertEqual(self.w.research.preview_response(env.compact(packet))['revision'],n)
            atomic_json(self.w.directory/'inbox'/('later-'+str(n)+'.json'),packet)
            received=receiver.check();self.assertFalse(received['errors']);self.assertEqual(received['received'],1)
            prior=self.w.research.request(self.case.request['request_id'])['results'][-1]['envelope']
            self.assertEqual(prior['findings'][0]['review_status'],'pending');self.assertEqual(prior['findings'][0]['human_approval']['state'],'unknown')
        history=self.w.research.request(self.case.request['request_id'])
        self.assertEqual(history['results'][0]['envelope']['_transport'],original)
        self.assertEqual([x['envelope']['revision'] for x in history['results']],[1,2,3])
        reopened=LocalWorkspace(self.w.directory);again=InboxReceiver(reopened,quiet_seconds=0).check()
        self.assertEqual(again['received'],0);self.assertFalse(again['errors']);self.assertEqual(reopened.research.request(self.case.request['request_id']),history)
        self.case.workspace=reopened
        root,meta=package(self.case,prior,revision=4)
        value=json.loads((root/'evidence.json').read_text());value['sources']['TEST-02']=prior['findings'][0]['sources'][-1];atomic_json(root/'evidence.json',value)
        meta['evidence_map']['sha256']=reports.digest((root/'evidence.json').read_bytes());meta['reader_editorial']['evidence_map_sha256']=meta['evidence_map']['sha256'];atomic_json(root/'metadata.local.json',meta)
        self.assertTrue(publish(reopened,root,check_only=True)['valid']);publish(reopened,root)
        self.assertFalse(InboxReceiver(reopened,quiet_seconds=0).check()['errors'])
        report=next(r for r in reports.catalog(reopened)['reports'] if r['model']['kind']=='prepared_report')
        self.assertEqual(report['metadata']['producer_result']['revision'],3)
        self.assertEqual(report['content']['sources']['TEST-02']['source_record'],prior['findings'][0]['sources'][-1])

    def test_wrong_predecessor_reused_revisions_new_sequence_scope_and_review_are_rejected(self):
        original=self.next_result();variants=[]
        variants.append({**deepcopy(original),'previous_result_digest':'0'*64})
        variants.append({**deepcopy(original),'previous_result_revision':0})
        variants.append({**deepcopy(original),'result_id':str(uuid4())})
        variants.append({**deepcopy(original),'completion':'partial'})
        for field in ('finding_revision','record_revision'):
            changed=deepcopy(original);changed['findings'][0][field]=self.raw['findings'][0][field]
            changed['findings'][0]['finding_ref'][field]=changed['findings'][0][field];changed['findings'][0]['review'][field]=changed['findings'][0][field];variants.append(changed)
        bad=deepcopy(original);bad['findings'][0]['country_code']='CAN';variants.append(bad)
        bad=deepcopy(original);bad['findings'][0]['review']['finding_revision']=str(uuid4());variants.append(bad)
        before=self.w.research.request(self.case.request['request_id'])
        for raw in variants:
            with self.subTest(raw=raw['result_id']):
                with self.assertRaises(ValueError):self.w.research.preview_response(env.compact(env.packet(raw)))
                with self.assertRaises(ValueError):self.w.research.receive(env.packet(raw))
        self.assertEqual(self.w.research.request(self.case.request['request_id']),before)

    def test_post_complete_country_revision_cannot_rebind_to_another_saved_request(self):
        raw=self.next_result();second=self.w.research.submit(self.case.submission(countries=['NZL'],scope='country_conditions',bounds={'institutions':0,'programs':0}))['request']
        raw.update(request_id=second['request_id'],request_revision=second['revision'],request_digest=second['digest'])
        with self.assertRaisesRegex(ValueError,'earlier result'):self.w.research.receive(env.packet(raw))


if __name__=='__main__':unittest.main()
