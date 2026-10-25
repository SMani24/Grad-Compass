"""Confirmed dispatch uses invented profiles and an isolated fake Paperclip HTTP API."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import hashlib,json,socket,threading,time,unittest,subprocess,os
from unittest.mock import patch
from uuid import uuid4
import test_local as fixtures
from web.local import atomic_json,LocalWorkspace
from web.dispatch import Dispatch,Paperclip,config


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.LocalTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.w=self.f.workspace;self.tasks={};self.creates=0;self.posts=0;self.online=True;self.lose_ack=False;self.guard=threading.Lock()
        self.company=str(uuid4());self.dave=str(uuid4());root=self.f.root/'approved';root.mkdir()
        content=b'{"invented":"no applicant data"}';(root/'profile.json').write_bytes(content);(root/'COMPLETE').write_text('complete\n')
        atomic_json(root/'receipt.json',{'profile_id':str(uuid4()),'revision_id':str(uuid4()),'sha256':hashlib.sha256(content).hexdigest(),'receipt_id':str(uuid4()),'approved_at':'2026-10-25T00:00:00Z','decision':'accepted','actor_type':'human','reliable_for_discovery':True})
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,value,status=200):
                raw=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_GET(self):
                if not owner.online:return self.reply({'error':'offline'},503)
                return self.reply(list(owner.tasks.values()) if '/issues?' in self.path else {'id':owner.company})
            def do_POST(self):
                value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with owner.guard:
                    owner.posts+=1;key=value['idempotencyKey']
                    if key not in owner.tasks:
                        owner.creates+=1;owner.tasks[key]={'id':str(uuid4()),'identifier':'TEST-'+str(owner.creates),'companyId':owner.company,'assigneeAgentId':owner.dave,'status':'todo','description':value['description']}
                    result=owner.tasks[key]
                    if owner.lose_ack:
                        owner.lose_ack=False;self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
                    self.reply(result)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=self.server.serve_forever,daemon=True).start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        atomic_json(self.w.directory/'paperclip-connection.local.json',{'url':'http://127.0.0.1:'+str(self.server.server_port),'company_id':self.company,'dave_id':self.dave,'approved_profile_directory':str(root),'atomic_idempotency':True})
        self.service=Dispatch(self.w)
    def prepare(self,**changes):return self.service.prepare(self.f.submission(**changes))
    def confirm(self,e):return self.service.confirm(e['id'],e['confirmation_digest'])
    def test_cancellation_cannot_invoke_and_confirmation_is_exact(self):
        before=len(self.w.research.snapshot()['requests']);e=self.prepare();self.service.cancel(e['id'])
        with self.assertRaises(ValueError):self.confirm(e)
        self.assertEqual((self.creates,len(self.w.research.snapshot()['requests'])),(0,before))
        e=self.prepare()
        with self.assertRaises(ValueError):self.service.confirm(e['id'],'a'*64)
        self.assertEqual(self.posts,0)
    def test_offline_pending_restart_edit_revision_cancel_and_profile_isolation(self):
        self.online=False;e=self.prepare();first=self.confirm(e)
        self.assertEqual(first['status'],'pending');self.assertEqual(first['attempts'],0)
        self.assertTrue((self.w.directory/'research-handoff'/('request-'+first['request']['id']+'.json')).is_file())
        service=Dispatch(LocalWorkspace(self.w.directory));self.assertEqual(service.snapshot()['entries'][0]['id'],e['id'])
        # Reconnecting itself never calls the dispatch endpoint.
        self.online=True;service.snapshot();self.assertEqual(self.posts,0)
        changed=service.prepare(self.f.submission(context='Explicit edited scope'),edit_id=e['id'])
        amended=service.confirm(changed['id'],changed['confirmation_digest']);self.assertEqual(amended['status'],'accepted');self.assertEqual(amended['revision'],2)
        self.assertNotEqual(amended['request']['id'],first['request']['id']);self.assertEqual(service.snapshot()['entries'][0]['status'],'superseded')
        self.assertEqual(self.w.research.request(amended['request']['id'])['request']['parent_request_id'],first['request']['id'])
        with self.assertRaises(ValueError):service.cancel(changed['id'])
        other=Dispatch(LocalWorkspace(self.f.root/'other'));self.assertEqual(other.snapshot()['entries'],[])
        with self.assertRaises(ValueError):other.retry(e['id'])
    def test_duplicate_clicks_and_lost_ack_recover_one_task(self):
        e=self.prepare();self.lose_ack=True
        first=self.confirm(e);self.assertEqual(first['status'],'uncertain');self.assertEqual(self.creates,1)
        # Two independent service instances model app windows after a restart.
        with ThreadPoolExecutor(2) as pool:
            rows=list(pool.map(lambda _:Dispatch(LocalWorkspace(self.w.directory)).retry(e['id']),range(2)))
        self.assertEqual({r['task']['id'] for r in rows},{first['task']['id']} if first['task'] else {next(iter(self.tasks.values()))['id']})
        self.assertTrue(all(r['status']=='accepted' for r in rows));self.assertEqual(self.creates,1);self.assertEqual(self.posts,1)
        original=self.w.research.request(rows[0]['request']['id'])
        with self.assertRaises(ValueError):self.service.prepare(self.f.submission(),edit_id=e['id'])
        self.assertEqual(self.w.research.request(rows[0]['request']['id']),original)
    def test_atomic_remote_key_replays_even_if_search_cannot_find_task(self):
        e=self.prepare();self.lose_ack=True;first=self.confirm(e)
        class SearchUnavailable(Paperclip):
            def reconcile(self,marker):return None
        recovered=Dispatch(self.w,client_factory=SearchUnavailable).retry(e['id'])
        self.assertEqual(recovered['status'],'accepted');self.assertEqual((self.posts,self.creates),(2,1))
    def test_old_uncertain_attempt_reconciles_only_and_credentials_stay_private(self):
        e=self.prepare();self.lose_ack=True;self.confirm(e);self.tasks.clear()
        later=Dispatch(self.w,clock=lambda:time.time()+8*86400);row=later.retry(e['id'])
        self.assertEqual(row['status'],'uncertain');self.assertIn('seven-day',row['error']);self.assertEqual(self.posts,1)
        self.assertNotIn('approved_profile_directory',json.dumps(later.snapshot()))
        self.assertNotIn('GRAD_COMPASS_PAPERCLIP_TOKEN',json.dumps(later.snapshot()))
    def test_profile_change_requires_new_confirmation(self):
        e=self.prepare();root=Path(config(self.w)['approved_profile_directory']);v=json.loads((root/'receipt.json').read_text());v['decision']='rejected';atomic_json(root/'receipt.json',v)
        row=self.confirm(e);self.assertEqual(row['status'],'pending');self.assertEqual(self.posts,0)

    def test_independent_processes_share_one_durable_dispatch(self):
        self.online=False;e=self.prepare();self.confirm(e);self.online=True
        code="import json,sys;from web.local import LocalWorkspace;from web.dispatch import Dispatch;r=Dispatch(LocalWorkspace(sys.argv[1])).retry(sys.argv[2]);print(json.dumps({'status':r['status'],'task':r['task']['id']}))"
        python=str(Path(__file__).resolve().parents[1]/'envGradCompass/bin/python')
        environment={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'PYTHONDONTWRITEBYTECODE':'1'}
        children=[subprocess.Popen([python,'-B','-c',code,str(self.w.directory),e['id']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment) for _ in range(2)]
        rows=[]
        for child in children:
            output,error=child.communicate(timeout=25);self.assertEqual(child.returncode,0,error);rows.append(json.loads(output))
        self.assertEqual(rows[0],rows[1]);self.assertEqual(rows[0]['status'],'accepted');self.assertEqual((self.posts,self.creates),(1,1))

    def test_unflushed_state_cannot_reach_the_remote_create(self):
        e=self.prepare()
        with patch('web.dispatch.os.fsync',side_effect=OSError('Invented durability failure')):
            with self.assertRaises(OSError):self.confirm(e)
        self.assertEqual(self.posts,0)
        recovered=self.confirm(e);self.assertEqual(recovered['status'],'accepted');self.assertEqual(self.creates,1)

    def test_marker_substrings_or_wrong_digest_do_not_record_acceptance(self):
        e=self.prepare();self.lose_ack=True;self.confirm(e)
        task=next(iter(self.tasks.values()));original=task['description']
        task['description']='prefix '+original
        result=self.service.retry(e['id']);self.assertEqual(result['status'],'uncertain');self.assertIn('conflicting',result['error']);self.assertEqual(self.creates,1)
        task['description']=original.replace(e['profile_reference']['sha256'],'a'*64)
        result=self.service.retry(e['id']);self.assertEqual(result['status'],'uncertain');self.assertEqual(self.creates,1)
        task['description']=original;task['status']='done'
        result=self.service.retry(e['id']);self.assertEqual(result['status'],'accepted');self.assertEqual(result['task']['status'],'done')
        self.assertIsNone(self.w.research.request(result['request']['id'])['acknowledgement'])

    def test_confirmation_binds_the_company_and_agent_destination(self):
        e=self.prepare();path=self.w.directory/'paperclip-connection.local.json';value=json.loads(path.read_text());value['company_id']=str(uuid4());atomic_json(path,value)
        result=self.confirm(e);self.assertEqual(result['status'],'pending');self.assertIn('destination changed',result['error']);self.assertEqual(self.posts,0)
