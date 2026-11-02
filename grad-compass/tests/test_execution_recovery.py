"""Administrative recovery uses invented requests and a fake control plane only."""
from copy import deepcopy
from pathlib import Path
import json,time,unittest
from uuid import uuid4
import test_dispatch as fixtures
from web.local import LocalWorkspace,atomic_json
from web.request_tracking import RequestTracker
from web.execution_recovery import ExecutionRecovery,records
from web import research_envelopes as env


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.d=fixtures.DispatchTests();self.d.setUp();self.addCleanup(self.d.doCleanups)
        self.w=self.d.w;self.entry=self.d.confirm(self.d.prepare(countries=['CAN'],scope='country_conditions'))
        path=self.w.directory/'paperclip-connection.local.json';value=json.loads(path.read_text());value.update(automatic_recovery_after='2026-01-01T00:00:00Z',runtime_preflight=True);atomic_json(path,value)
        self.identity=self.entry['request']['id'];self.root=next(iter(self.d.tasks.values()))
        self.root.update(status='in_progress',blockedBy=[],updatedAt=env.now())
        self.task=self.root;self.questions=[];self.messages=[];self.posts=0;self.probes=0
        self.online=True;self.lose_ack=False;self.reject_post=False;self.crash=False;self.native_fail=False;self.live=[]
        self.clock=[time.time()];owner=self
        class Client:
            def __init__(self,connection):pass
            def issue(self,identity):
                if not owner.online:raise OSError('Invented offline control plane')
                if identity==owner.root['id']:return deepcopy(owner.root)
                if identity==owner.task['id']:return deepcopy(owner.task)
                raise ValueError('Invented missing foreign task')
            def execution(self,identity):
                if identity==owner.task['id']:return deepcopy(owner.projection)
                return {'execution':{'phase':'completed'}}
            def runs(self,identity):return [deepcopy(owner.run)]
            def comments(self,identity):return deepcopy(owner.messages)
            def preflight(self,agent_id=None):
                owner.probes+=1
                owner.probed_agent=agent_id
                if owner.native_fail:raise ValueError('Runtime probe failed with private detail')
            def call(self,path,data=None):
                if not owner.online:raise OSError('Invented offline control plane')
                if path.endswith('/interactions'):return deepcopy(owner.questions)
                if path.endswith('/live-runs'):return deepcopy(owner.live)
                if path.endswith('/comments') and data is not None:
                    if owner.crash:owner.crash=False;raise SystemExit('Invented process exit before HTTP')
                    owner.posts+=1
                    if owner.reject_post:raise OSError('Invented lost connection before commit')
                    owner.messages.append({'id':str(uuid4()),**deepcopy(data)})
                    if owner.lose_ack:owner.lose_ack=False;raise OSError('Invented lost acknowledgement after commit')
                    return owner.messages[-1]
                raise AssertionError(path)
        self.Client=Client;self.orphan()
    def orphan(self,cause='orphaned_running_run'):
        rid=str(uuid4());self.projection={'runId':rid,'agentId':self.d.dave,'execution':{'phase':'failed','cause':cause}}
        self.run={'runId':rid,'agentId':self.d.dave,'contextIssueId':self.task['id'],'status':'interrupted','errorCode':cause,'finishedAt':env.now()}
        RequestTracker(self.w,client_factory=self.Client).refresh()
    def worker(self,w=None):return ExecutionRecovery(w or self.w,client_factory=self.Client,clock=lambda:self.clock[0])
    def events(self):return list(records(self.w)['events'].values())
    def test_resume_same_task_once_and_replay_restart_preserve_scope_and_history(self):
        before=self.w.research.request(self.identity);self.worker().check()
        self.assertEqual((self.posts,self.probes),(1,1));self.assertEqual(self.events()[0]['status'],'delivered')
        self.assertTrue(self.messages[0]['resume']);self.assertFalse(self.messages[0]['reopen'])
        ledger=(self.w.directory/'execution-recovery.json').read_bytes()
        self.worker(LocalWorkspace(self.w.directory)).check();self.worker().check()
        self.assertEqual((self.w.directory/'execution-recovery.json').read_bytes(),ledger)
        self.assertEqual((self.posts,self.d.creates,self.d.posts),(1,1,1))
        self.assertEqual(self.w.research.request(self.identity),before)
    def test_lost_ack_reconciles_after_new_execution_without_resending(self):
        self.lose_ack=True;self.worker().check();self.assertEqual(self.events()[0]['status'],'uncertain')
        self.projection.update(runId=str(uuid4()),execution={'phase':'working'})
        self.run.update(runId=self.projection['runId'],status='running',errorCode=None)
        RequestTracker(self.w,client_factory=self.Client).refresh()
        self.clock[0]+=61;self.worker(LocalWorkspace(self.w.directory)).check()
        self.assertEqual(self.events()[0]['status'],'delivered');self.assertEqual(self.posts,1)
    def test_exit_after_durable_reservation_before_post_recovers_once(self):
        self.crash=True
        with self.assertRaises(SystemExit):self.worker().check()
        self.assertEqual(self.events()[0]['status'],'prepared');self.assertEqual(self.posts,0)
        self.worker(LocalWorkspace(self.w.directory)).check()
        self.assertEqual(self.events()[0]['status'],'delivered');self.assertEqual(self.posts,1)
    def test_pending_decisions_defer_without_consuming_budget_and_resume_only_after_resolution(self):
        self.questions=[{'status':'pending'}];self.worker().check()
        self.assertEqual(self.posts,0);self.assertEqual(self.events()[0]['status'],'deferred')
        self.assertFalse(self.events()[0]['reserved']);self.assertIn('decision',self.events()[0]['message'])
        self.questions=[];self.clock[0]+=61;self.worker().check();self.assertEqual(self.posts,1)
    def test_quota_model_failure_review_failure_and_completed_work_never_resume(self):
        for cause in ['provider_quota','adapter_failed','review_changes_required']:
            self.orphan(cause);self.worker().check()
        self.orphan();self.root['status']='done';RequestTracker(self.w,client_factory=self.Client).refresh();self.worker().check()
        self.assertEqual((self.posts,self.probes),(0,0));self.assertEqual(self.events(),[])
    def test_native_readiness_failure_preserves_blocker_without_repeated_inference(self):
        self.native_fail=True;self.worker().check();self.clock[0]+=61;self.worker().check()
        self.assertEqual((self.probes,self.posts),(1,0));self.assertEqual(self.events()[0]['status'],'blocked')
        self.assertNotIn('private detail',self.events()[0]['message'])
    def test_native_attempt_limit_is_not_bypassed(self):
        self.projection['execution'].update(attempt=3,maxAttempts=3)
        RequestTracker(self.w,client_factory=self.Client).refresh();self.worker().check()
        self.assertEqual((self.posts,self.probes),(0,0));self.assertIn('execution-attempt limit',self.events()[0]['message'])
    def test_concurrent_live_execution_prevents_another_resume(self):
        self.live=[{'id':str(uuid4()),'status':'running'}];self.worker().check()
        self.assertEqual(self.posts,0);self.assertEqual(self.events()[0]['status'],'superseded')
        self.assertFalse(self.events()[0]['reserved'])
    def test_malformed_recovery_history_fails_closed_and_preserves_bytes(self):
        p=self.w.directory/'execution-recovery.json';p.write_text(json.dumps({'schema_version':'grad-compass-execution-recovery-1','events':{'bad':{}}}))
        before=p.read_bytes()
        with self.assertRaises(ValueError):self.worker().check()
        self.assertEqual(p.read_bytes(),before);self.assertEqual(self.posts,0)
        snapshot=RequestTracker(self.w).snapshot()
        self.assertTrue(any(e['file']=='Automatic recovery' for e in snapshot['unassociated_delivery_errors']))
    def test_policy_does_not_sweep_historical_failures_or_unconfigured_profiles(self):
        self.run['finishedAt']='2025-01-01T00:00:00Z';RequestTracker(self.w,client_factory=self.Client).refresh();self.worker().check()
        self.assertEqual((self.posts,self.probes),(0,0))
        self.orphan();path=self.w.directory/'paperclip-connection.local.json';value=json.loads(path.read_text());value.pop('automatic_recovery_after');atomic_json(path,value)
        self.worker().check();self.assertEqual(self.posts,0)
    def test_two_recoveries_per_step_and_two_transport_attempts_are_bounded(self):
        for _ in range(3):self.orphan();self.worker().check()
        last=next(e for e in self.events() if e['run_id']==self.run['runId'])
        self.assertEqual(self.posts,2);self.assertEqual(last['status'],'blocked')
        self.assertIn('Two automatic',last['message'])
    def test_uncertain_delivery_does_not_retry_indefinitely(self):
        self.reject_post=True
        for _ in range(4):self.worker().check();self.clock[0]+=61
        self.assertEqual(self.posts,2);self.assertEqual(self.events()[0]['status'],'blocked')
        self.assertIn('two attempts',self.events()[0]['message'])
    def test_offline_and_other_profiles_never_create_or_resume_tasks(self):
        self.online=False;self.worker().check();self.assertEqual(self.posts,0)
        other=LocalWorkspace(self.d.f.root/'other-profile');self.worker(other).check()
        self.assertEqual(records(other)['events'],{});self.assertEqual(self.d.creates,1)
    def test_current_assignment_dependency_and_foreign_ancestry_are_not_bypassed(self):
        self.task={**self.root,'id':str(uuid4()),'identifier':'TEST-2','parentId':str(uuid4())}
        self.root['blockedBy']=[self.task];self.orphan();self.worker().check();self.assertEqual(self.posts,0)
        self.task['parentId']=self.root['id'];self.task['blockedBy']=[{'status':'in_progress'}]
        self.worker().check();self.assertEqual(self.events()[0]['status'],'deferred');self.assertEqual(self.posts,0)
        self.task['blockedBy']=[];self.task['assigneeAgentId']=str(uuid4());self.clock[0]+=61
        self.worker().check();self.assertEqual(self.posts,0)
    def test_changed_profile_is_not_silently_used_for_accepted_recovery(self):
        from web.dispatch import config
        p=Path(config(self.w)['approved_profile_directory'])/'receipt.json'
        value=json.loads(p.read_text());value['receipt_id']=str(uuid4());atomic_json(p,value)
        self.worker().check();self.assertEqual(self.posts,0);self.assertEqual(self.events()[0]['status'],'blocked')
    def test_child_recovery_checks_its_actual_assigned_agent_and_preserves_root_binding(self):
        agent=str(uuid4())
        self.task={**self.root,'id':str(uuid4()),'identifier':'TEST-2','parentId':self.root['id'],'assigneeAgentId':agent}
        self.root['blockedBy']=[self.task];self.orphan()
        self.projection['agentId']=agent;self.run['agentId']=agent
        RequestTracker(self.w,client_factory=self.Client).refresh();self.worker().check()
        self.assertEqual(self.posts,1);self.assertEqual(self.probed_agent,agent)
        self.assertEqual(self.entry['destination']['dave_id'],self.d.dave)
    def test_backup_restores_private_recovery_ledger(self):
        from web.recovery import restore_backup
        self.worker().check();saved=self.w.backup()
        restored=restore_backup(self.w.directory/'backups'/saved['name'],self.d.f.root/'restored-recovery')
        self.assertEqual(records(restored),records(self.w))
