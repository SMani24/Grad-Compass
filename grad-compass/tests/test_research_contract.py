"""GRA-55 byte, parser, provenance and immutable-lineage rejection tests."""
from contextlib import closing
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
import unittest
from uuid import uuid4

import test_research
from web import research_envelopes as env
from web.server import handler_for


class ResearchContractTests(unittest.TestCase):
    def setUp(self):
        self.case=test_research.ResearchTests('test_explicit_rejection_and_clarification_do_not_claim_execution')
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.store=self.case.store
        self.request=self.store.submit(self.case.submission())["request"]

    def response(self, choice):
        return self.store.demo_response(self.request["request_id"],choice)

    def receive(self, value):
        return self.store.receive(value["_transport"])

    def complete(self):
        self.receive(self.response("accepted"))
        first=self.response("result-1");self.receive(first)
        complete=self.response("result-2");self.receive(complete)
        return first,complete

    def http(self, raw, path="/api/research/receive"):
        handler=object.__new__(handler_for(self.case.workspace,session_token="synthetic-session"))
        handler.path=path;handler.server=SimpleNamespace(server_port=8765)
        handler.headers={"Host":"127.0.0.1:8765","Origin":"http://127.0.0.1:8765","X-Grad-Compass-Session":"synthetic-session",
                         "Content-Type":"application/json","Content-Length":str(len(raw))}
        handler.rfile=io.BytesIO(raw);result={}
        handler.respond=lambda status,payload:result.update(status=status,payload=payload)
        handler.do_POST();return result

    def test_named_fixture_reproduces_exact_bytes_and_complete_feedback_refresh_lineage(self):
        sys.path.insert(0,str(test_research.APP_ROOT/'scripts'))
        import build_research_fixture
        files=build_research_fixture.build()
        for name,raw in files.items(): self.assertEqual((build_research_fixture.FIXTURE/name).read_bytes(),raw,name)
        manifest=env.loads(files['manifest.json'])
        artifacts={name:env.verify({"body":files[name].decode('utf-8'),"sha256":digest}) for name,digest in manifest['sha256'].items()}
        root,first,last,feedback,refresh=[artifacts[name+'.json'] for name in ('request','result-1','result-2','feedback','refresh')]
        self.assertEqual(first['completion'],'partial');self.assertEqual(last['completion'],'complete')
        self.assertEqual(last['previous_result_digest'],first['digest'])
        self.assertEqual(feedback['result_digest'],last['digest'])
        self.assertEqual(feedback['finding_revision'],last['findings'][0]['finding_revision'])
        self.assertEqual(refresh['parent_request_digest'],root['digest'])
        self.assertEqual(refresh['prior_results'][0]['finding_revision'],feedback['finding_revision'])
        self.assertTrue(all('digest' not in env.loads(raw) for name,raw in files.items() if name!='manifest.json'))

    def test_original_request_and_feedback_bytes_survive_storage_and_export(self):
        request=self.request;first,last=self.complete()
        feedback=self.case.comment(request,last)
        for artifact,identity in ((request,None),(feedback,feedback['feedback_id'])):
            exported=self.store.export(request['request_id'],identity)
            raw=Path(exported['path']).read_bytes()
            self.assertEqual(raw,artifact['_transport']['body'].encode('utf-8'))
            self.assertEqual(hashlib.sha256(raw).hexdigest(),artifact['digest'])
            reference=env.loads(Path(exported['path']).with_suffix('.ref.json').read_bytes())
            self.assertEqual(reference['sha256'],hashlib.sha256(raw).hexdigest())
        with closing(self.store.connect()) as db:
            stored=env.loads(db.execute('SELECT body FROM research_results WHERE revision=2').fetchone()[0])
        self.assertEqual(stored,last['_transport'])

    def test_changed_serialization_is_rejected_with_original_or_recomputed_digest(self):
        ack=self.response('accepted');transport=ack['_transport']
        for body in (transport['body']+'\n',json.dumps(env.loads(transport['body']),indent=2)):
            with self.subTest(body_length=len(body)):
                with self.assertRaises(ValueError):self.store.receive({**transport,'body':body})
                changed={'body':body,'sha256':hashlib.sha256(body.encode()).hexdigest()}
                with self.assertRaises(ValueError):self.store.receive(changed)
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')
        self.assertTrue(self.receive(ack)['changed'])
        result=self.response('result-1')
        changed={**result['_transport'],'body':result['_transport']['body']+' '}
        with self.assertRaises(ValueError):self.store.receive(changed)
        changed['sha256']=hashlib.sha256(changed['body'].encode()).hexdigest()
        with self.assertRaises(ValueError):self.store.receive(changed)

    def test_duplicate_keys_are_rejected_at_body_transport_file_and_http_boundaries(self):
        ack=self.response('accepted');transport=ack['_transport'];body=transport['body']
        duplicate=body.replace('"request_digest":', '"request_digest":"wrong","request_digest":',1)
        forged={'body':duplicate,'sha256':hashlib.sha256(duplicate.encode()).hexdigest()}
        for packet in (forged,):
            with self.assertRaisesRegex(ValueError,'Duplicate JSON'):self.store.receive(packet)
        transport_json=json.dumps(transport)
        duplicate_transport=transport_json[:-1]+',"sha256":'+json.dumps(transport['sha256'])+'}'
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'):self.store.preview_response(duplicate_transport)
        self.assertEqual(self.http(('{"envelope":'+duplicate_transport+'}').encode())['status'],409)
        repeated_http=('{"envelope":'+transport_json+',"envelope":'+transport_json+'}').encode()
        self.assertEqual(self.http(repeated_http)['status'],409)
        for data in (duplicate_transport,json.dumps(forged)):
            raw=json.dumps({'transport_json':data}).encode()
            self.assertEqual(self.http(raw,'/api/research/preview-response')['status'],409)
        self.assertEqual(self.store.preview_response(transport_json),ack)
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')
        self.assertEqual(self.http(json.dumps({'envelope':transport}).encode())['status'],200)

    def test_invalid_utf8_nonfinite_json_and_missing_envelope_fields_are_rejected(self):
        for raw in (b'{"envelope":"\\xff"}', b'{"value":NaN}', b'{"value":Infinity}'):
            if b'\\xff' in raw: raw=raw.replace(b'\\xff',bytes([255]))
            self.assertEqual(self.http(raw)['status'],409)
        with self.assertRaises(ValueError):self.store.preview_response("\ud800")
        with self.assertRaises(ValueError):env.verify({'body':"\ud800",'sha256':'0'*64})
        for body in ({'schema_version':'0.1.0','synthetic':True},
                     {'schema_version':'0.1.0','synthetic':True,'envelope_kind':'result'}):
            with self.assertRaises(ValueError):self.store.receive(env.packet(body))
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')

    def test_country_source_review_and_public_record_metadata_are_required(self):
        self.receive(self.response('accepted'))
        value=self.response('result-1');original=env.loads(value['_transport']['body'])
        mutations=[
            ('record identity',lambda b:b['findings'][0].pop('country_record_id')),
            ('record revision',lambda b:b['findings'][0].pop('record_revision')),
            ('finding revision',lambda b:b['findings'][0].pop('finding_revision')),
            ('finding ref',lambda b:b['findings'][0]['finding_ref'].update(record_revision=env.opaque('wrong'))),
            ('review binding',lambda b:b['findings'][0]['review'].update(finding_revision=env.opaque('wrong'))),
            ('review status',lambda b:b['findings'][0]['review'].update(decision='accepted')),
            ('human approval',lambda b:b['findings'][0]['human_approval'].update(state='approved')),
            ('agent review kind',lambda b:b['findings'][0]['review'].update(kind='human_approval')),
            ('reviewer',lambda b:b['findings'][0]['review'].pop('reviewer_id')),
            ('review time',lambda b:b['findings'][0]['review'].update(reviewed_at='2026-10-15')),
            ('observation',lambda b:b['findings'][0].update(observed_at='2026-10-15')),
            ('source identity',lambda b:b['findings'][0]['sources'][0].pop('source_id')),
            ('source time',lambda b:b['findings'][0]['sources'][0].update(observed_at='2026-10-15')),
            ('source URL',lambda b:b['findings'][0]['sources'][0].update(source_url='http://example.invalid/test')),
            ('page locator',lambda b:b['findings'][0]['sources'][0].pop('locator')),
            ('unknowns',lambda b:b['findings'][0].update(uncertainties=[])),
            ('public institution revision',lambda b:b['public_associations'][0].pop('institution_record_revision')),
            ('public program revision',lambda b:b['public_associations'][1].update(program_record_revision=env.opaque('wrong'))),
            ('public parent',lambda b:b['public_associations'][1].update(institution_id=env.opaque('wrong'))),
            ('public batch digest',lambda b:b['public_associations'][0].update(manifest_sha256='0'*64)),
        ]
        for label,mutate in mutations:
            body=deepcopy(original);mutate(body);packet=env.packet(body)
            with self.subTest(label=label):
                with self.assertRaises(ValueError):env.validate_result(env.verify(packet))
                with self.assertRaises(ValueError):self.store.receive(packet)
        self.assertEqual(self.store.request(self.request['request_id'])['results'],[])
        self.receive(value)

    def test_parent_result_and_finding_revision_bindings_reject_stale_or_cross_request_refs(self):
        first,last=self.complete()
        other=self.store.submit(self.case.submission())['request']
        ref={'result_id':last['result_id'],'revision':2,'digest':last['digest'],'finding_id':'country:CAN','finding_revision':last['findings'][0]['finding_revision']}
        base=self.case.submission(scope='refresh',parent_request_id=self.request['request_id'],parent_request_revision=1,
                                  parent_request_digest=self.request['digest'],prior_results=[ref])
        invalid=[{'parent_request_id':other['request_id']},{'parent_request_revision':2},{'parent_request_revision':True},
                 {'parent_request_digest':'0'*64},{'parent_request_id':None},{'prior_results':[]},{'prior_results':[ref,ref]},
                 {'countries':['FRA']}]
        invalid += [{'prior_results':[{**ref,**change}]} for change in (
            {'result_id':env.opaque('wrong')},{'revision':1},{'revision':True},{'digest':first['digest']},
            {'finding_id':'country:DEU'},{'finding_revision':first['findings'][0]['finding_revision']},
            {'finding_revision':None},{'finding_id':None})]
        before=self.store.snapshot()
        for change in invalid:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):self.store.submit({**base,**change})
                self.assertEqual(self.store.snapshot(),before)
        refresh=self.store.submit(base)['request']
        self.assertEqual(refresh['parent_request_digest'],self.request['digest'])
        self.assertEqual(refresh['prior_results'],[ref])

    def test_feedback_rejects_wrong_request_result_and_finding_revisions(self):
        first,last=self.complete()
        for change in ({'request_revision':True},{'request_revision':2},{'request_digest':'0'*64},
                       {'result_digest':first['digest']},{'revision':True},{'result_id':env.opaque('wrong')},
                       {'finding_revision':first['findings'][0]['finding_revision']},{'finding_id':'country:DEU'}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):self.case.comment(self.request,last,**change)
        self.assertEqual(self.store.request(self.request['request_id'])['feedback'],[])
        feedback=self.case.comment(self.request,last)
        self.assertEqual(feedback['result_digest'],last['digest'])
        self.assertEqual(feedback['finding_revision'],last['findings'][0]['finding_revision'])

    def test_previous_result_digest_and_complete_state_are_bound(self):
        self.receive(self.response('accepted'))
        first=self.response('result-1');last=self.response('result-2')
        for change in ({'previous_result_digest':'0'*64},{'previous_result_revision':True},
                       {'completion':'partial'},{'result_revision':3},{'synthetic':False}):
            body=env.loads(last['_transport']['body']);body.update(change)
            with self.subTest(change=change):
                with self.assertRaises(ValueError):self.store.receive(env.packet(body))
        with self.assertRaises(ValueError):self.receive(last)
        self.receive(first);self.receive(last)
        self.assertFalse(self.receive(first)['changed'])
        self.assertEqual(self.store.latest_country('CAN')['source_revision'],'demo-CAN-r2')

    def test_legacy_history_is_preserved_without_relabeling_or_migrating_its_digest(self):
        identity=str(uuid4())
        body={'private_schema_version':'0.1.0','synthetic':True,'envelope_kind':'request','request_id':identity,
              'revision':1,'created_at':'2026-10-14T12:00:00Z','owner_id':env.opaque('legacy-owner'),'profile_reference':None,
              'countries':['CAN'],'scope':'country_conditions','preferences':{key:None for key in env.PREFERENCE_FIELDS},
              'limits':None,'context':None,'parent_request_id':None,'prior_results':[]}
        legacy=env.compact({**body,'digest':env.fingerprint(body)})
        with closing(self.store.connect()) as db,db:
            db.execute('INSERT INTO research_requests VALUES(?,?,?,?)',(identity,str(uuid4()),'legacy-submission',legacy))
        self.store.save_country({'country_code':'CAN','watched':True,'note':'Keep existing state'})
        view=self.store.request(identity)['request'];self.assertTrue(view['legacy'])
        for operation in (lambda:self.store.export(identity),lambda:self.store.demo_response(identity,'accepted')):
            with self.assertRaises(ValueError):operation()
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT body FROM research_requests WHERE id=?',(identity,)).fetchone()[0],legacy)
        self.assertEqual(self.store.snapshot()['countries']['CAN']['note'],'Keep existing state')
