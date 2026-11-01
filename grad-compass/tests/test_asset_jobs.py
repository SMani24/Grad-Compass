"""Invented request-bound retrieval and task events; no real network or research."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import io,json,threading,time,unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from PIL import Image
import test_dispatch as fixtures
from web import asset_jobs as assets,research_envelopes as env
from web.local import LocalWorkspace,atomic_json
from web.request_tracking import RequestTracker


class AssetJobTests(unittest.TestCase):
    def setUp(self):
        self.d=fixtures.DispatchTests();self.d.setUp();self.addCleanup(self.d.doCleanups)
        self.w=self.d.w;e=self.d.prepare(countries=['CAN'],scope='country_conditions')
        self.accepted=self.d.confirm(e);self.request=self.accepted['request'];self.root=next(iter(self.d.tasks.values()))
        self.task={'id':str(uuid4()),'parentId':self.root['id'],'companyId':self.d.company,'assigneeAgentId':str(uuid4()),'status':'in_review'}
        self.comments=[];self.posts=0;self.fetches=0;self.online=True;self.lose_ack=False;self.clock=[time.time()+5]
        image=io.BytesIO();Image.new('RGB',(80,50),(10,70,90)).save(image,format='JPEG');self.raw=image.getvalue()
        owner=self
        class Client:
            def __init__(self,connection):pass
            def call(self,path,data=None):
                if not owner.online:raise ConnectionError('Invented unavailable Paperclip')
                if path=='/issues/'+owner.root['id']:return deepcopy(owner.root)
                if path=='/issues/'+owner.task['id']:return deepcopy(owner.task)
                if path=='/issues/'+owner.task['id']+'/comments':
                    if data is None:return deepcopy(owner.comments)
                    owner.posts+=1;comment={'id':str(uuid4()),**data};owner.comments.append(comment)
                    if owner.lose_ack:owner.lose_ack=False;raise ConnectionError('Invented lost response after commit')
                    return deepcopy(comment)
                raise AssertionError('Unexpected endpoint '+path)
        self.Client=Client
        self.asset={'original_url':'https://images.pexels.com/photos/123/invented.jpg',
                    'source_url':'https://example.invalid/invented-source','license_url':'https://example.invalid/permission',
                    'creator':'Invented fixture creator','license':'Invented fixture permission',
                    'caption':'Synthetic test swatch, not a country photograph','alt':'Invented test swatch'}
        self.queued=assets.enqueue(self.w,self.request,'CAN',self.task['id'],self.asset,self.task['assigneeAgentId'])
        self.folder=self.w.directory/'asset-jobs/jobs'/self.queued['job_id']
    def fetch(self,url):self.fetches+=1;return self.raw
    def worker(self,w=None,fetch=None):return assets.AssetJobs(w or self.w,client_factory=self.Client,fetch=fetch or self.fetch,clock=lambda:self.clock[0],quiet_seconds=0)
    def state(self):return env.loads((self.folder/'state.json').read_bytes())

    def test_normal_download_event_restart_and_replay_preserve_original_without_approval(self):
        saved=self.w.research.request(self.request['id']);worker=self.worker();worker.check()
        state=self.state();self.assertEqual(state['status'],'downloaded');self.assertEqual(self.posts,1)
        receipt=env.loads((self.folder/'receipt.json').read_bytes())
        self.assertEqual(receipt['sha256'],assets.hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(receipt['independent_review'],'pending');self.assertEqual(receipt['release'],'not_granted')
        paths=[self.folder/n for n in ('original','receipt.json','state.json','event.json')]
        before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
        self.worker(LocalWorkspace(self.w.directory)).check();worker.check()
        self.assertEqual({p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths},before)
        self.assertEqual((self.fetches,self.posts,self.d.creates),(1,1,1));self.assertEqual(self.w.research.request(self.request['id']),saved)
        self.assertFalse(any('/heartbeat' in c.get('body','') for c in self.comments))
    def test_lost_event_response_reconciles_before_resend_and_never_downloads_again(self):
        self.lose_ack=True;self.worker().check();self.assertEqual(self.state()['status'],'downloaded')
        self.assertEqual(env.loads((self.folder/'event.json').read_bytes())['status'],'pending')
        self.clock[0]+=61;self.worker(LocalWorkspace(self.w.directory)).check()
        self.assertEqual((self.posts,self.fetches),(1,1));self.assertEqual(env.loads((self.folder/'event.json').read_bytes())['status'],'delivered')
    def test_offline_before_acceptance_readback_queues_then_recovers(self):
        self.online=False;worker=self.worker();worker.check()
        self.assertEqual(self.state()['status'],'queued');self.assertEqual(self.fetches,0)
        self.online=True;self.clock[0]+=61;self.worker(LocalWorkspace(self.w.directory)).check()
        self.assertEqual(self.state()['status'],'downloaded');self.assertEqual(self.fetches,1)
    def test_offline_after_download_preserves_original_and_recovers_notification_only(self):
        def retrieve(url):
            raw=self.fetch(url);self.online=False;return raw
        self.worker(fetch=retrieve).check();self.assertEqual(self.state()['status'],'downloaded')
        row=next(r for r in RequestTracker(self.w).snapshot()['requests'] if r['request_id']==self.request['id'])
        self.assertIn('notification is waiting',row['notice']);self.assertNotEqual(row['status'],'failed')
        self.online=True;self.clock[0]+=61;self.worker(LocalWorkspace(self.w.directory)).check()
        self.assertEqual((self.fetches,self.posts),(1,1))
    def test_denial_and_rate_limit_are_terminal_with_specific_existing_task_event(self):
        self.worker().check()
        for code in ('access_denied','rate_limited'):
            with self.subTest(code=code):
                # Separate candidates represent independent invented sources.
                asset={**self.asset,'original_url':'https://images.pexels.com/photos/123/'+code+'.jpg'}
                q=assets.enqueue(self.w,self.request,'CAN',self.task['id'],asset,self.task['assigneeAgentId']);folder=self.w.directory/'asset-jobs/jobs'/q['job_id']
                def denied(url):raise assets.RetrievalFailure(code,'Invented HTTP '+('429' if code=='rate_limited' else '403')+'; no retry')
                # Leave the default fixture already terminal so only this job runs.
                self.worker(fetch=denied).check()
                state=env.loads((folder/'state.json').read_bytes());self.assertEqual(state['status'],'failed');self.assertEqual(state['attempts'],1)
                before=(folder/'state.json').read_bytes();self.worker(fetch=lambda _:self.fail('Denied source retried')).check()
                self.assertEqual((folder/'state.json').read_bytes(),before)
    def test_digest_duplicate_keys_scope_and_unapproved_request_reject_before_network(self):
        path=Path(self.queued['job_path']);packet=env.loads(path.read_bytes());job=env.loads(packet['body'])
        for change in ({**packet,'sha256':'a'*64},{'body':packet['body'].replace('"job_id":','"job_id":"duplicate","job_id":'),'sha256':'a'*64}):
            with self.assertRaises(ValueError):assets.validate(self.w,change)
        duplicate=packet['body'].replace('"job_id":','"job_id":"duplicate","job_id":')
        with self.assertRaisesRegex(ValueError,'Duplicate'):assets.validate(self.w,{'body':duplicate,'sha256':assets.hashlib.sha256(duplicate.encode()).hexdigest()})
        for key,value in [('country_code','CHL'),('request',{**self.request,'sha256':'a'*64})]:
            invalid={**job,key:value}
            with self.assertRaises(ValueError):assets.validate(self.w,env.packet(invalid))
        other=LocalWorkspace(self.d.f.root/'other')
        with self.assertRaises(ValueError):assets.validate(other,packet)
        self.assertEqual(self.fetches,0)
    def test_original_origins_redirects_credentials_and_local_addresses_are_rejected(self):
        for url in ('http://images.pexels.com/x','https://localhost/x','https://127.0.0.1/x','https://images.pexels.com.evil.invalid/x',
                    'https://name:secret@images.pexels.com/x','https://images.pexels.com:8000/x','file:///etc/passwd'):
            with self.subTest(url=url),self.assertRaises(ValueError):assets.public_url(url,download=True)
        for url in ('https://10.0.0.1/x','https://169.254.169.254/x'):
            with self.assertRaises(ValueError):assets.public_url(url)
        # Production opener disables redirects, so none can transfer a request
        # to an unvalidated host or an HTTP/local endpoint.
        import urllib.error
        opener=unittest.mock.Mock();opener.open.side_effect=urllib.error.HTTPError(self.asset['original_url'],302,'redirect',{},None)
        with patch('urllib.request.build_opener',return_value=opener):
            with self.assertRaises(assets.RetrievalFailure):assets.download(self.asset['original_url'])
    def test_task_binding_and_closed_task_do_not_retrieve_or_send_other_task_events(self):
        self.task['parentId']=str(uuid4());self.worker().check();self.assertEqual((self.fetches,self.posts),(0,0))
        self.assertTrue(assets.summaries(self.w)[0]['error'])
    def test_corrected_remote_binding_resolves_attention_but_retains_diagnostic(self):
        parent=self.task['parentId'];self.task['parentId']=str(uuid4());self.worker().check()
        self.task['parentId']=parent;self.worker().check()
        self.assertEqual([a['status'] for a in assets.summaries(self.w)],['downloaded'])
        evidence=env.loads(next((self.w.directory/'asset-jobs/invalid').glob('*.json')).read_bytes())
        self.assertTrue(evidence['resolved_at']);self.assertIn('exact assigned owner',evidence['error'])
        self.assertEqual((self.fetches,self.posts),(1,1))
    def test_exact_assignee_and_closed_task_are_checked_before_retrieval(self):
        for field,value in [('assigneeAgentId',str(uuid4())),('status','done')]:
            original=self.task[field];self.task[field]=value;self.worker().check()
            self.assertEqual((self.fetches,self.posts),(0,0));self.task[field]=original
    def test_changed_original_cannot_publish_a_fabricated_completion_event(self):
        self.lose_ack=True;self.worker().check();self.assertEqual(self.posts,1)
        # Model a lost post before reaching the server, then a corrupt local file.
        self.comments.clear();(self.folder/'original').write_bytes(b'changed')
        self.clock[0]+=61;self.worker().check();self.assertEqual(self.posts,1)
        self.assertIn('binding changed',env.loads((self.folder/'event.json').read_bytes())['message'])
    def test_bad_image_and_size_are_rejected_with_preserved_history(self):
        self.worker(fetch=lambda _:b'<html>not an image</html>').check()
        self.assertEqual(self.state()['status'],'failed');self.assertFalse((self.folder/'original').exists())
        self.assertEqual(self.state()['history'][-1]['event'],'failed')
        with self.assertRaises(ValueError):assets.image_info(b'x'*(assets.MAX_BYTES+1))
    def test_crash_after_original_recovers_local_bytes_without_refetch(self):
        self.folder.mkdir(parents=True);(self.folder/'original').write_bytes(self.raw)
        packet=env.loads(Path(self.queued['job_path']).read_bytes())
        atomic_json(self.folder/'state.json',{'job_id':self.queued['job_id'],'request_id':self.request['id'],'country_code':'CAN','input_sha256':packet['sha256'],'status':'fetching','attempts':1,'history':[{'event':'retrieval_started'}]})
        self.worker(fetch=lambda _:self.fail('Completed bytes refetched')).check()
        self.assertEqual(self.state()['status'],'downloaded');self.assertEqual(self.posts,1)
    def test_concurrent_windows_fetch_once_and_file_permissions_are_private(self):
        started=threading.Event();finish=threading.Event()
        def slow(url):started.set();finish.wait(5);return self.fetch(url)
        with ThreadPoolExecutor(2) as pool:
            first=pool.submit(self.worker(fetch=slow).check);self.assertTrue(started.wait(3))
            second=pool.submit(self.worker().check);second.result(timeout=3);finish.set();first.result(timeout=5)
        self.assertEqual((self.fetches,self.posts),(1,1));self.assertEqual((self.folder/'original').stat().st_mode&0o777,0o600)
    def test_job_identity_replay_and_changed_input_cannot_duplicate_work(self):
        self.worker().check();again=assets.enqueue(self.w,self.request,'CAN',self.task['id'],self.asset,self.task['assigneeAgentId'])
        self.assertEqual(again,self.queued)
        with self.assertRaises(ValueError):assets.enqueue(self.w,self.request,'CAN',self.task['id'],{**self.asset,'caption':'Changed finalized content'},self.task['assigneeAgentId'])
        self.assertEqual(self.fetches,1)
    def test_failure_surfaces_in_requests_and_backup_restore_retains_original_and_event(self):
        self.worker(fetch=lambda _:(_ for _ in ()).throw(assets.RetrievalFailure('offline','Invented asset network unavailable'))).check()
        row=next(r for r in RequestTracker(self.w).snapshot()['requests'] if r['request_id']==self.request['id'])
        self.assertTrue(row['needs_attention']);self.assertIn('Invented asset network',row['notice']);self.assertIn('Dave routes',row['next_action'])
        backup=self.w.backup();from web.recovery import restore_backup
        restored=restore_backup(self.w.directory/'backups'/backup['name'],self.d.f.root/'restored')
        self.assertEqual(assets.summaries(restored),assets.summaries(self.w))
    def test_hidden_incomplete_and_symlink_jobs_never_fetch(self):
        original=Path(self.queued['job_path']);original.rename(original.with_name('.unfinished.json'))
        (original.parent/'partial.json').write_text('{unfinished');self.worker().check();self.assertEqual(self.fetches,0)
        original.symlink_to(original.with_name('.unfinished.json'));self.worker().check();self.assertEqual(self.fetches,0)


if __name__=='__main__':unittest.main()
