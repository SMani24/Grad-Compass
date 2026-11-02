"""Bounded continuation of accepted work after verified controller process loss.

No new issues/agents, generic failure retries, review decisions or permission
repairs. The owner-approved policy uses the existing supported resume-input API.
"""
from contextlib import contextmanager
import fcntl
import os
import time
from uuid import uuid5,NAMESPACE_URL
from web import research_envelopes as env
from web.dispatch import Dispatch,config,durable,profile_reference
from web.execution_status import active_recovery,open_dependencies
from web.local import regular
from web.request_tracking import RequestTracker,StatusClient,inspect,seconds

VERSION='grad-compass-execution-recovery-1'


class RecoveryGate(ValueError):
    """App-owned, safe explanation; remote response bodies never reach the UI."""


class WaitingGate(RecoveryGate):
    pass


def records(workspace):
    path=regular(workspace.directory/'execution-recovery.json')
    value=env.loads(path.read_bytes()) if path.exists() else {'schema_version':VERSION,'events':{}}
    if not isinstance(value,dict) or value.get('schema_version')!=VERSION or not isinstance(value.get('events'),dict):
        raise ValueError('Automatic recovery history needs technical attention; saved requests are retained')
    for key,event in value['events'].items():
        if (not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key)
            or not isinstance(event,dict) or event.get('status') not in ('prepared','uncertain','delivered','blocked','deferred','superseded')
            or type(event.get('reserved')) is not bool or type(event.get('posts')) is not int or not 0<=event['posts']<=2
            or not isinstance(event.get('message'),str) or not isinstance(event.get('history'),list)):
            raise ValueError('Automatic recovery history needs technical attention; saved requests are retained')
        for field in ('request_id','task_id','run_id'):env.identifier(event.get(field))
    return value


