from copy import deepcopy
import unittest
from web.execution_status import assess,older,foreign_wake_resolution


class ExecutionTests(unittest.TestCase):
    def wake_fixture(self):
        issue={'id':'task','companyId':'company','assigneeAgentId':'owner','status':'in_review'}
        projection={'runId':'notification','agentId':'recipient','execution':{'phase':'failed','cause':'issue_assignee_changed','label':'Cancelled'}}
        runs=[{'runId':'notification','contextIssueId':'task','agentId':'recipient','status':'cancelled','errorCode':'issue_assignee_changed','startedAt':None,'finishedAt':'2026-11-02T20:36:38.790Z'},
              {'runId':'owner-success','contextIssueId':'task','agentId':'owner','status':'succeeded','startedAt':'2026-11-02T20:35:18Z','finishedAt':'2026-11-02T20:36:38.448Z'}]
        return issue,projection,runs

    def test_unstarted_non_assignee_notification_is_distinct_from_owner_work(self):
        issue,projection,runs=self.wake_fixture();before=deepcopy((issue,projection,runs))
        answer=foreign_wake_resolution(issue,projection,None,runs,[])
        self.assertEqual(answer['reason'],'unstarted_non_assignee_wake');self.assertEqual(answer['owner_run_id'],'owner-success')
        self.assertEqual((issue,projection,runs),before);self.assertEqual(issue['status'],'in_review')

    def test_started_missing_unknown_or_wrong_task_attempt_is_not_dismissed(self):
        for field,value in (('startedAt','2026-11-02T20:35:00Z'),('status','failed'),('errorCode','provider_quota'),('contextIssueId','other-task')):
            issue,projection,runs=self.wake_fixture();runs[0][field]=value
            self.assertIsNone(foreign_wake_resolution(issue,projection,None,runs,[]))
        issue,projection,runs=self.wake_fixture();del runs[0]['startedAt']
        self.assertIsNone(foreign_wake_resolution(issue,projection,None,runs,[]))
        issue,projection,runs=self.wake_fixture();runs[1]['contextIssueId']='other-task'
        self.assertIsNone(foreign_wake_resolution(issue,projection,None,runs,[]))

    def test_new_owner_failure_live_attempt_and_recovery_are_never_hidden(self):
        for status in ('failed','cancelled','interrupted','running','unknown'):
            issue,projection,runs=self.wake_fixture()
            runs.append({**runs[1],'runId':'later-owner','status':status,'finishedAt':'2026-11-02T20:37:00Z'})
            self.assertIsNone(foreign_wake_resolution(issue,projection,None,runs,[]))
        issue,projection,runs=self.wake_fixture()
        self.assertIsNone(foreign_wake_resolution(issue,projection,{'status':'active'},runs,[]))

    def test_unknown_or_human_gate_is_preserved_but_agent_wait_is_not_failure(self):
        issue,projection,runs=self.wake_fixture()
        question={'status':'pending','companyId':'company','issueId':'task','addresseeAgentId':'recipient','effectiveResolverPolicy':'anyone'}
        self.assertIsNotNone(foreign_wake_resolution(issue,projection,None,runs,[question]))
        for changes in ({'effectiveResolverPolicy':'human_only'},{'effectiveResolverPolicy':None},{'addresseeAgentId':None},{'issueId':'other'},{'companyId':'other'}):
            self.assertIsNone(foreign_wake_resolution(issue,projection,None,runs,[{**question,**changes}]))
        self.assertIsNone(foreign_wake_resolution(issue,projection,None,runs,None))

    def test_closed_task_cannot_bypass_current_owner_verification(self):
        issue,projection,runs=self.wake_fixture();issue.update(status='done',completedAt='2026-11-02T20:36:38Z',blockedBy=[])
        runs.append({**runs[1],'runId':'later-failure','status':'failed','finishedAt':'2026-11-02T20:37:00Z'})
        self.assertIsNone(foreign_wake_resolution(issue,projection,None,runs,[]))
        answer=assess(issue,projection['execution'],None,runs[0],runs)
        self.assertEqual(answer['state'],'unresolved');self.assertEqual(answer['reason'],'unverified_owner_handoff')

    def test_stale_failed_projection_reconciles_with_later_success_for_completed_task(self):
        issue={'status':'done','completedAt':'2026-10-28T02:00:00Z','blockedBy':[]}
        run={'runId':'old','finishedAt':'2026-10-28T01:00:00Z','status':'failed'}
        success={'runId':'new','finishedAt':'2026-10-28T01:30:00Z','status':'succeeded'}
        answer=assess(issue,{'phase':'failed'},None,run,[run,success])
        self.assertEqual(answer['reason'],'successful_recovery')
        self.assertEqual(answer['successor_run_id'],'new')
        issue['blockedBy']=[{'status':'blocked'}]
        self.assertEqual(assess(issue,{'phase':'failed'},None,run,[run,success])['state'],'unresolved')

    def test_failure_resolved_by_later_authoritative_completion_but_not_by_report_existence(self):
        issue={'status':'done','completedAt':'2026-10-28T02:00:00Z','blockedBy':[]}
        run={'finishedAt':'2026-10-28T01:00:00Z'}
        self.assertEqual(assess(issue,{'phase':'failed'},None,run,[])['reason'],'task_completed_after_attempt')
        self.assertEqual(assess(issue,{'phase':'failed'},{'status':'active'},run,[])['state'],'unresolved')
        issue['completedAt']='2026-10-28T00:00:00Z'
        self.assertEqual(assess(issue,{'phase':'failed'},None,run,[])['reason'],'post_completion_failure')

    def test_same_task_delayed_old_attempt_is_ignored_but_new_task_version_can_reopen_work(self):
        fresh={'task':{'id':'task','statusVersion':3,'updatedAt':'2026-10-28T02:00:00Z'},'step':{'id':'task','updatedAt':'2026-10-28T02:00:00Z'},'run':{'startedAt':'2026-10-28T01:00:00Z'}}
        delayed=deepcopy(fresh);delayed['run']['startedAt']='2026-10-28T00:00:00Z'
        self.assertTrue(older(delayed,fresh))
        delayed['task']['statusVersion']=4
        self.assertFalse(older(delayed,fresh))


if __name__=='__main__':unittest.main()
