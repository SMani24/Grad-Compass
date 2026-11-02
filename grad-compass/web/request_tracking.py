"""Persistent execution observations, separate from immutable research and reviews.

Polling is GET-only. Recovery controls never create an issue or infer acceptance.
"""
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl,os,time,re
from copy import deepcopy
from web import research_envelopes as env
from web.local import regular
from web.dispatch import Dispatch,Paperclip,config,durable
from web.execution_status import ADMINISTRATIVE_CANCELLATIONS,active_recovery,closed_cancellation,foreign_wake_resolution,assess,older

VERSION='grad-compass-request-tracking-1'
STALE_SECONDS=1800


def seconds(value):
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
    except (ValueError,TypeError,AttributeError):return None


@contextmanager
def tracking_lock(workspace):
    with workspace.state_lock:
        fd=os.open(regular(workspace.directory/'.request-tracking.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'r+') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX);yield


class StatusClient(Paperclip):
    def issue(self,identity):return self.call('/issues/'+env.identifier(identity))
    def execution(self,identity):return self.call('/issues/'+env.identifier(identity)+'/execution')
    def runs(self,identity):return self.call('/issues/'+env.identifier(identity)+'/runs')
    def comments(self,identity):return self.call('/issues/'+env.identifier(identity)+'/comments')


def issue_link(connection,issue):
    env.identifier(issue['id']);identifier=issue.get('identifier','')
    match=re.fullmatch(r'([A-Z][A-Z0-9]*)-[0-9]+',identifier)
    # Producer-confirmed company-prefixed route; do not promise a UUID alias.
    return connection['url'].rstrip('/')+'/'+match[1]+'/issues/'+identifier if match else None


def inspect(client,entry,connection):
    """Follow explicit dependencies and verified descendants of the bound task."""
    root=client.issue(entry['task']['id'])
    binding={'request':entry['request'],'profile':entry['profile_reference'],'destination':entry['destination']}
    if (not isinstance(root,dict) or root.get('id')!=entry['task']['id'] or root.get('companyId')!=connection['company_id'] or root.get('assigneeAgentId')!=entry['destination']['dave_id']
        or not Dispatch.matches(root,'Grad-Compass dispatch '+entry['dispatch_key'],binding)):
        raise ValueError('Linked Paperclip task does not match the saved request. No recovery is allowed')
    candidates={root['id']:root};depth={root['id']:0}
    if not isinstance(root.get('blockedBy',[]),list):raise ValueError('Paperclip task dependencies have an unsupported shape')
    for blocker in root.get('blockedBy',[]):
        if not isinstance(blocker,dict) or not isinstance(blocker.get('terminalBlockers',[]),list):raise ValueError('Paperclip task dependencies have an unsupported shape')
        for item in [blocker,*blocker.get('terminalBlockers',[])]:
            if not isinstance(item,dict):raise ValueError('Paperclip task dependency identity is missing')
            env.identifier(item.get('id'));candidates.setdefault(item['id'],item)
            depth[item['id']]=max(depth.get(item['id'],0),1 if item is blocker else 2)
    # A coordinator can be blocked on a technical decision while an independent
    # research child has failed. Dependencies alone hide that stopped execution.
    children=client.call('/companies/'+connection['company_id']+'/issues?descendantOf='+root['id']+'&limit=17')
    if not isinstance(children,list) or len(children)>16:
        raise ValueError('Research child-step status needs review in Paperclip. The last known state is retained.')
    descendants={}
    for child in children:
        if not isinstance(child,dict) or child.get('companyId')!=connection['company_id']:
            raise ValueError('Research child-step identity does not match the saved request')
        identity=env.identifier(child.get('id'));env.identifier(child.get('parentId'))
        if identity==root['id'] or identity in descendants:
            raise ValueError('Research child-step ancestry is ambiguous')
        descendants[identity]=child
    for identity,child in descendants.items():
        seen={identity};parent=child['parentId'];level=1
        while parent!=root['id']:
            if parent in seen or parent not in descendants:
                raise ValueError('Research child-step is not bound to the saved request')
            seen.add(parent);parent=descendants[parent]['parentId'];level+=1
        if child.get('status') not in ('done','cancelled') or active_recovery(child.get('activeRecoveryAction')) or child.get('scheduledRetry'):
            candidates[identity]=child;depth[identity]=max(depth.get(identity,0),level)
    if len(candidates)>16:raise ValueError('Task dependency graph needs review in Paperclip')
    observations=[];unavailable_steps=[];diagnostic_notes=[]
    for identity,summary in candidates.items():
        # Finished siblings do not imply completion of the research request.
        if identity!=root['id'] and summary.get('status') in ('done','cancelled') and not active_recovery(summary.get('activeRecoveryAction')) and not summary.get('scheduledRetry'):continue
        try:
            issue=root if identity==root['id'] else client.issue(identity)
            if not isinstance(issue,dict) or issue.get('companyId')!=connection['company_id'] or issue.get('id')!=identity:raise ValueError('Task dependency identity does not match')
            projection=client.execution(identity) or {}
        except (OSError,ValueError,KeyError,TypeError):
            if identity==root['id']:raise
            unavailable_steps.append(identity);continue
        if identity in descendants and issue.get('parentId')!=descendants[identity]['parentId']:
            raise ValueError('Research child-step changed its request association during refresh')
        if not isinstance(projection,dict):raise ValueError('Paperclip execution status has an unsupported shape')
        execution=projection.get('execution') or {}
        if not isinstance(execution,dict):raise ValueError('Paperclip execution status has an unsupported shape')
        if projection.get('runId') is not None:env.identifier(projection['runId'])
        recovery=projection.get('recoveryAction') or issue.get('activeRecoveryAction')
        if recovery is not None and not isinstance(recovery,dict):raise ValueError('Paperclip recovery status has an unsupported shape')
        reconciled=None;attempts=None
        if execution.get('cause')=='issue_assignee_changed' and execution.get('phase') in ('failed','recovery_needed'):
            try:
                attempts=client.runs(identity)
                interactions=client.call('/issues/'+identity+'/interactions')
                reconciled=foreign_wake_resolution(issue,projection,recovery,attempts,interactions)
            except (OSError,ValueError,KeyError,TypeError):pass  # Unverified cancellation stays unresolved.
        observations.append((issue,projection,execution,recovery,reconciled,attempts))
    def rank(item):
        issue,projection,execution,recovery,reconciled,attempts=item
        stopped=execution.get('phase') in ('failed','recovery_needed') and not reconciled and not closed_cancellation({**issue,'blockedBy':[]},execution,recovery)
        # After preparation hands back to delivery, the deeper preparer can be
        # idle while its coordinator actively validates. Keep actual stops and
        # decision gates first, then select real work before an idle deeper wait.
        substantive_stop=stopped and execution.get('cause') not in ADMINISTRATIVE_CANCELLATIONS
        return (substantive_stop,stopped,active_recovery(recovery),execution.get('phase')=='waiting_for_answer',
                execution.get('phase') in ('working','running','executing'),depth[issue['id']],issue.get('status')=='blocked')
    issue,projection,execution,recovery,reconciled,attempts=max(observations,key=rank)
    run_id=projection.get('runId');run={};failure=None;run_history=[]
    if run_id:
        try:
            values=attempts if attempts is not None else client.runs(issue['id'])
            if not isinstance(values,list) or any(not isinstance(r,dict) for r in values):raise ValueError()
        except (OSError,ValueError,TypeError):values=[];diagnostic_notes.append('Attempt details could not be read; the execution projection remains authoritative.')
        matching=[r for r in values if r.get('contextIssueId')==issue['id'] and r.get('agentId')==projection.get('agentId')]
        run=next((r for r in matching if r.get('runId')==run_id),{})
        run_history=[{k:r.get(k) for k in ('runId','status','startedAt','finishedAt','errorCode','retryOfRunId')} for r in matching]
    if execution.get('phase') in ('failed','recovery_needed') and run_id:
        try:
            values=client.comments(issue['id'])
            if not isinstance(values,list) or any(not isinstance(c,dict) for c in values):raise ValueError()
        except (OSError,ValueError,TypeError):values=[];diagnostic_notes.append('Failure details require access in Paperclip; the recorded failure state is retained.')
        for comment in values:
            metadata=comment.get('metadata') or {}
            if not isinstance(metadata,dict):continue
            if comment.get('authorType')!='system' or metadata.get('sourceRunId')!=run_id:continue
            sections=metadata.get('sections',[])
            if not isinstance(sections,list):continue
            for section in sections:
                if not isinstance(section,dict) or not isinstance(section.get('rows',[]),list):continue
                for row in section.get('rows',[]):
                    if not isinstance(row,dict):continue
                    if row.get('label')=='Failure summary' and isinstance(row.get('value'),str):failure=row['value'][:1000]
    # Do not turn privileged stderr or arbitrary comments into a browser API.
    # Recognized safe diagnoses use app-owned wording; raw logs stay in Paperclip.
    if failure:
        if 'Not inside a trusted directory' in failure:failure='The execution working directory was not trusted by the research runtime.'
        elif any(term in failure.lower() for term in ('usage limit','quota exceeded','rate limit')):failure='The execution provider reported a usage or rate limit. Its restrictions must be respected before retrying.'
        else:failure='Paperclip recorded failure details. Open the task for the authorized diagnostic.'
    safe_execution={k:execution.get(k) for k in ('phase','label','cause','lastConfirmedActivityAt','retryAt','attempt','maxAttempts','permittedActions','predecessorRunId','successorRunId')}
    safe_run={k:run.get(k) for k in ('runId','status','startedAt','finishedAt','errorCode','retryExhaustedReason','retryOfRunId')}
    safe_recovery={k:recovery.get(k) for k in ('id','kind','status','ownerType','cause','nextAction')} if recovery else None
    work=reconciled or assess(issue,execution,recovery,run,matching if run_id else [])
    descriptor=issue.get('unblockDescriptor')
    blocker={k:descriptor.get(k) for k in ('owner','action')} if isinstance(descriptor,dict) else None
    agent_decision=None
    if issue.get('status')=='in_review':
        try:
            interactions=client.call('/issues/'+issue['id']+'/interactions')
            if isinstance(interactions,list):
                pending=next((v for v in interactions if isinstance(v,dict) and v.get('status')=='pending'
                    and v.get('companyId')==connection['company_id'] and v.get('issueId')==issue['id']
                    and v.get('addresseeAgentId') and v.get('effectiveResolverPolicy')=='anyone'),None)
                if pending:agent_decision={k:pending.get(k) for k in ('id','addresseeAgentId','createdAt')}
        except (ValueError,OSError):pass  # An unreadable/unsupported interaction never implies approval.
    # Issue and attempt endpoints are separate reads. Reject a mixed transition
    # instead of briefly presenting an old failure as the new task's state.
    def stamp(value):
        if not isinstance(value,dict):raise ValueError('Paperclip task readback has an unsupported shape; the last known state is retained.')
        return [value.get(k) for k in ('id','statusVersion','status','updatedAt','assigneeAgentId','activeRecoveryAction')]+[value.get('blockedBy',[])]
    if stamp(client.issue(root['id']))!=stamp(root) or issue['id']!=root['id'] and stamp(client.issue(issue['id']))!=stamp(issue):
        raise ValueError('Paperclip changed during the status check. The last known state is retained; refresh again.')
    return {'task':{k:root.get(k) for k in ('id','identifier','status','updatedAt','completedAt','statusVersion')},
        'step':{k:issue.get(k) for k in ('id','identifier','title','status','updatedAt','completedAt','statusVersion')},
        'task_url':issue_link(connection,root),'recovery_url':issue_link(connection,issue),
        'run':safe_run,'run_history':run_history,'execution':safe_execution,'recovery':safe_recovery,'failure':failure,
        'current_work':work,'blocker':blocker,'agent_decision':agent_decision,'scheduled_retry':bool(issue.get('scheduledRetry')),'unavailable_steps':unavailable_steps,'diagnostic_notes':diagnostic_notes,'observed_at':env.now()}


class RequestTracker:
    def __init__(self,workspace,client_factory=StatusClient,clock=time.time):
        self.workspace=workspace;self.path=regular(workspace.directory/'request-tracking.json');self.client_factory=client_factory;self.clock=clock
    def read(self):
        value=env.loads(self.path.read_bytes()) if self.path.exists() else {'schema_version':VERSION,'requests':{}}
        if value.get('schema_version')!=VERSION or not isinstance(value.get('requests'),dict):raise ValueError('Request tracking needs recovery; saved research is unchanged')
        return value
    def observe_delivery(self,errors):
        grouped={}
        for error in errors:
            if error.get('request_id'):grouped.setdefault(error['request_id'],[]).append(error)
        with tracking_lock(self.workspace):
            state=self.read();changed=False
            identities=set(grouped)|{k for k,v in state['requests'].items() if v.get('delivery_errors')}
            for identity in identities:
                row=state['requests'].setdefault(identity,{'history':[]});current=grouped.get(identity,[])
                if row.get('delivery_errors',[])==current:continue
                row['delivery_errors']=current;row['history'].append({'kind':'delivery','observed_at':env.now(),'errors':deepcopy(current)});changed=True
            if changed:durable(self.path,state)
    def refresh(self,request_id=None):
        # No remote calls while holding the local state lock. A busy refresh is
        # coalesced rather than duplicated by app-open, timer and explicit refresh.
        if not hasattr(self.workspace,'request_refresh_lock'):
            import threading
            with self.workspace.state_lock:
                if not hasattr(self.workspace,'request_refresh_lock'):self.workspace.request_refresh_lock=threading.Lock()
        if not self.workspace.request_refresh_lock.acquire(blocking=False):return {'refreshing':True}
        try:
            entries=Dispatch(self.workspace).snapshot()['entries']
            if request_id and not any(e.get('request',{}).get('id')==request_id for e in entries if e.get('request')):
                # Manual requests have no remote association; never guess by country.
                self.workspace.research.request(request_id);return {'refreshing':False}
            for entry in entries:
                if entry['status']!='accepted' or request_id and entry['request']['id']!=request_id:continue
                identity=entry['request']['id'];attempted=env.now()
                try:
                    connection=config(self.workspace)
                    if not connection or entry['destination']!={'company_id':connection['company_id'],'dave_id':connection['dave_id']}:raise ValueError('The configured Paperclip destination differs from this saved request')
                    current=self.workspace.research.request(identity)['request']
                    if (current['revision'],current['digest'])!=(entry['request']['revision'],entry['request']['sha256']):raise ValueError('Saved request identity changed; preserve it for recovery')
                    observation=inspect(self.client_factory(connection),entry,connection);problem=None
                except (OSError,ValueError,KeyError,TypeError) as error:
                    observation=None;problem=str(error) if isinstance(error,ValueError) else 'Paperclip status cannot currently be refreshed. Your last known state and saved work are retained.'
                with tracking_lock(self.workspace):
                    state=self.read();row=state['requests'].setdefault(identity,{'history':[]})
                    row['last_attempt_at']=attempted;row['connection_error']=problem
                    if observation and row.get('latest',{}).get('step',{}).get('id') in observation.get('unavailable_steps',[]):
                        row['connection_error']='The previously observed step cannot currently be refreshed. Its last known state is retained.';observation=None
                    if observation and older(observation,row.get('latest')):
                        row['refresh_note']='An older Paperclip update was ignored; the latest confirmed state is retained.';observation=None
                    elif observation:row.pop('refresh_note',None)
                    if observation is not None:
                        signature=env.fingerprint({k:v for k,v in observation.items() if k!='observed_at'})
                        if row.get('signature')!=signature:
                            row['history'].append(deepcopy(observation));row['signature']=signature
                        row['latest']=observation;row['last_success_at']=attempted
                    durable(self.path,state)
            return {'refreshing':False}
        finally:self.workspace.request_refresh_lock.release()
    def snapshot(self):
        from web import report_packages
        with tracking_lock(self.workspace):state=deepcopy(self.read())
        research=self.workspace.research.snapshot();entries=Dispatch(self.workspace).snapshot()['entries']
        reports=report_packages.catalog(self.workspace)['reports']
        receiver=getattr(self.workspace,'inbox_receiver',None)
        errors=receiver.status()['errors'] if receiver else []
        rows=[];by_request={e['request']['id']:e for e in entries if e.get('request')}
        from web.asset_jobs import summaries
        assets=summaries(self.workspace)
        from web.execution_recovery import records
        recovery_error=[]
        try:recoveries=list(records(self.workspace)['events'].values())
        except (OSError,ValueError):recoveries=[];recovery_error=[{'file':'Automatic recovery','error':'Recovery history cannot be read. Saved requests and original research are retained; technical reconciliation is required.'}]
        for summary in research['requests']:
            detail=self.workspace.research.request(summary['request_id']);request=detail['request'];identity=request['request_id'];entry=by_request.get(identity)
            prepared={r['metadata']['country_code']:r for r in reversed(reports) if r['metadata']['request']['id']==identity and r['model']['kind']=='prepared_report'}
            from web import batch_progress
            report_states=batch_progress.countries(request['countries'],prepared,request['scope']=='country_conditions' or bool(prepared))
            track=state['requests'].get(identity,{})
            row={'id':identity,'request_id':identity,'countries':request['countries'],'scope':request['scope'],'intake':request['preferences'].get('intake'),'created_at':request['created_at'],
                'dispatch_id':entry['id'] if entry else None,'dispatch_status':entry['status'] if entry else 'manual','dispatch_updated_at':(entry.get('updated_at') or entry.get('accepted_at') or entry.get('confirmed_at') or entry['created_at']) if entry else request['created_at'],
                'task':entry.get('task') if entry else None,'tracking':track,'acknowledgement':summary['state'],'response_completion':summary.get('completion'),
                'dispatch_history':entry.get('attempt_history',[]) if entry else [],
                'results_count':len(detail['results']),'reports':report_states,'delivery_errors':[e for e in errors if e.get('request_id')==identity] if receiver else track.get('delivery_errors',[])}
            row['asset_jobs']=[a for a in assets if a['request_id']==identity]
            row['automatic_recovery']=[e for e in recoveries if e['request_id']==identity]
            dates=[request['created_at'],*[x['envelope'].get('issued_at') or x['envelope'].get('created_at') or request['created_at'] for x in detail['results']]]
            if detail.get('acknowledgement'):dates.append(detail['acknowledgement'].get('acknowledged_at') or request['created_at'])
            row['local_updated_at']=max(dates)
            if entry and entry.get('task'):
                try:
                    connection=config(self.workspace)
                    if connection and entry['destination']=={'company_id':connection['company_id'],'dave_id':connection['dave_id']}:row['task_url']=issue_link(connection,entry['task'])
                except (ValueError,OSError):pass
            row['batch_progress']=batch_progress.summary(report_states,summary.get('completion'))
            row['execution_progress']=summary.get('execution_progress')
            rows.append(self.describe(row))
        for entry in reversed(entries):
            if entry.get('request'):continue
            rows.append(self.describe({'id':'draft:'+entry['id'],'request_id':None,'dispatch_id':entry['id'],'dispatch_status':entry['status'],'dispatch_updated_at':entry.get('updated_at') or entry['created_at'],'countries':entry['payload']['countries'],'scope':entry['payload']['scope'],'intake':entry['payload']['preferences'].get('intake'),'created_at':entry['created_at'],'task':None,'tracking':{},'reports':[],'results_count':0,'delivery_errors':[]}))
        rows.sort(key=lambda r:r['created_at'],reverse=True)
        asset_errors=[{'file':'Asset job '+a.get('file','unknown'),'error':a['error']['message']} for a in assets if not a.get('request_id') and a.get('error')]
        return {'requests':rows,'attention_count':sum(r['needs_attention'] for r in rows),'unassociated_delivery_errors':[e for e in errors if not e.get('request_id')]+asset_errors+recovery_error,'checked_at':env.now()}
    def describe(self,row):
        latest=row['tracking'].get('latest',{});execution=latest.get('execution',{});phase=execution.get('phase');dispatch=row['dispatch_status']
        work=latest.get('current_work',{});resolved=work.get('state')=='resolved'
        state='waiting';label='Saved — waiting for acknowledgement';stage='Manual handoff';notice=None
        ready=sum(r['available'] for r in row['reports']);total=len(row['countries'])
        if dispatch in ('draft','pending','uncertain','dispatching','cancelled','superseded'):
            state=dispatch;label={'draft':'Draft — not submitted','pending':'Pending dispatch','uncertain':'Dispatch receipt uncertain','dispatching':'Dispatch attempt recorded','cancelled':'Cancelled — history retained','superseded':'Replaced — history retained'}[state];stage='Dispatch'
            if state=='uncertain':notice='Delivery may already be accepted. Review and retry to reconcile the existing task.'
        else:
            stage=latest.get('step',{}).get('title') or ('Awaiting research' if row.get('acknowledgement')=='accepted' else 'Awaiting acknowledgement')
            if row['results_count']:state='findings';label='Findings received — report delivery is separate'
            elif row.get('acknowledgement')=='accepted':state='active';label='Acknowledged — awaiting research progress'
            elif row.get('acknowledgement') in ('rejected','needs_clarification'):
                state='blocked';label='Request needs clarification' if row['acknowledgement']=='needs_clarification' else 'Request declined';notice='Review the saved acknowledgement before preparing an explicit amendment.'
            if latest:
                task_status=latest['task']['status']
                if latest.get('scheduled_retry'):
                    state='retry_scheduled';label='Paperclip retry scheduled';notice='Paperclip has a scheduled retry. No additional retry will be started by the app.'
                elif (phase in ('failed','recovery_needed') and not resolved) or work.get('state')=='unresolved':
                    state='failed';label='Research step failed' if phase=='failed' else 'Recovery required'
                    step=latest.get('step',{});name=step.get('title') or 'Research execution'
                    if name.startswith('Grad Compass:'):name='Country report coordination'
                    notice=name+' ('+(step.get('identifier') or 'linked task')+') stopped. Existing findings and reports are preserved.'
                    if work.get('reason')=='post_completion_failure':notice+=' Paperclip has not reconciled this attempt with its completed task; the recorded recovery must be checked.'
                    if latest.get('failure') and 'not trusted' in latest['failure']:
                        notice+=' The assigned runtime could not start because its working folder was not trusted; its setup needs repair before an explicit retry.'
                    if execution.get('cause')=='provider_quota':
                        state='blocked';label='Paused — provider usage limit'
                        notice=name+' reached the research provider’s usage limit. The saved request, received originals and completed work remain intact; this is not a new request or lost research.'
                elif task_status=='cancelled':state='cancelled';label='Paperclip task cancelled';notice='The accepted task was cancelled in Paperclip. Its request and any saved work remain.'
                elif task_status=='blocked' and latest.get('agent_decision'):
                    state='active';label='Awaiting a research-team decision'
                elif task_status=='blocked' and latest.get('step',{}).get('status')=='in_progress':
                    state='active';label='Assigned step in progress'
                elif task_status=='blocked':
                    state='blocked';label='Waiting on a blocked step'
                    name=latest.get('step',{}).get('title') or 'The assigned step'
                    if name.startswith('Grad Compass:'):name='Country report coordination'
                    notice=name+' is waiting. Existing reports and research remain available; this is separate from an execution failure.'
                elif task_status=='done':state='awaiting_delivery';label='Execution finished — waiting for report delivery'
                elif not row['results_count']:state='active';label='Research in progress' if phase in ('running','executing') else 'Accepted — waiting for the next step'
            if ready:
                label=('Reports available' if ready==total else 'Some reports available')+(' · task needs attention' if state=='failed' else ' · step waiting' if state=='blocked' else '')
                if state=='blocked' and execution.get('cause')=='provider_quota':label=('Reports available' if ready==total else 'Some reports available')+' · provider usage limit'
                if state not in ('failed','blocked','cancelled','retry_scheduled'):
                    bounded=row.get('response_completion')=='complete'
                    outstanding=row.get('batch_progress',{}).get('outstanding_count',0)
                    execution_done=not latest or resolved or work.get('state')=='complete' or latest.get('task',{}).get('status')=='done'
                    state='complete' if ready==total and bounded and not outstanding and execution_done else 'partial_reports'
                    if state=='complete':label+=' · request complete'
                    if ready==total and not bounded:label+=' · response '+('partial' if row.get('response_completion')=='partial' else 'not complete')
                    if outstanding:label+=' · deliverables outstanding'
        activity=execution.get('lastConfirmedActivityAt') or latest.get('step',{}).get('updatedAt') or row['created_at'];stamp=seconds(activity)
        decision_at=(latest.get('agent_decision') or {}).get('createdAt');decision_stamp=seconds(decision_at)
        if decision_stamp is not None and (stamp is None or decision_stamp>stamp):activity=decision_at;stamp=decision_stamp
        delayed=state in ('active','waiting','findings','awaiting_delivery','retry_scheduled') and stamp is not None and self.clock()-stamp>STALE_SECONDS
        if delayed and not notice:notice='No recent progress has been reported. Refresh status or open the task; this is not a confirmed failure.'
        elif delayed and state=='retry_scheduled':notice+=' No recent progress has been reported; refresh or inspect the existing retry in Paperclip.'
        if row['delivery_errors']:notice='An incoming response could not be validated or recorded. Earlier findings and reports are preserved.'
        offline=row['tracking'].get('connection_error')
        next_action='Refresh status to check progress; responses are received automatically.'
        if state=='complete':next_action='No recovery action is needed. Reports are ready for inspection; factual review and human approval remain separate.'
        elif state=='failed':
            recovery=latest.get('recovery') or {}
            action=recovery.get('nextAction') if active_recovery(recovery) else None
            if latest.get('failure') and 'not trusted' in latest['failure']:action='Repair the assigned runtime’s trusted working-folder configuration, then explicitly resume this existing step.'
            elif latest.get('failure') and 'usage or rate limit' in latest['failure']:action='Wait for the provider limit to clear, then review the existing step’s supported recovery action.'
            next_action=(action[:1000] if isinstance(action,str) and action.strip() else 'Dave must reconcile the stopped attempt and any unfinished deliverable in the linked task before resuming only the necessary step.')+' Completed research must be reused; do not submit another request.'
        elif state=='blocked':
            action=(latest.get('blocker') or {}).get('action')
            next_action=(action[:1000] if isinstance(action,str) and action.strip() else 'Open the linked step to see its assigned owner and unresolved dependency.')+' Reuse the existing request and completed work; no replacement request is needed.'
            if execution.get('cause')=='provider_quota':
                next_action='Dave must resume only the existing interrupted step once the provider permits execution. Do not repeat completed downloads or submit the request again; no quota bypass or immediate retry loop.'
        if row['delivery_errors']:next_action='Inspect the recorded incoming-response error and repair or redeliver that exact response through recovery. Do not repeat successful research.'
        asset_failures=[a for a in row.get('asset_jobs',[]) if a['status']=='failed']
        # A later successful candidate supersedes the earlier acquisition failure,
        # whose immutable receipt remains in technical history.
        recovered={a['country_code'] for a in row.get('asset_jobs',[]) if a['status']=='downloaded'}
        asset_failures=[a for a in asset_failures if a['country_code'] not in recovered]
        if asset_failures:
            notice='Country photograph retrieval needs recovery: '+asset_failures[0]['error']['message']
            next_action=asset_failures[0]['error']['action']
            if state!='failed':
                state='blocked';label='Reports available · photograph needs recovery' if ready else 'Photograph needs recovery'
        event_wait=any(a.get('event_status')=='pending' for a in row.get('asset_jobs',[]))
        if event_wait and not notice:
            invalid_event=next((a for a in row.get('asset_jobs',[]) if a.get('event_status')=='pending' and a.get('event_error_kind')=='validation'),None)
            notice=('The photograph outcome needs delivery repair: '+invalid_event['event_message']) if invalid_event else 'The photograph outcome is saved; Paperclip notification is waiting for reconnect. No research will be restarted.'
        row.update(status=state,label=label,stage=stage,notice=notice,delayed=delayed,needs_attention=bool(notice or offline),updated_at=max(latest.get('step',{}).get('updatedAt') or row['created_at'],row.get('local_updated_at') or row['created_at'],row.get('dispatch_updated_at') or row['created_at']),last_activity_at=activity,
            work_saved=(str(row['results_count'])+' received result revision(s); '+str(ready)+' prepared country report(s). Earlier versions and annotations are preserved.') if row['results_count'] or ready else 'No findings or prepared reports have been received for this request. Its request and acknowledgement history are saved.',
            execution_health=work.get('state') or ('unresolved' if state=='failed' else 'unknown'),execution_resolution=work if resolved else None,next_action=next_action,
            task_url=latest.get('task_url') or row.get('task_url'),recovery_url=latest.get('recovery_url'),last_checked_at=row['tracking'].get('last_attempt_at'),last_success_at=row['tracking'].get('last_success_at'))
        return row
