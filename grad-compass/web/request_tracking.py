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
    """Only follow explicit dependency identities within the bound task/company."""
    root=client.issue(entry['task']['id'])
    binding={'request':entry['request'],'profile':entry['profile_reference'],'destination':entry['destination']}
    if (not isinstance(root,dict) or root.get('id')!=entry['task']['id'] or root.get('companyId')!=connection['company_id'] or root.get('assigneeAgentId')!=entry['destination']['dave_id']
        or not Dispatch.matches(root,'Grad-Compass dispatch '+entry['dispatch_key'],binding)):
        raise ValueError('Linked Paperclip task does not match the saved request. No recovery is allowed')
    candidates={root['id']:root}
    if not isinstance(root.get('blockedBy',[]),list):raise ValueError('Paperclip task dependencies have an unsupported shape')
    for blocker in root.get('blockedBy',[]):
        if not isinstance(blocker,dict) or not isinstance(blocker.get('terminalBlockers',[]),list):raise ValueError('Paperclip task dependencies have an unsupported shape')
        for item in [blocker,*blocker.get('terminalBlockers',[])]:
            if not isinstance(item,dict):raise ValueError('Paperclip task dependency identity is missing')
            env.identifier(item.get('id'));candidates.setdefault(item['id'],item)
    if len(candidates)>16:raise ValueError('Task dependency graph needs review in Paperclip')
    observations=[];unavailable_steps=[];diagnostic_notes=[]
    for identity,summary in candidates.items():
        # Finished siblings do not imply completion of the research request.
        if identity!=root['id'] and summary.get('status') in ('done','cancelled'):continue
        try:
            issue=root if identity==root['id'] else client.issue(identity)
            if not isinstance(issue,dict) or issue.get('companyId')!=connection['company_id'] or issue.get('id')!=identity:raise ValueError('Task dependency identity does not match')
            projection=client.execution(identity) or {}
        except (OSError,ValueError,KeyError,TypeError):
            if identity==root['id']:raise
            unavailable_steps.append(identity);continue
        if not isinstance(projection,dict):raise ValueError('Paperclip execution status has an unsupported shape')
        execution=projection.get('execution') or {}
        if not isinstance(execution,dict):raise ValueError('Paperclip execution status has an unsupported shape')
        if projection.get('runId') is not None:env.identifier(projection['runId'])
        recovery=projection.get('recoveryAction') or issue.get('activeRecoveryAction')
        if recovery is not None and not isinstance(recovery,dict):raise ValueError('Paperclip recovery status has an unsupported shape')
        observations.append((issue,projection,execution,recovery))
    def rank(item):
        issue,projection,execution,recovery=item
        return (execution.get('phase') in ('failed','recovery_needed'),bool(recovery),issue.get('status')=='blocked',execution.get('phase') in ('running','executing'),issue['id']!=root['id'])
    issue,projection,execution,recovery=max(observations,key=rank)
    run_id=projection.get('runId');run={};failure=None;run_history=[]
    if run_id:
        try:
            values=client.runs(issue['id'])
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
    return {'task':{k:root.get(k) for k in ('id','identifier','status','updatedAt')},
        'step':{k:issue.get(k) for k in ('id','identifier','title','status','updatedAt')},
        'task_url':issue_link(connection,root),'recovery_url':issue_link(connection,issue),
        'run':safe_run,'run_history':run_history,'execution':safe_execution,'recovery':safe_recovery,'failure':failure,
        'scheduled_retry':bool(issue.get('scheduledRetry')),'unavailable_steps':unavailable_steps,'diagnostic_notes':diagnostic_notes,'observed_at':env.now()}


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
        return {'requests':rows,'attention_count':sum(r['needs_attention'] for r in rows),'unassociated_delivery_errors':[e for e in errors if not e.get('request_id')],'checked_at':env.now()}
    def describe(self,row):
        latest=row['tracking'].get('latest',{});execution=latest.get('execution',{});phase=execution.get('phase');dispatch=row['dispatch_status']
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
                elif phase in ('failed','recovery_needed'):
                    state='failed';label='Research step failed' if phase=='failed' else 'Recovery required'
                    notice='A research step stopped. Existing saved work is preserved.'
                    if latest.get('failure') and 'not trusted' in latest['failure']:
                        notice='The researcher could not start because its working folder was not trusted. The runtime setup must be repaired before an explicit retry.'
                elif task_status=='cancelled':state='cancelled';label='Paperclip task cancelled';notice='The accepted task was cancelled in Paperclip. Its request and any saved work remain.'
                elif task_status=='blocked':state='blocked';label='Waiting on a blocked step';notice='The assigned work needs attention in Paperclip. No automatic restart is requested.'
                elif task_status=='done':state='awaiting_delivery';label='Execution finished — waiting for report delivery'
                elif not row['results_count']:state='active';label='Research in progress' if phase in ('running','executing') else 'Accepted — waiting for the next step'
            if ready:
                label=('Reports available' if ready==total else 'Some reports available')+(' · task needs attention' if state in ('failed','blocked') else '')
                if state not in ('failed','blocked','cancelled','retry_scheduled'):
                    bounded=row.get('response_completion')=='complete'
                    outstanding=row.get('batch_progress',{}).get('outstanding_count',0)
                    state='complete' if ready==total and bounded and not outstanding else 'partial_reports'
                    if ready==total and not bounded:label+=' · response '+('partial' if row.get('response_completion')=='partial' else 'not complete')
                    if outstanding:label+=' · deliverables outstanding'
        activity=execution.get('lastConfirmedActivityAt') or latest.get('step',{}).get('updatedAt') or row['created_at'];stamp=seconds(activity)
        delayed=state in ('active','waiting','findings','awaiting_delivery','retry_scheduled') and stamp is not None and self.clock()-stamp>STALE_SECONDS
        if delayed and not notice:notice='No recent progress has been reported. Refresh status or open the task; this is not a confirmed failure.'
        elif delayed and state=='retry_scheduled':notice+=' No recent progress has been reported; refresh or inspect the existing retry in Paperclip.'
        if row['delivery_errors']:notice='An incoming response could not be validated or recorded. Earlier findings and reports are preserved.'
        offline=row['tracking'].get('connection_error')
        row.update(status=state,label=label,stage=stage,notice=notice,delayed=delayed,needs_attention=bool(notice or offline),updated_at=max(latest.get('step',{}).get('updatedAt') or row['created_at'],row.get('local_updated_at') or row['created_at'],row.get('dispatch_updated_at') or row['created_at']),last_activity_at=activity,
            work_saved=(str(row['results_count'])+' received result revision(s); '+str(ready)+' prepared country report(s). Earlier versions and annotations are preserved.') if row['results_count'] or ready else 'No findings or prepared reports have been received for this request. Its request and acknowledgement history are saved.',
            next_action='Open the existing step’s recovery card in Paperclip. A board operator must review the recorded failure, repair any runtime issue and explicitly resume the original owner within the same scope. The app will not submit another task.' if state=='failed' else 'Open the existing task to see its assigned owner and unresolved dependency. A blocked stage is separate from a confirmed execution failure; do not submit another request.' if state=='blocked' else 'Refresh status to check progress; responses are received automatically.',
            task_url=latest.get('task_url') or row.get('task_url'),recovery_url=latest.get('recovery_url'),last_checked_at=row['tracking'].get('last_attempt_at'),last_success_at=row['tracking'].get('last_success_at'))
        return row