@contextmanager
def exclusive(workspace):
    fd=os.open(regular(workspace.directory/'.execution-recovery.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'r+') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:yield False;return
        yield True


class ExecutionRecovery:
    def __init__(self,workspace,client_factory=StatusClient,clock=time.time):
        self.workspace=workspace;self.client_factory=client_factory;self.clock=clock
        self.path=regular(workspace.directory/'execution-recovery.json')
    def save(self,state,event,status,message):
        event.update(status=status,message=message,updated_at=env.now())
        event.setdefault('history',[]).append({'at':env.now(),'status':status,'message':message})
        durable(self.path,state)
    @staticmethod
    def eligible(observation):
        return (observation.get('execution',{}).get('cause')=='orphaned_running_run'
            and observation.get('execution',{}).get('phase') in ('failed','recovery_needed')
            and observation.get('run',{}).get('status')=='interrupted'
            and observation.get('run',{}).get('errorCode')=='orphaned_running_run'
            and observation.get('task',{}).get('status') not in ('done','cancelled'))
    @staticmethod
    def bound_task(client,identity,entry,connection):
        task=client.issue(env.identifier(identity));ancestor=task
        if task.get('id')!=identity:raise RecoveryGate('Recovery task identity cannot be verified.')
        for _ in range(5):
            if ancestor.get('companyId')!=connection['company_id']:raise RecoveryGate('Recovery task is outside the accepted request.')
            if ancestor['id']==entry['task']['id']:return task
            parent=env.identifier(ancestor.get('parentId'));ancestor=client.issue(parent)
            if ancestor.get('id')!=parent:raise RecoveryGate('Recovery task ancestry cannot be verified.')
        raise RecoveryGate('Recovery task ancestry cannot be verified.')
    def check(self):
        if not getattr(self.workspace,'operational',False):return
        with exclusive(self.workspace) as acquired:
            if not acquired:return
            state=records(self.workspace);tracking=RequestTracker(self.workspace).read()
            connection=config(self.workspace)
            if not connection or connection.get('runtime_preflight') is not True:return
            enabled_at=seconds(connection.get('automatic_recovery_after'))
            if enabled_at is None:return
            for entry in Dispatch(self.workspace).snapshot()['entries']:
                if entry['status']!='accepted':continue
                identity=entry['request']['id'];cached=tracking['requests'].get(identity,{}).get('latest',{})
                pending=[(k,e) for k,e in state['events'].items() if e['request_id']==identity and e['status'] in ('prepared','uncertain') and self.clock()>=e.get('retry_at',0)]
                finished=seconds(cached.get('run',{}).get('finishedAt'))
                if not pending and (finished is None or finished<enabled_at):continue
                if not self.eligible(cached) and not pending:continue
                # Never infer a request association from country names or titles.
                if entry['destination']!={'company_id':connection['company_id'],'dave_id':connection['dave_id']}:continue
                client=self.client_factory(connection)
                event=None;key=None
                try:
                    request=self.workspace.research.request(identity)['request']
                    if (request['revision'],request['digest'])!=(entry['request']['revision'],entry['request']['sha256']):continue
                    observed=inspect(client,entry,connection)
                    for key,event in pending:
                        task=self.bound_task(client,event['task_id'],entry,connection)
                        comments=client.comments(task['id']);marker='Grad-Compass administrative recovery '+key
                        matches=[c for c in comments if marker in (c.get('body') or '').splitlines()]
                        if matches:
                            event.update(comment_id=matches[0]['id'],reserved=True,posts=max(1,event['posts']));self.save(state,event,'delivered','Same-task resume input received; original work and history retained.')
                        elif client.execution(task['id']).get('runId')!=event['run_id'] or task.get('status') in ('done','cancelled'):
                            self.save(state,event,'superseded','Paperclip progressed independently; no duplicate resume input sent.')
                    if not self.eligible(observed):continue
                    finished=seconds(observed['run'].get('finishedAt'))
                    if finished is None or finished<enabled_at:continue
                    task=self.bound_task(client,observed['step']['id'],entry,connection);run=observed['run']['runId']
                    key=env.fingerprint({'request':entry['request'],'task':task['id'],'run':run})
                    event=state['events'].get(key)
                    if event and (event['status'] in ('delivered','blocked','superseded') or self.clock()<event.get('retry_at',0)):continue
                    if not event:
                        event={'request_id':identity,'task_id':task['id'],'run_id':run,'created_at':env.now(),'posts':0,'reserved':False}
                        state['events'][key]=event
                    marker='Grad-Compass administrative recovery '+key
                    comments=client.comments(task['id'])
                    if not isinstance(comments,list) or any(not isinstance(c,dict) for c in comments):raise ValueError('Recovery input readback is unavailable')
                    matches=[c for c in comments if marker in (c.get('body') or '').splitlines()]
                    if matches:
                        event.update(comment_id=matches[0]['id'],reserved=True,posts=max(1,event['posts']));self.save(state,event,'delivered','Same-task resume input received; original work and history retained.');continue
                    if (task.get('status')!='in_progress' or open_dependencies(task) or active_recovery(task.get('activeRecoveryAction'))
                        or task.get('scheduledRetry') or task.get('assigneeAgentId')!=client.execution(task['id']).get('agentId')):
                        raise WaitingGate('This task requires its existing dependency, recovery owner or assignment to be reconciled; no automatic resume was sent.')
                    for issue_id in {task['id'],entry['task']['id']}:
                        questions=client.call('/issues/'+issue_id+'/interactions')
                        if not isinstance(questions,list) or any(not isinstance(q,dict) for q in questions):raise ValueError('Required decision state cannot be verified')
                        if any(q.get('status')=='pending' for q in questions):raise WaitingGate('An existing decision is still pending. Automatic recovery will not bypass it.')
                    execution=observed['execution'];attempt=execution.get('attempt');limit=execution.get('maxAttempts')
                    if observed['run'].get('retryExhaustedReason') or (type(attempt) is int and type(limit) is int and attempt>=limit):
                        raise RecoveryGate('Paperclip reports its execution-attempt limit reached. Dave must inspect the existing task; no automatic resume was sent.')
                    if profile_reference(connection)!=entry['profile_reference']:raise RecoveryGate('The approved profile reference changed; technical reconciliation is required before recovery.')
                    used=sum(e.get('reserved',False) for e in state['events'].values() if e['request_id']==identity and e['task_id']==task['id'])
                    if not event['reserved'] and used>=2:raise RecoveryGate('Two automatic administrative recoveries were already used for this step. Dave must inspect the existing task; no duplicate research was submitted.')
                    if event['posts']>=2:raise RecoveryGate('Resume input delivery remains uncertain after two attempts. Dave must reconcile its saved marker; no further automatic resend.')
                    client.preflight(task['assigneeAgentId'])
                    # Recheck authoritative attempt immediately before mutation.
                    latest=client.execution(task['id']);current=client.issue(task['id'])
                    live=client.call('/issues/'+task['id']+'/live-runs')
                    if not isinstance(live,list):raise RecoveryGate('Active-execution state cannot be verified; no automatic resume was sent.')
                    if (latest.get('runId')!=run or latest.get('execution',{}).get('cause')!='orphaned_running_run'
                        or latest.get('execution',{}).get('phase') not in ('failed','recovery_needed') or live
                        or current.get('status')!='in_progress' or current.get('assigneeAgentId')!=task.get('assigneeAgentId')
                        or open_dependencies(current)):
                        self.save(state,event,'superseded','Paperclip progressed before recovery; no resume input sent.');continue
                    event['reserved']=True;event['posts']+=1
                    self.save(state,event,'prepared','Verified controller interruption; bounded same-task continuation prepared.')
                    client.call('/issues/'+task['id']+'/comments',{
                        'body':marker+'\nOwner-approved bounded administrative recovery for existing request '+identity+' after interrupted run '+run+'. The controller lost this execution. Resume ONLY this existing task: inspect saved progress and reuse completed artifacts, sources and review dispositions; finish only remaining authorized work. Preserve original scope, limits, request binding and history. Do not create a replacement request, repeat successful stages, bypass provider limits, change permissions or infer review/approval/release. If a substantive blocker remains, record its exact owner and action.',
                        'clientRequestId':str(uuid5(NAMESPACE_URL,marker)),'resume':True,'reopen':False,'interrupt':False})
                    event['retry_at']=self.clock()+60
                    self.save(state,event,'uncertain','Resume input sent; reconciling the saved receipt without duplicate work.')
                    comments=client.comments(task['id'])
                    matches=[c for c in comments if marker in (c.get('body') or '').splitlines()]
                    if matches:
                        event['comment_id']=matches[0]['id'];self.save(state,event,'delivered','Same-task resume input received; original work and history retained.')
                except OSError:
                    if event is not None and state['events'].get(key) is event:
                        event['retry_at']=self.clock()+60
                        self.save(state,event,'uncertain','Paperclip is unavailable; recovery receipt will reconcile on reconnect. No new request was created.')
                except (ValueError,KeyError,TypeError) as error:
                    if event is not None and state['events'].get(key) is event:
                        event['retry_at']=self.clock()+60
                        self.save(state,event,'deferred' if isinstance(error,WaitingGate) else 'blocked',str(error) if isinstance(error,RecoveryGate) else 'Automatic recovery could not verify its gates. Dave must reconcile this existing step; no new request was created.')
