"""Operational storage/transport tests use only invented records in disposable directories."""
from contextlib import closing
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from uuid import uuid4

APP_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP_ROOT))
from web import research_envelopes as env
from web.local import LocalWorkspace
from web.recovery import restore_backup
from web.server import DemoWorkspace,handler_for


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='grad-compass-local-test-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.workspace=LocalWorkspace(self.root/'local');self.store=self.workspace.research
        self.request=self.store.submit(self.submission())['request']

    def submission(self,**changes):
        return {'submission_key':str(uuid4()),'countries':['CAN','FRA'],'scope':'universities_programs',
                'preferences':{'intake':'Invented intake'},'remember_preferences':True,'limits':'Test only',
                'context':None,'parent_request_id':None,'prior_results':[],
                'bounds':{'institutions':2,'programs':3},**changes}

    def base(self,**changes):
        return {'schema_version':'0.1.0','synthetic':False,'request_id':self.request['request_id'],
                'request_revision':1,'request_digest':self.request['digest'],**changes}

    def ack(self):
        return self.base(envelope_kind='acknowledgement',ack_id=str(uuid4()),
                         acknowledged_at='2026-10-16T00:00:00Z',state='accepted',execution_progress=None)

    def country(self,field='funding'):
        record=str(uuid4());revision=str(uuid4());finding_revision=str(uuid4());identity='country:CAN:'+field
        value={'kind':'country','country_code':'CAN','field':field,'finding_id':identity,
               'finding_revision':finding_revision,'country_schema_version':'0.1.0','country_record_id':record,
               'record_revision':revision,'source_revision':'test-source','summary':'Invented test finding',
               'observed_at':'2026-10-16T00:00:00Z','coverage':'Unknown test coverage','evidence_status':'unknown',
               'review_status':'pending','review':{'kind':'agent_factual_review','decision':'pending','reviewer_id':None,
               'reviewed_at':None,'country_record_id':record,'record_revision':revision,'finding_id':identity,
               'finding_revision':finding_revision},'human_approval':{'state':'unknown'},'sources':[],
               'uncertainties':['Invented test; no factual acceptance.']}
        value['finding_ref']={k:value[k] for k in ('country_record_id','record_revision','finding_id','finding_revision','evidence_status','review_status')}
        return value

    def result(self,**changes):
        return self.base(envelope_kind='result',result_id=str(uuid4()),result_revision=1,
                         previous_result_revision=None,previous_result_digest=None,issued_at='2026-10-16T00:00:00Z',
                         completion='complete',findings=[self.country(),self.country('costs')],public_associations=[],**changes)

    def public(self,result):
        # Reuse the public, invented exchange example, with a new test batch ID and pending review.
        source=APP_ROOT.parent/'grad-compass-exchange/examples'/('batch-'+env.BATCH_ID)
        identity=str(uuid4());target=self.workspace.directory/'batches'/('batch-'+identity);target.mkdir(mode=0o700)
        manifest=env.loads((source/'manifest.json').read_bytes());manifest['batch_id']=identity
        records={}
        for name in ('institutions.jsonl','programs.jsonl'):
            rows=[env.loads(line) for line in (source/name).read_bytes().splitlines()]
            for row in rows:row['review']={'state':'pending'}
            records[name]=rows;raw=(''.join(env.compact(r)+'\n' for r in rows)).encode()
            (target/name).write_bytes(raw);manifest['sha256'][name]=hashlib.sha256(raw).hexdigest()
        raw=(env.compact(manifest)+'\n').encode();(target/'manifest.json').write_bytes(raw)
        institution=records['institutions.jsonl'][0];program=records['programs.jsonl'][0]
        association={'batch_id':identity,'manifest_sha256':hashlib.sha256(raw).hexdigest(),
                     'institution_id':institution['id'],'institution_record_revision':institution['record_revision'],
                     'program_id':program['id'],'program_record_revision':program['record_revision']}
        findings=[{'kind':'institution','finding_id':'institution:'+institution['id'],'finding_revision':str(uuid4()),
                   'external_id':institution['id'],'country_code':institution['country_code']},
                  {'kind':'program','finding_id':'program:'+program['id'],'finding_revision':str(uuid4()),
                   'external_id':program['id'],'institution_id':institution['id'],'country_code':institution['country_code']}]
        result['findings'].extend(findings);result['public_associations']=[association]
        return target,association

    def receive(self,value):return self.store.receive(env.packet(value))

    def complete(self,public=False):
        ack=self.ack();self.receive(ack);result=self.result()
        if public:self.public(result)
        self.receive(result);return ack,result

    def test_real_reference_exact_bytes_replay_and_persistence_without_expiry(self):
        exported=self.store.export(self.request['request_id']);path=Path(exported['path'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),self.request['digest'])
        reference=env.loads(path.with_suffix('.ref.json').read_bytes())
        self.assertIs(reference['synthetic'],False)
        self.assertEqual(self.store.export(self.request['request_id']),exported)
        self.store.save_country({'country_code':'CAN','watched':True,'note':'Keep my note'})
        self.workspace.country_decisions('CAN','On hold')
        ack,result=self.complete(public=True);before=self.store.snapshot()
        self.assertFalse(self.receive(ack)['changed']);self.assertFalse(self.receive(result)['changed'])
        reopened=LocalWorkspace(self.workspace.directory);reopened.research.clock=lambda:'2099-12-01T00:00:00Z'
        self.assertEqual(reopened.research.snapshot(),before)
        rows=reopened.overview()['universities'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['research']['review'],'pending');self.assertIsNone(rows[0]['latitude'])
        self.assertEqual(len(reopened.university(rows[0]['id'])['programs']),1)
        self.assertEqual(len(reopened.research.latest_country('CAN')['findings']),2)
        self.assertEqual(reopened.country_decisions(),{'CAN':'On hold'})
        self.assertEqual(reference['sha256'],self.request['digest'])
        self.assertEqual(self.workspace.directory.stat().st_mode&0o777,0o700)
        self.assertEqual(path.stat().st_mode&0o777,0o600)

    def test_real_transport_rejects_wrong_scope_duplicate_keys_and_changed_bytes(self):
        value=self.ack();packet=env.packet(value)
        for change in ({**packet,'body':packet['body']+' '},env.packet({**value,'synthetic':True}),
                       env.packet({**value,'request_digest':'0'*64})):
            with self.assertRaises(ValueError):self.store.receive(change)
        duplicate=packet['body'].replace('"state":','"state":"rejected","state":')
        with self.assertRaisesRegex(ValueError,'Duplicate JSON'):
            self.store.receive({'body':duplicate,'sha256':hashlib.sha256(duplicate.encode()).hexdigest()})
        with self.assertRaises(ValueError):env.verify(packet) # Synthetic reader still refuses real payloads.
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')
        with self.assertRaises(ValueError):self.store.demo_response(self.request['request_id'],'accepted')

    def test_request_limits_and_malformed_review_metadata_are_rejected(self):
        for bounds in ({'institutions':True,'programs':1},{'institutions':-1,'programs':1},{'institutions':201,'programs':0},None):
            with self.assertRaises(ValueError):self.store.submit(self.submission(bounds=bounds))
        payload=self.submission();del payload['bounds']
        with self.assertRaises(ValueError):self.store.submit(payload)
        self.receive(self.ack());result=self.result()
        mutations=[lambda f:f.pop('observed_at'),lambda f:f.pop('coverage'),lambda f:f.update(review_status='accepted'),
                   lambda f:f['review'].update(finding_revision=str(uuid4())),lambda f:f.update(sources=[{'source_url':'http://example.invalid'}]),
                   lambda f:f.update(human_approval={'state':'accepted'}),lambda f:f.update(country_code='DEU'),
                   lambda f:f.update(finding_ref={})]
        for mutation in mutations:
            forged=deepcopy(result);mutation(forged['findings'][0])
            with self.assertRaises(ValueError):self.receive(forged)
        with self.assertRaises(ValueError):self.receive({**result,'findings':[result['findings'][0]]*2})
        self.assertEqual(self.store.request(self.request['request_id'])['results'],[])

    def test_associations_bind_actual_batch_parent_revision_and_typed_findings(self):
        self.receive(self.ack());result=self.result();target,association=self.public(result)
        for field,value in (('manifest_sha256','0'*64),('institution_record_revision',str(uuid4())),
                            ('program_record_revision',str(uuid4())),('institution_id',str(uuid4()))):
            forged=deepcopy(result);forged['public_associations'][0][field]=value
            with self.assertRaises(ValueError):self.receive(forged)
        for field,value in (('institution_id',str(uuid4())),('country_code','FRA')):
            forged=deepcopy(result);forged['findings'][-1][field]=value
            with self.assertRaises(ValueError):self.receive(forged)
        forged=deepcopy(result);forged['findings']=forged['findings'][:2]
        with self.assertRaises(ValueError):self.receive(forged)
        limited=self.store.submit(self.submission(bounds={'institutions':0,'programs':0}))['request']
        original=self.request;self.request=limited;self.receive(self.ack());self.request=original
        forged={**result,'request_id':limited['request_id'],'request_digest':limited['digest']}
        with self.assertRaises(ValueError):self.receive(forged)
        self.receive(result);before=self.workspace.overview()
        # Received evidence survives producer intake removal; replay uses retained exact bytes.
        import shutil
        shutil.rmtree(target)
        self.assertEqual(self.workspace.overview(),before)
        self.assertFalse(self.receive(result)['changed'])

    def test_result_feedback_refresh_sequence_retains_bindings_and_prior_results(self):
        self.receive(self.ack());partial=self.result();partial['completion']='partial';first=env.seal(partial)
        self.receive(partial)
        complete={**partial,'result_revision':2,'previous_result_revision':1,'previous_result_digest':first['digest'],'completion':'complete'}
        self.receive(complete);last=env.seal(complete);finding=last['findings'][0]
        fields={'request_id':self.request['request_id'],'request_revision':1,'request_digest':self.request['digest'],
                'result_id':last['result_id'],'revision':2,'result_digest':last['digest'],'finding_id':finding['finding_id'],
                'finding_revision':finding['finding_revision'],'comment':'Please refresh the test source','submission_key':str(uuid4())}
        feedback=self.store.feedback(**fields)
        export=self.store.export(self.request['request_id'],feedback['feedback_id'])
        self.assertIs(env.loads(Path(export['path']).with_suffix('.ref.json').read_bytes())['synthetic'],False)
        ref={'result_id':last['result_id'],'revision':2,'digest':last['digest'],'finding_id':finding['finding_id'],'finding_revision':finding['finding_revision']}
        payload=self.submission(scope='refresh',parent_request_id=self.request['request_id'],parent_request_revision=1,
                                parent_request_digest=self.request['digest'],prior_results=[ref],remember_preferences=False,
                                preferences={'intake':'Request-only exception'})
        refreshed=self.store.submit(payload)['request']
        self.assertEqual(refreshed['parent_request_digest'],self.request['digest'])
        self.assertEqual(self.store.snapshot()['preferences']['intake'],'Invented intake')
        for changes in ({'parent_request_digest':'0'*64},{'prior_results':[{**ref,'finding_revision':str(uuid4())}]}):
            with self.assertRaises(ValueError):self.store.submit({**payload,'submission_key':str(uuid4()),**changes})
        with self.assertRaises(ValueError):self.store.feedback(**{**fields,'submission_key':str(uuid4()),'result_digest':'0'*64})
        with self.assertRaises(ValueError):self.receive({**complete,'result_revision':3,'previous_result_revision':2,'previous_result_digest':last['digest']})
        with self.assertRaises(ValueError):self.receive({**partial,'result_id':str(uuid4())})
        self.assertEqual(len(self.store.request(self.request['request_id'])['results']),2)

    def test_location_provenance_and_unresolved_records_never_need_centroids(self):
        self.complete(public=True);row=self.workspace.overview()['universities'][0];identity=row['research']['external_id']
        self.assertIsNone(row['latitude'])
        value={'status':'verified','campus':'Invented test campus','latitude':40.1,'longitude':-73.2,
               'source_url':'https://example.invalid/test-campus','locator':'Test point feature','observed_at':'2026-10-16T00:00:00Z',
               'uncertainty':'Invented test coordinate, not a real location'}
        for changes in ({'latitude':float('nan')},{'longitude':181},{'latitude':True},{'locator':''},{'source_url':'http://example.invalid'}):
            with self.assertRaises(ValueError):self.workspace.save_location(identity,{**value,**changes})
        self.workspace.save_location(identity,value);self.workspace.save_location(identity,value)
        with closing(self.workspace.connect()) as db:self.assertEqual(db.execute('SELECT count(*) FROM locations').fetchone()[0],1)
        self.assertEqual(self.workspace.overview()['universities'][0]['latitude'],40.1)
        self.workspace.save_location(identity,{**value,'status':'unresolved','uncertainty':'Verification withdrawn'})
        self.assertIsNone(self.workspace.overview()['universities'][0]['latitude'])
        self.assertEqual(len(self.workspace.overview()['universities']),1)

    def test_backup_restore_keeps_exact_research_personal_state_and_locations(self):
        self.store.save_country({'country_code':'CAN','watched':True,'note':'Recovery note'})
        self.workspace.country_decisions('CAN','Shortlisted');self.workspace.display_preferences('extra-large')
        self.store.export(self.request['request_id']);_,result=self.complete(public=True)
        row=self.workspace.overview()['universities'][0]
        self.workspace.save_location(row['research']['external_id'],{'status':'verified','campus':'Test campus',
            'latitude':40.1,'longitude':-73.2,'observed_at':'2026-10-16T00:00:00Z','source_url':'https://example.invalid/map',
            'locator':'Invented test feature','uncertainty':'Test only'})
        finding=result['findings'][0];saved=env.seal(result)
        feedback=self.store.feedback(request_id=self.request['request_id'],request_revision=1,request_digest=self.request['digest'],
            result_id=result['result_id'],revision=1,result_digest=saved['digest'],finding_id=finding['finding_id'],
            finding_revision=finding['finding_revision'],comment='Keep this feedback',submission_key=str(uuid4()))
        self.store.export(self.request['request_id'],feedback['feedback_id'])
        snapshot=self.workspace.backup();source=self.workspace.directory/'backups'/snapshot['name']
        restored=restore_backup(source,self.root/'recovered')
        self.assertEqual(restored.research.snapshot(),self.store.snapshot())
        self.assertEqual(restored.research.request(self.request['request_id']),self.store.request(self.request['request_id']))
        self.assertEqual(restored.overview(),self.workspace.overview())
        self.assertEqual(restored.country_decisions(),{'CAN':'Shortlisted'})
        self.assertEqual(restored.display_preferences(),{'text_size':'extra-large'})
        restored.research.export(self.request['request_id'])
        with self.assertRaises(ValueError):restore_backup(source,restored.directory)
        (source/'country-decisions.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'bytes'):restore_backup(source,self.root/'corrupt')
        self.assertFalse((self.root/'corrupt').exists())

    def test_candidate_scope_and_revision_metadata_cannot_bypass_result_limits(self):
        self.receive(self.ack());result=self.result();_,association=self.public(result)
        institution=next(f for f in result['findings'] if f['kind']=='institution')
        country=result['findings'][0]
        candidate={'schema_version':'producer-candidate-0.1.0','countries':[{'key':'CAN',
            'country_record_id':country['country_record_id'],'country_record_revision':country['record_revision']}],
            'institutions':[{'key':'test-university'}],'programs':[],
            'public_record_bindings':[{'kind':'institution','key':'test-university','id':institution['external_id'],
                'record_revision':association['institution_record_revision']}]}
        result['candidate']=candidate
        for changes in ({'profile':{}},{'schema_version':'unknown'},{'countries':[{'key':'DEU'}]},
                        {'institutions':[{'key':'unbound'}]},{'public_record_bindings':[]}):
            with self.assertRaises(ValueError):self.receive({**result,'candidate':{**candidate,**changes}})
        self.assertTrue(self.receive(result)['changed'])

    def test_partial_results_cannot_reuse_finding_revision_or_expand_cumulative_scope(self):
        self.request=self.store.submit(self.submission(countries=['CAN','AUS'],bounds={'institutions':1,'programs':1}))['request']
        self.receive(self.ack());first=self.result();first['completion']='partial';target,association=self.public(first)
        self.receive(first);original=env.seal(first)
        second={**first,'result_revision':2,'previous_result_revision':1,'previous_result_digest':original['digest']}
        forged=deepcopy(second);forged['findings'][0]['summary']='Changed without a revision'
        with self.assertRaisesRegex(ValueError,'finding revision'):self.receive(forged)
        # Each revision individually contains one institution, but together there would be two.
        other=env.loads((target/'institutions.jsonl').read_bytes().splitlines()[1])
        second['findings']=[{'kind':'institution','country_code':other['country_code'],'external_id':other['id'],
            'finding_id':'institution:'+other['id'],'finding_revision':str(uuid4())}]
        second['public_associations']=[{k:v for k,v in {**association,'institution_id':other['id'],
            'institution_record_revision':other['record_revision']}.items() if not k.startswith('program_')}]
        with self.assertRaisesRegex(ValueError,'Cumulative'):self.receive(second)

    def test_preview_personal_state_preserved_without_modifying_or_mixing_samples(self):
        previous=self.root/'preview'
        subprocess.run([sys.executable,'-B',str(APP_ROOT/'scripts/create_demo.py'),str(previous)],check=True,capture_output=True)
        old=DemoWorkspace(previous);old.research.save_country({'country_code':'CAN','watched':True,'note':'Existing note'})
        old.country_decisions('CAN','Excluded');old.display_preferences('large')
        sample=old.research.submit({k:v for k,v in self.submission().items() if k!='bounds'})['request']
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in previous.iterdir() if p.is_file()}
        migrated=LocalWorkspace(self.root/'migrated',previous)
        self.assertEqual(migrated.research.snapshot()['countries'],old.research.snapshot()['countries'])
        self.assertEqual(migrated.country_decisions(),{'CAN':'Excluded'})
        self.assertEqual(migrated.display_preferences(),{'text_size':'large'})
        self.assertEqual(migrated.overview()['universities'],[])
        self.assertEqual(migrated.research.snapshot()['requests'],[])
        self.assertEqual(migrated.archived_requests(sample['request_id'])['request']['request_id'],sample['request_id'])
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in previous.iterdir() if p.is_file()})
        migrated.research.save_country({'country_code':'CAN','watched':False})
        self.assertFalse(LocalWorkspace(migrated.directory,previous).research.snapshot()['countries']['CAN']['watched'])

    def test_inbox_and_http_actions_never_execute_agents_and_require_session(self):
        ack=self.ack();packet=env.packet(ack);inbox=self.workspace.directory/'inbox'
        (inbox/'ack.json').write_text(json.dumps(packet));(inbox/'bad.json').write_text('{bad')
        receipt=self.store.scan_inbox();self.assertEqual((receipt['received'],receipt['errors']),(1,1))
        self.assertEqual(self.store.scan_inbox()['received'],0)
        for path in ('/api/local/backup','/api/local/refresh'):
            handler=object.__new__(handler_for(self.workspace,session_token='test-session'))
            handler.path=path;handler.server=SimpleNamespace(server_port=8765)
            handler.headers={'Host':'127.0.0.1:8765','Origin':'http://127.0.0.1:8765','Content-Type':'application/json','Content-Length':'2'}
            handler.rfile=io.BytesIO(b'{}');response={};handler.respond=lambda status,payload:response.update(status=status,payload=payload)
            handler.do_POST();self.assertEqual(response['status'],403)
            handler.headers['X-Grad-Compass-Session']='test-session';handler.rfile=io.BytesIO(b'{}')
            handler.do_POST();self.assertEqual(response['status'],200)

    def test_linked_runtime_and_backup_members_are_refused(self):
        link=self.root/'linked';link.symlink_to(self.workspace.directory,target_is_directory=True)
        with self.assertRaises(ValueError):LocalWorkspace(link)
        snapshot=self.workspace.backup();source=self.workspace.directory/'backups'/snapshot['name']
        link.unlink();link.symlink_to(source,target_is_directory=True)
        with self.assertRaises(ValueError):restore_backup(link,self.root/'unsafe')
        manifest=env.loads((source/'backup.json').read_bytes());manifest['sha256']['../escape']='0'*64
        (source/'backup.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):restore_backup(source,self.root/'unsafe')


if __name__=='__main__':unittest.main()
