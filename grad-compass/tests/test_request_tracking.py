"""Asynchronous journeys use invented requests and isolated fake HTTP only."""
from copy import deepcopy
import json,time,unittest
from uuid import uuid4
from pathlib import Path
import test_dispatch as dispatch_fixture
from web.dispatch import Dispatch
from web.request_tracking import RequestTracker
from web.local import LocalWorkspace,atomic_json
from web import research_envelopes as env,report_packages
from web.inbox import InboxReceiver


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.d=dispatch_fixture.DispatchTests();self.d.setUp();self.addCleanup(self.d.doCleanups)
        self.w=self.d.w;self.entry=self.d.prepare(countries=['CAN'],scope='country_conditions',bounds={'institutions':0,'programs':0})
        self.accepted=self.d.confirm(self.entry);self.identity=self.accepted['request']['id'];self.root=next(iter(self.d.tasks.values()))
        self.d.f.request=self.w.research.request(self.identity)['request']
        self.tracker=RequestTracker(self.w);self.run=str(uuid4())
        self.execution={'runId':self.run,'agentId':self.d.dave,'execution':{'phase':'running','label':'Running','lastConfirmedActivityAt':env.now(),'permittedActions':['inspect_run']},'recoveryAction':None}
        self.root.update(updatedAt=env.now(),blockedBy=[],status='in_progress')
        self.routes(self.root,self.execution)
    def routes(self,issue,execution):
        prefix='/api/issues/'+issue['id'];self.d.routes.update({prefix:issue,prefix+'/execution':execution,prefix+'/runs':[{'runId':execution['runId'],'agentId':execution['agentId'],'contextIssueId':issue['id'],'status':execution['execution']['phase']}],prefix+'/comments':[]})
    def row(self,service=None):return next(r for r in (service or self.tracker).snapshot()['requests'] if r['request_id']==self.identity)
    def fail(self):
        self.root['status']='blocked';self.execution['execution'].update(phase='failed',cause='adapter_failed',attempt=3,maxAttempts=3,successorRunId=None)
        self.execution['recoveryAction']={'id':str(uuid4()),'kind':'stranded_assigned_issue','status':'active','ownerType':'board','nextAction':'Repair runtime, then explicitly recover the existing task.'}
        self.d.routes['/api/issues/'+self.root['id']+'/comments']=[{'authorType':'system','metadata':{'sourceRunId':self.run,'sections':[{'rows':[{'label':'Failure summary','value':'Not inside a trusted directory and --skip-git-repo-check was not specified.'}]}]}}]
    def test_accepted_then_failed_request_and_notice_survive_restart_without_changing_history(self):
        self.d.f.receive(self.d.f.ack());before=self.w.research.request(self.identity)
        self.tracker.refresh();self.assertEqual(self.row()['status'],'active')
        self.fail();self.tracker.refresh();r=self.row();self.assertEqual(r['status'],'failed');self.assertIn('not trusted',r['notice']);self.assertTrue(r['needs_attention'])
        reopened=RequestTracker(LocalWorkspace(self.w.directory));self.assertEqual(self.row(reopened)['status'],'failed');self.assertEqual(len(self.row(reopened)['tracking']['history']),2)
        self.assertEqual(self.w.research.request(self.identity),before);self.assertEqual(self.d.creates,1);self.assertEqual(self.d.posts,1)
    def test_unavailable_retains_last_known_failure_and_does_not_claim_a_new_failure(self):
        self.fail();self.tracker.refresh();first=self.row();self.d.online=False;self.tracker.refresh();r=self.row()
        self.assertEqual(r['status'],'failed');self.assertTrue(r['tracking']['connection_error']);self.assertEqual(r['last_success_at'],first['last_success_at']);self.assertEqual(r['tracking']['history'],first['tracking']['history'])
        self.d.online=True;self.execution['execution']['phase']='running';self.root['status']='in_progress';self.execution['recoveryAction']=None;self.tracker.refresh();self.d.online=False;self.tracker.refresh()
        self.assertEqual(self.row()['status'],'active');self.assertNotIn('failed',self.row()['label'].lower())
    def test_unavailable_before_first_observation_retains_known_task_and_navigation(self):
        self.d.online=False;self.tracker.refresh();r=self.row()
        self.assertEqual(r['task']['id'],self.root['id']);self.assertNotEqual(r['status'],'failed');self.assertTrue(r['tracking']['connection_error']);self.assertTrue(r['task_url'].endswith('/TEST/issues/TEST-1'));self.assertEqual(self.d.posts,1)
    def test_root_completion_does_not_hide_failed_child_or_select_a_sibling_run(self):
        child={'id':str(uuid4()),'identifier':'TEST-2','companyId':self.d.company,'title':'Prepare country report','status':'blocked','updatedAt':env.now()}
        self.root['blockedBy']=[child];self.root['status']='blocked';self.execution['execution']['phase']='completed'
        execution={'runId':str(uuid4()),'agentId':str(uuid4()),'execution':{'phase':'failed','cause':'adapter_failed','permittedActions':['inspect_run']}}
        self.routes(child,execution)
        self.d.routes['/api/issues/'+child['id']+'/runs'].insert(0,{'runId':execution['runId'],'contextIssueId':self.root['id'],'agentId':execution['agentId'],'status':'succeeded'})
        self.tracker.refresh();r=self.row();self.assertEqual(r['status'],'failed');self.assertEqual(r['tracking']['latest']['step']['id'],child['id']);self.assertEqual(r['tracking']['latest']['run']['status'],'failed')
        self.assertTrue(r['recovery_url'].endswith('/TEST/issues/TEST-2'));self.assertTrue(r['task_url'].endswith('/TEST/issues/TEST-1'))
    def test_repeated_reads_delayed_updates_and_done_without_report_never_fabricate_completion(self):
        self.tracker.refresh();self.tracker.refresh();self.assertEqual(len(self.row()['tracking']['history']),1)
        later=RequestTracker(self.w,clock=lambda:time.time()+86400);r=self.row(later);self.assertTrue(r['delayed']);self.assertNotEqual(r['status'],'failed')
        self.root['status']='done';self.execution['execution']['phase']='completed';self.tracker.refresh();r=self.row();self.assertEqual(r['status'],'awaiting_delivery');self.assertFalse(any(c['available'] for c in r['reports']))
    def test_closed_app_recovers_progress_then_final_report_through_existing_inbox(self):
        self.d.f.receive(self.d.f.ack());self.tracker.refresh();initial=self.w.research.request(self.identity)
        result=self.d.f.result();finding=self.d.f.country();finding['sources']=[{'source_id':str(uuid4()),'source_revision':'invented-r1','source_url':'https://example.invalid/evidence','title':'Invented evidence','locator':'Fixture section','observed_at':env.now()}];result['findings']=[finding];atomic_json(self.w.directory/'inbox/result.json',env.packet(result))
        reopened=LocalWorkspace(self.w.directory);receiver=InboxReceiver(reopened,quiet_seconds=0);reopened.inbox_receiver=receiver;self.assertEqual(receiver.check()['received'],1)
        tracker=RequestTracker(reopened);self.assertEqual(self.row(tracker)['status'],'findings')
        saved=reopened.research.request(self.identity)['results'][0]['envelope']
        from report_fixtures import package
        root,meta=package(self.d.f,saved,code='CAN')
        from web.report_delivery import publish
        publication=publish(reopened,root)
        notice=next(p for p in (reopened.directory/'inbox').glob('report-*.json'))
        packet=json.loads(notice.read_text());body=json.loads(packet['body']);metadata=reopened.directory/body['metadata_path'];original=metadata.read_bytes();metadata.unlink()
        receiver.check();r=self.row(tracker);self.assertTrue(r['delivery_errors']);self.assertIn('could not be validated',r['notice'])
        self.assertTrue(tracker.read()['requests'][self.identity]['history'])
        metadata.write_bytes(original);self.assertFalse(receiver.check()['errors']);self.root['status']='done';self.execution['execution']['phase']='completed';tracker.refresh()
        r=self.row(tracker);self.assertEqual(r['status'],'complete');self.assertFalse(r['delivery_errors']);self.assertEqual(r['reports'][0]['review']['human']['state'],'not_requested')
        self.assertEqual(receiver.check()['received'],0);self.assertEqual(len(reopened.research.request(self.identity)['results']),1);self.assertEqual(self.d.creates,1)
        self.assertEqual(reopened.research.request(self.identity)['request'],initial['request'])
    def test_wrong_binding_is_not_followed_and_other_profiles_cannot_see_or_refresh_it(self):
        self.root['description']='Different request';self.tracker.refresh();self.assertIn('does not match',self.row()['tracking']['connection_error']);self.assertEqual(self.row()['status'],'waiting')
        other=RequestTracker(LocalWorkspace(self.d.f.root/'other'));self.assertEqual(other.snapshot()['requests'],[])
        with self.assertRaises(ValueError):other.refresh(self.identity)
    def test_lost_dispatch_ack_is_reconciled_only_by_explicit_existing_retry(self):
        e=self.d.prepare(countries=['CAN']);self.d.lose_ack=True;r=self.d.confirm(e);self.assertEqual(r['status'],'uncertain');before=self.d.posts
        self.tracker.refresh();self.assertEqual(self.d.posts,before)
        result=self.d.service.retry(e['id']);self.assertEqual(result['status'],'accepted');self.assertEqual(self.d.creates,2) # one distinct fixture request, one recovered request
        self.assertEqual(self.d.posts,before)
        entry=next(e for e in self.d.service.read()['entries'] if e['id']==result['id'])
        self.assertEqual([e['action'] for e in entry['attempt_history']],['confirmed','send_attempt','uncertain','task_receipt'])

    def test_status_api_uses_profile_and_csrf_guards_and_backup_retains_observations(self):
        import test_profiles as profile_fixture
        from web.profiles import LocalProfiles
        from web.recovery import restore_backup
        self.fail();self.tracker.refresh()
        helper=object.__new__(profile_fixture.ProfileTests);helper.profiles=LocalProfiles(self.w.directory)
        self.assertEqual(helper.http('/api/requests')['status'],200)
        self.assertEqual(helper.http('/api/requests/refresh',{'request_id':self.identity},**{'X-Grad-Compass-Workspace':''})['status'],403)
        self.assertEqual(helper.http('/api/requests/refresh',{'request_id':self.identity})['status'],200)
        backup=self.w.backup();restored=restore_backup(self.w.directory/'backups'/backup['name'],self.d.f.root/'restored-tracking')
        self.assertEqual(RequestTracker(restored).read(),self.tracker.read())

    def test_wrong_agent_or_context_runs_and_unbound_failure_messages_are_ignored(self):
        self.fail();prefix='/api/issues/'+self.root['id']
        self.d.routes[prefix+'/runs']=[{'runId':self.run,'contextIssueId':self.root['id'],'agentId':str(uuid4()),'status':'succeeded'}]
        self.d.routes[prefix+'/comments'].insert(0,{'authorType':'system','metadata':{'sourceRunId':str(uuid4()),'sections':[{'rows':[{'label':'Failure summary','value':'A different run failed'}]}]}})
        self.tracker.refresh();latest=self.row()['tracking']['latest'];self.assertIsNone(latest['run']['status']);self.assertEqual(latest['run_history'],[])
        self.assertIn('not trusted',latest['failure'])
    def test_malformed_remote_status_preserves_observed_state_and_requests_attention(self):
        self.tracker.refresh();before=self.row()['tracking']['latest']
        self.d.routes['/api/issues/'+self.root['id']+'/execution']=['unsupported']
        self.tracker.refresh();row=self.row();self.assertEqual(row['tracking']['latest'],before)
        self.assertNotEqual(row['status'],'failed');self.assertTrue(row['needs_attention']);self.assertIn('unsupported shape',row['tracking']['connection_error'])
    def test_failure_visibility_does_not_require_privileged_attempt_or_error_access(self):
        from web.request_tracking import StatusClient
        class LimitedDetails(StatusClient):
            def runs(self,identity):raise PermissionError('Invented private run history')
            def comments(self,identity):raise PermissionError('Invented privileged failure detail')
        self.fail();service=RequestTracker(self.w,client_factory=LimitedDetails);service.refresh();r=self.row(service)
        self.assertEqual(r['status'],'failed');self.assertTrue(r['needs_attention']);self.assertFalse(r['tracking']['connection_error']);self.assertEqual(len(r['tracking']['latest']['diagnostic_notes']),2)
    def test_scheduled_retry_is_distinct_from_exhausted_terminal_failure(self):
        self.fail();self.root['scheduledRetry']={'runId':self.run,'status':'scheduled'};self.tracker.refresh();r=self.row()
        self.assertEqual(r['status'],'retry_scheduled');self.assertEqual(self.d.creates,1)
        self.root['scheduledRetry']=None;self.tracker.refresh();self.assertEqual(self.row()['status'],'failed');self.assertEqual(self.d.posts,1)


if __name__=='__main__':unittest.main()
