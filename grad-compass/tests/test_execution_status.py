from copy import deepcopy
import unittest
from web.execution_status import assess,older


class ExecutionTests(unittest.TestCase):
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
