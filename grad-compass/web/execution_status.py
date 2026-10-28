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


def assess(issue,execution,recovery,run,runs):
    phase=execution.get('phase');failed=phase in ('failed','recovery_needed')
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
