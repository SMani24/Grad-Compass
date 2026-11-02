"""Reconcile work disposition without erasing the underlying attempt outcome."""
from datetime import datetime

ADMINISTRATIVE_CANCELLATIONS={'continuation_task_ownership_changed','issue_assignee_changed'}
TERMINAL_RECOVERY={'resolved','completed','cancelled','closed','dismissed'}


def timestamp(value):
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
    except (ValueError,TypeError,AttributeError):return None


def active_recovery(recovery):
    return bool(recovery and recovery.get('status') not in TERMINAL_RECOVERY)


def open_dependencies(issue):
    return [r for r in issue.get('blockedBy',[]) if r.get('status') not in ('done','cancelled')
        or active_recovery(r.get('activeRecoveryAction')) or r.get('scheduledRetry')]


def closed_cancellation(issue,execution,recovery):
    return (issue.get('status')=='done' and not active_recovery(recovery) and not open_dependencies(issue)
        and execution.get('cause') in ADMINISTRATIVE_CANCELLATIONS
        and execution.get('label','').lower()=='cancelled')


def foreign_wake_resolution(issue,projection,recovery,runs,interactions):
    """Reconcile only an unstarted wrong-assignee wake, never failed research."""
    execution=projection.get('execution') or {};owner=issue.get('assigneeAgentId')
    if (execution.get('phase') not in ('failed','recovery_needed')
        or execution.get('cause')!='issue_assignee_changed'
        or execution.get('label','').lower()!='cancelled'
        or active_recovery(recovery) or not owner or not projection.get('agentId')
        or not projection.get('runId') or owner==projection.get('agentId')):return None
    if not isinstance(runs,list) or any(not isinstance(r,dict) for r in runs):return None
    stopped=next((r for r in runs if r.get('runId')==projection.get('runId')
        and r.get('contextIssueId')==issue['id'] and r.get('agentId')==projection.get('agentId')),None)
    if (not stopped or 'startedAt' not in stopped or stopped['startedAt'] is not None
        or stopped.get('status')!='cancelled' or stopped.get('errorCode')!='issue_assignee_changed'
        or timestamp(stopped.get('finishedAt')) is None):return None
    owned=[r for r in runs if r.get('contextIssueId')==issue['id'] and r.get('agentId')==owner]
    # Unknown/live/newer failed owner attempts must not be dismissed from an
    # earlier success. /runs also includes related tasks: bind both identities.
    if not owned or any(r.get('status') not in ('succeeded','failed','cancelled','interrupted','timed_out')
        or timestamp(r.get('finishedAt')) is None for r in owned):return None
    latest=max(owned,key=lambda r:timestamp(r['finishedAt']))
    if latest.get('status')!='succeeded' or timestamp(latest.get('startedAt')) is None:return None
    if not isinstance(interactions,list) or any(not isinstance(q,dict) for q in interactions):return None
    if any(q.get('status')=='pending' and (q.get('companyId')!=issue.get('companyId')
        or q.get('issueId')!=issue['id'] or not q.get('addresseeAgentId')
        or q.get('effectiveResolverPolicy')!='anyone') for q in interactions):return None
    return {'state':'resolved','reason':'unstarted_non_assignee_wake','owner_run_id':latest['runId'],
        'message':'An unstarted follow-up for another agent was cancelled on this task. The current owner has a successful run on the same task; outstanding task, review and approval requirements remain unchanged.'}


def assess(issue,execution,recovery,run,runs):
    phase=execution.get('phase');failed=phase in ('failed','recovery_needed')
    if (failed and run.get('errorCode')=='issue_assignee_changed' and run.get('agentId')
        and issue.get('assigneeAgentId') and run['agentId']!=issue['assigneeAgentId']
        and 'startedAt' in run and run['startedAt'] is None):
        # Closed-task cancellation rules cannot stand in for checking the
        # current owner. Only foreign_wake_resolution supplies that proof.
        return {'state':'unresolved','reason':'unverified_owner_handoff',
                'message':'Paperclip selected an unstarted follow-up for another agent; the current owner’s execution and outstanding gates still require verification.'}
    if failed and not active_recovery(recovery) and issue.get('status')=='done' and not open_dependencies(issue):
        end=timestamp(run.get('finishedAt'));closed=timestamp(issue.get('completedAt'))
        later=next((r for r in runs if r.get('status')=='succeeded' and end is not None
            and timestamp(r.get('finishedAt')) is not None and timestamp(r['finishedAt'])>end),None)
        if closed_cancellation(issue,execution,recovery) and run.get('status')=='cancelled' and run.get('errorCode')==execution.get('cause'):
            return {'state':'resolved','reason':'closed_task_continuation_cancelled',
                'message':'Paperclip completed this task, then cancelled an unneeded continuation. No unresolved recovery or dependency is recorded. The cancelled attempt remains in history.'}
        if later:
            return {'state':'resolved','reason':'successful_recovery','successor_run_id':later['runId'],
                'message':'A later successful attempt and the completed task supersede the earlier failure. The original attempt remains in history.'}
        if end is not None and closed is not None and closed>=end:
            return {'state':'resolved','reason':'task_completed_after_attempt',
                'message':'Paperclip recorded task completion after this attempt stopped, with no unresolved recovery or dependency. The stopped attempt remains in history.'}
    if failed or active_recovery(recovery):
        return {'state':'unresolved','reason':'post_completion_failure' if issue.get('status')=='done' else 'execution_failure',
            'message':'A stopped attempt or active recovery still needs reconciliation in Paperclip.'}
    return {'state':'complete' if issue.get('status')=='done' else 'active','reason':'current_task_state'}


def older(observation,previous):
    """Never let an old task version or delayed attempt undo accepted progress."""
    if not previous:return False
    current_task=observation['task'];old_task=previous['task']
    if current_task['id']!=old_task['id']:return False
    a,b=current_task.get('statusVersion'),old_task.get('statusVersion')
    if type(a) is int and type(b) is int and a!=b:return a<b
    a,b=timestamp(current_task.get('updatedAt')),timestamp(old_task.get('updatedAt'))
    if a is not None and b is not None and a!=b:return a<b
    if observation['step']['id']!=previous['step']['id']:return False
    a,b=timestamp(observation['step'].get('updatedAt')),timestamp(previous['step'].get('updatedAt'))
    if a is not None and b is not None and a!=b:return a<b
    a,b=timestamp(observation.get('run',{}).get('startedAt')),timestamp(previous.get('run',{}).get('startedAt'))
    return a is not None and b is not None and a<b
