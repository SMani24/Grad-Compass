"""Explicit local dispatch with immutable requests and a durable per-profile outbox.

Nothing in this module runs on startup, polling or reconnection. Paperclip's
atomic company/idempotency-key transaction is required, not search-then-create.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit,quote
import urllib.request
from uuid import uuid4
from web.local import regular,atomic_json
from web import research_envelopes as env

VERSION='grad-compass-dispatch-1'
RETENTION_SECONDS=7*86400


def durable(path,value):
    atomic_json(path,value)
    with path.open('rb') as stream:os.fsync(stream.fileno())
    descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


@contextmanager
def lock(workspace):
    with workspace.state_lock:
        path=regular(workspace.directory/'.dispatch.lock')
        descriptor=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,'r+') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX);yield


def config(workspace):
    path=regular(workspace.directory/'paperclip-connection.local.json')
    if not path.exists():return None
    value=env.loads(path.read_bytes());parsed=urlsplit(value.get('url',''))
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost') or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Use the configured local Paperclip connection')
    env.identifier(value.get('company_id'));env.identifier(value.get('dave_id'))
    if value.get('atomic_idempotency') is not True:raise ValueError('Paperclip atomic dispatch compatibility has not been verified')
    return value


def profile_reference(connection):
    if not connection:return None
    root=Path(connection.get('approved_profile_directory',''))
    if not root.is_absolute() or any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('Approved profile reference is unavailable')
    receipt=env.loads(regular(root/'receipt.json').read_bytes())
    if regular(root/'COMPLETE').read_text().strip()!='complete' or receipt.get('decision')!='accepted' or receipt.get('actor_type')!='human' or receipt.get('reliable_for_discovery') is not True:raise ValueError('The profile has no verified human approval/completion receipt')
    digest=hashlib.sha256(regular(root/'profile.json').read_bytes()).hexdigest()
    if digest!=receipt.get('sha256'):raise ValueError('Approved profile bytes no longer match their receipt')
    # References only. No profile content crosses the app API or issue payload.
    return {'id':receipt['profile_id'],'revision':receipt['revision_id'],'sha256':digest,'receipt_id':receipt['receipt_id'],'approved_at':receipt['approved_at'],'approval':'accepted'}


class Paperclip:
    def __init__(self,connection):self.connection=connection
    def call(self,path,data=None):
        headers={'Content-Type':'application/json'}
        token=os.environ.get('GRAD_COMPASS_PAPERCLIP_TOKEN')
        if token:headers['Authorization']='Bearer '+token
        # Never follow redirects with private handoffs or credentials.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        req=urllib.request.Request(self.connection['url'].rstrip('/')+'/api'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        with urllib.request.build_opener(NoRedirect).open(req,timeout=12) as response:
            raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError('Paperclip response exceeds the local limit')
            return env.loads(raw)
    def available(self):return self.call('/companies/'+self.connection['company_id'])
    def create(self,payload):return self.call('/companies/'+self.connection['company_id']+'/issues',payload)
    def reconcile(self,marker):
        values=self.call('/companies/'+self.connection['company_id']+'/issues?q='+quote(marker))
        matches=[item for item in values if marker in (item.get('description') or '')]
        if len(matches)>1:raise ValueError('Conflicting Paperclip tasks require technical reconciliation; no task was created')
        return matches[0] if matches else None


class Dispatch:
    def __init__(self,workspace,client_factory=None,clock=time.time):self.workspace=workspace;self.client_factory=client_factory or Paperclip;self.clock=clock;self.path=regular(workspace.directory/'dispatch-outbox.json')
    def read(self):
        value=env.loads(self.path.read_bytes()) if self.path.exists() else {'schema_version':VERSION,'entries':[]}
        if value.get('schema_version')!=VERSION or not isinstance(value.get('entries'),list):raise ValueError('Invalid private dispatch outbox; preserve it for recovery')
        return value
    def write(self,state):durable(self.path,state)
    @staticmethod
    def event(entry,action,**details):entry.setdefault('attempt_history',[]).append({'at':env.now(),'action':action,**details})
    def settings(self):
        try:
            connection=config(self.workspace);return {'configured':connection is not None,'profile_reference':profile_reference(connection),'destination':{'company_id':connection['company_id'],'dave_id':connection['dave_id']} if connection else None,'error':None}
        except (ValueError,OSError):return {'configured':False,'profile_reference':None,'destination':None,'error':'Approved profile or connection needs technical attention; pending requests are retained'}
    def snapshot(self):
        with lock(self.workspace):return {**self.settings(),'entries':self.read()['entries']}
    def prepare(self,payload,edit_id=None):
        if not self.workspace.operational:raise ValueError('Confirmed dispatch is available only in an operational local profile')
        with lock(self.workspace):
            state=self.read();payload=deepcopy(payload);env.request_values(payload)
            prior=next((x for x in state['entries'] if x['id']==edit_id),None) if edit_id else None
            if edit_id and (prior is None or prior['status'] not in ('draft','pending') or prior.get('attempts',0)):
                raise ValueError('Only unattempted pending requests can be edited. Reconcile accepted/uncertain tasks first; use an explicit amendment for accepted work')
            if prior and prior.get('request'):
                r=prior['request'];payload.update(parent_request_id=r['id'],parent_request_revision=r['revision'],parent_request_digest=r['sha256'])
            if prior:payload['submission_key']=str(uuid4())
            existing=next((x for x in state['entries'] if x['id']==payload['submission_key']),None)
            if existing:
                if existing['payload']!=payload:raise ValueError('This draft identity already has different contents; reopen it as an explicit revision')
                return existing
            settings=self.settings();entry={'id':payload['submission_key'],'revision':(prior['revision']+1) if prior else 1,'replaces':prior['id'] if prior else None,'payload':payload,'profile_reference':settings['profile_reference'],'destination':settings['destination'],'created_at':env.now(),'status':'draft','attempts':0,'error':settings['error'],'request':None,'task':None}
            entry['confirmation_digest']=env.fingerprint({'payload':payload,'profile_reference':entry['profile_reference'],'destination':entry['destination'],'revision':entry['revision']})
            entry['updated_at']=entry['created_at'];state['entries'].append(entry);self.write(state);return entry
    def confirm(self,identity,digest):
        with lock(self.workspace):
            state=self.read();entry=self.entry(state,identity)
            if entry['confirmation_digest']!=digest:raise ValueError('Review the exact countries, profile reference and limits before confirming')
            if entry['status'] in ('cancelled','superseded'):raise ValueError('This request was cancelled or replaced; it cannot be dispatched')
            if entry['status']=='draft':
                # Commit immutable request bytes and private export BEFORE any HTTP call.
                saved=self.workspace.research.submit(entry['payload'])['request'];self.workspace.research.export(saved['request_id'])
                entry['request']={'id':saved['request_id'],'revision':saved['revision'],'sha256':saved['digest']}
                entry['dispatch_key']='grad-compass:'+env.fingerprint({'request':entry['request'],'profile':entry['profile_reference'],'destination':entry.get('destination')})
                entry['status']='pending';entry['confirmed_at']=env.now();entry['updated_at']=entry['confirmed_at']
                self.event(entry,'confirmed',request=entry['request'])
                if entry['replaces']:
                    prior=self.entry(state,entry['replaces']);prior['status']='superseded';prior['replacement']=identity;prior['updated_at']=env.now()
                    self.event(prior,'superseded',replacement=identity)
                self.write(state)
        return self.retry(identity)
    @staticmethod
    def entry(state,identity):
        value=next((x for x in state['entries'] if x['id']==identity),None)
        if value is None:raise ValueError('Pending request not found in this local profile')
        return value
    def cancel(self,identity):
        with lock(self.workspace):
            state=self.read();entry=self.entry(state,identity)
            if entry.get('attempts') or entry['status'] not in ('draft','pending','cancelled'):raise ValueError('This task may already be accepted. Reconcile it first; accepted history cannot be cancelled locally')
            entry['status']='cancelled';entry['updated_at']=env.now();self.event(entry,'cancelled');self.write(state);return entry
    @staticmethod
    def matches(task,marker,binding):
        lines=(task.get('description') or '').splitlines()
        if lines.count(marker)!=1:return False
        candidates=[line[len('Grad-Compass binding '):] for line in lines if line.startswith('Grad-Compass binding ')]
        if len(candidates)!=1:return False
        try:return env.loads(candidates[0])==binding
        except ValueError:return False
    def retry(self,identity):
        with lock(self.workspace):
            state=self.read();entry=self.entry(state,identity)
            if entry['status']=='accepted':return entry
            if entry['status'] not in ('pending','uncertain','dispatching'):raise ValueError('Confirm this pending request before dispatch')
            try:
                connection=config(self.workspace)
                if not connection:raise ValueError('Paperclip is not configured for this profile. Request saved; configure the connection, review and explicitly retry')
                if entry.get('destination')!={'company_id':connection['company_id'],'dave_id':connection['dave_id']}:raise ValueError('The Paperclip destination changed or was unavailable at confirmation. Review an explicit new draft revision')
                reference=profile_reference(connection)
                if reference!=entry['profile_reference']:raise ValueError('The approved profile reference changed or was unavailable at confirmation. Review an explicit new draft revision')
                current=self.workspace.research.request(entry['request']['id'])['request']
                if current['digest']!=entry['request']['sha256']:raise ValueError('Saved request binding changed; preserve history for recovery')
                client=self.client_factory(connection);client.available()
                marker='Grad-Compass dispatch '+entry['dispatch_key']
                binding={'request':entry['request'],'profile':entry['profile_reference'],'destination':entry['destination']}
                binding_line='Grad-Compass binding '+env.compact(binding)
                task=client.reconcile(marker) if entry['attempts'] else None
                if not task:
                    if entry.get('first_attempt_at') and self.clock()-entry['first_attempt_at']>=RETENTION_SECONDS:
                        raise ValueError('Earlier delivery is uncertain beyond Paperclip’s seven-day deduplication window. Reconciliation found no task; no duplicate dispatch will be attempted')
                    export=self.workspace.research.export(current['request_id'])
                    entry['first_attempt_at']=entry.get('first_attempt_at',self.clock());entry['attempts']+=1;entry['status']='dispatching';entry['error']=None;entry['updated_at']=env.now();self.event(entry,'send_attempt',attempt=entry['attempts']);self.write(state)
                    payload={'title':'Grad Compass: '+', '.join(current['countries'])+' · '+current['request_id'],
                        'description':marker+'\n'+binding_line+'\n\n'+export['prompt']+'\n\nExplicitly confirmed app dispatch. Approved profile reference (no content): '+json.dumps(reference,sort_keys=True),
                        'assigneeAgentId':connection['dave_id'],'status':'todo','priority':'medium','idempotencyKey':entry['dispatch_key'],'allowDuplicate':True}
                    task=client.create(payload)
                if task.get('companyId')!=connection['company_id'] or task.get('assigneeAgentId')!=connection['dave_id'] or not self.matches(task,marker,binding):
                    raise ValueError('Paperclip returned a conflicting task binding; no acceptance was recorded')
                env.identifier(task.get('id'))
                entry['task']={k:task.get(k) for k in ('id','identifier','status')};entry['status']='accepted';entry['error']=None;entry['accepted_at']=env.now();entry['updated_at']=entry['accepted_at'];self.event(entry,'task_receipt',task=entry['task']);self.write(state)
            except (ValueError,OSError,TimeoutError) as error:
                # No credential, remote body or URL appears in logs/UI errors.
                entry['status']='uncertain' if entry['attempts'] else 'pending'
                entry['error']=str(error) if isinstance(error,ValueError) else 'Paperclip did not confirm delivery. Your request is saved; explicitly retry to reconcile without duplicates'
                entry['updated_at']=env.now()
                self.event(entry,entry['status'],error=entry['error'])
                self.write(state)
            return entry
