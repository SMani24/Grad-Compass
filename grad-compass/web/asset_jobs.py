"""Bounded public-photo retrieval for an already accepted local request.

The desktop owns network I/O; agents retain provenance, review and release.
Jobs and originals stay private. No request, task or agent is created here.
"""
from contextlib import contextmanager
from datetime import datetime,timezone
import fcntl
import hashlib
import io
import ipaddress
import os
from pathlib import Path
import socket
import time
from urllib.parse import urlsplit
import urllib.error
import urllib.request
from uuid import uuid5,NAMESPACE_URL

from PIL import Image
from web import research_envelopes as env
from web.local import private_directory,regular
from web.dispatch import Dispatch,Paperclip,config,durable

VERSION='grad-compass-asset-job-1'
ORIGINS={'images.pexels.com','upload.wikimedia.org'}
MAX_BYTES=12_000_000
MAX_PIXELS=40_000_000


def public_url(value,download=False):
    if not isinstance(value,str) or len(value)>2048 or any(ord(c)<33 for c in value):raise ValueError('Use a public HTTPS asset reference')
    try:
        p=urlsplit(value)
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443) or p.fragment:raise ValueError()
        if download and p.hostname not in ORIGINS:raise ValueError()
        if not download and (p.hostname in ('localhost','127.0.0.1','::1') or '.' not in p.hostname):raise ValueError()
        try:address=ipaddress.ip_address(p.hostname)
        except ValueError:address=None
        if address and not address.is_global:raise ValueError()
    except ValueError:raise ValueError('Use a permitted public HTTPS image origin; no credentials or alternate ports') from None
    return value


def identity(request,country,url):
    return str(uuid5(NAMESPACE_URL,'grad-compass-asset:'+env.compact([request,country,url])))


def validate(workspace,packet):
    if not isinstance(packet,dict) or set(packet)!={'body','sha256'} or not isinstance(packet['body'],str):raise ValueError('Asset jobs need exact-byte transport')
    raw=packet['body'].encode('utf-8');env.digest_reference(packet['sha256'])
    if len(raw)>20000 or hashlib.sha256(raw).hexdigest()!=packet['sha256']:raise ValueError('Asset job digest mismatch')
    job=env.loads(raw)
    if not isinstance(job,dict) or set(job)!={'schema_version','job_id','request','country_code','task_id','assignee_agent_id','asset','created_at'} or job['schema_version']!=VERSION:raise ValueError('Use the versioned asset job fields')
    env.identifier(job['job_id']);env.identifier(job['task_id']);env.identifier(job['assignee_agent_id']);env.utc(job['created_at'])
    request=job['request']
    if not isinstance(request,dict) or set(request)!={'id','revision','sha256'}:raise ValueError('Asset job needs its exact saved request binding')
    env.identifier(request['id']);env.digest_reference(request['sha256'])
    if type(request['revision']) is not int:raise ValueError('Asset request revision must be an integer')
    saved=workspace.research.request(request['id'])['request']
    if (request['revision'],request['sha256'])!=(saved['revision'],saved['digest']) or job['country_code'] not in saved['countries']:raise ValueError('Asset is outside the saved request revision or countries')
    if saved['scope'] not in ('country_conditions','refresh'):raise ValueError('This request does not authorize country-report assets')
    entries=Dispatch(workspace).read()['entries']
    entry=next((e for e in entries if e.get('request')==request and e['status']=='accepted'),None)
    if not entry:raise ValueError('Asset retrieval requires an already accepted app request')
    a=job['asset']
    if not isinstance(a,dict) or set(a)!={'original_url','source_url','license_url','creator','license','caption','alt'}:raise ValueError('Supply original, source, license, creator, caption and alt fields')
    for k in ('creator','license','caption','alt'):
        if not isinstance(a[k],str) or not a[k].strip() or len(a[k])>1000:raise ValueError('Supply bounded nonempty asset descriptions')
    for k in ('original_url','source_url','license_url'):public_url(a[k],download=k=='original_url')
    if job['job_id']!=identity(request,job['country_code'],a['original_url']):raise ValueError('Asset job identity must be derived from its exact request, country and URL')
    return job,entry


def enqueue(workspace,request,country,task_id,asset,assignee_id):
    job={'schema_version':VERSION,'job_id':identity(request,country,asset['original_url']),
         'request':request,'country_code':country,'task_id':task_id,'assignee_agent_id':assignee_id,'asset':asset,'created_at':env.now()}
    packet=env.packet(job);validate(workspace,packet)
    folder=private_directory(workspace.directory/'asset-jobs'/'requests');path=regular(folder/(job['job_id']+'.json'))
    if path.exists():
        prior=env.loads(path.read_bytes());old,_=validate(workspace,prior)
        if {k:v for k,v in old.items() if k!='created_at'}!={k:v for k,v in job.items() if k!='created_at'}:raise ValueError('Existing immutable asset job has different content')
    else:durable(path,packet)
    return {'job_id':job['job_id'],'job_path':str(path),'state_path':str(path.parent.parent/'jobs'/job['job_id']/'state.json')}


def image_info(raw):
    if len(raw)>MAX_BYTES:raise ValueError('Photograph exceeds the 12 MB limit')
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height>MAX_PIXELS:raise ValueError('Use a bounded JPEG, PNG or WebP photograph')
            image.load()
            return {'format':image.format,'width':image.width,'height':image.height}
    except Image.DecompressionBombError:raise ValueError('Photograph dimensions exceed the safe decode limit') from None


class RetrievalFailure(Exception):
    def __init__(self,code,message):super().__init__(message);self.code=code


def download(url):
    public_url(url,download=True)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    req=urllib.request.Request(url,headers={'User-Agent':'Grad-Compass/1.0 (request-bound licensed country photograph)'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:
            if response.status!=200:raise RetrievalFailure('http_status','Image host did not return a complete original')
            size=response.headers.get('Content-Length')
            if size and int(size)>MAX_BYTES:raise RetrievalFailure('size_limit','Photograph exceeds the 12 MB limit')
            started=time.monotonic();chunks=[];total=0
            while True:
                chunk=response.read(min(65536,MAX_BYTES+1-total))
                if not chunk:break
                total+=len(chunk);chunks.append(chunk)
                if total>MAX_BYTES:raise RetrievalFailure('size_limit','Photograph exceeds the 12 MB limit')
                if time.monotonic()-started>30:raise RetrievalFailure('timeout','Image retrieval exceeded its bounded time')
        return b''.join(chunks)
    except urllib.error.HTTPError as error:
        code='rate_limited' if error.code==429 else 'access_denied' if error.code in (401,403) else 'http_'+str(error.code)
        retry=error.headers.get('Retry-After')
        raise RetrievalFailure(code,'Image host returned HTTP '+str(error.code)+('. Retry-After: '+retry[:100] if retry else '')+'. No denied-source retry was made.') from None
    except (urllib.error.URLError,TimeoutError,socket.timeout,OSError):
        raise RetrievalFailure('connection_unavailable','The app could not retrieve the public image. The existing task needs a reachable permitted source.') from None


class AssetJobs:
    def __init__(self,workspace,client_factory=Paperclip,fetch=download,clock=time.time,quiet_seconds=1):
        self.workspace=workspace;self.client_factory=client_factory;self.fetch=fetch;self.clock=clock;self.quiet_seconds=quiet_seconds
        self.root=private_directory(workspace.directory/'asset-jobs')

    def client(self,job,entry):
        connection=config(self.workspace)
        if not connection or entry['destination']!={'company_id':connection['company_id'],'dave_id':connection['dave_id']}:raise ValueError('Asset task connection does not match the accepted request')
        client=self.client_factory(connection);root=client.call('/issues/'+entry['task']['id'])
        binding={'request':entry['request'],'profile':entry['profile_reference'],'destination':entry['destination']}
        if root.get('companyId')!=connection['company_id'] or root.get('assigneeAgentId')!=connection['dave_id'] or not Dispatch.matches(root,'Grad-Compass dispatch '+entry['dispatch_key'],binding):raise ValueError('Asset parent does not match the accepted request')
        task=client.call('/issues/'+job['task_id'])
        if task.get('id')!=job['task_id'] or task.get('companyId')!=connection['company_id'] or task.get('parentId')!=root['id'] or task.get('assigneeAgentId')!=job['assignee_agent_id']:raise ValueError('Asset task must match the exact assigned owner and direct parent of this accepted request')
        return client,task

    @contextmanager
    def lock(self):
        fd=os.open(regular(self.root/'.worker.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'r+') as stream:
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:yield False;return
            yield True

    def check(self):
        with self.lock() as acquired:
            if not acquired:return
            requests=private_directory(self.root/'requests')
            # One retrieval per tick bounds work and avoids monopolizing polling.
            for path in sorted(requests.glob('*.json')):
                if path.name.startswith('.') or self.clock()-path.lstat().st_mtime<self.quiet_seconds:continue
                job=None
                try:
                    if path.stat().st_size>25000:raise ValueError('Asset job exceeds its limit')
                    packet=env.loads(regular(path).read_bytes());job,entry=validate(self.workspace,packet)
                    if path.name!=job['job_id']+'.json':raise ValueError('Asset job filename identity mismatch')
                    folder=private_directory(self.root/'jobs'/job['job_id']);state_path=regular(folder/'state.json')
                    state=env.loads(state_path.read_bytes()) if state_path.exists() else {'job_id':job['job_id'],'request_id':job['request']['id'],'country_code':job['country_code'],'input_sha256':packet['sha256'],'status':'queued','attempts':0,'history':[]}
                    if state['input_sha256']!=packet['sha256']:raise ValueError('Finalized asset job changed; original outcome is preserved')
                    if state['status'] in ('downloaded','failed'):
                        self.notify(job,entry,state,folder);continue
                    if self.clock()<state.get('retry_at',0):continue
                    # A crashed HTTP GET can be retried at most once. A completed
                    # local original is recovered before considering another GET.
                    original=regular(folder/'original')
                    try:client,task=self.client(job,entry)
                    except OSError:
                        state.update(status='queued',retry_at=self.clock()+60,waiting='The bound Paperclip task cannot currently be validated; no retrieval or new work started.')
                        durable(state_path,state);continue
                    if task['status'] in ('done','cancelled'):
                        raise ValueError('The asset task is closed; do not start new retrieval')
                    diagnostic=self.root/'invalid'/(hashlib.sha256(path.name.encode()).hexdigest()+'.json')
                    if diagnostic.exists():
                        previous=env.loads(regular(diagnostic).read_bytes())
                        if not previous.get('resolved_at'):
                            durable(diagnostic,{**previous,'resolved_at':env.now(),'resolution':'The same job and current remote binding now validate; original diagnostic retained.'})
                    attempted=False
                    try:
                        if original.exists():raw=original.read_bytes()
                        else:
                            siblings=[p for p in requests.glob('*.json') if not p.name.startswith('.')]
                            count=0
                            for sibling in siblings:
                                try:
                                    value=env.loads(env.loads(regular(sibling).read_bytes())['body'])
                                    if value.get('request')==job['request'] and value.get('country_code')==job['country_code']:count+=1
                                except (ValueError,OSError,KeyError,TypeError):continue
                            if count>3:raise RetrievalFailure('scope_limit','At most three original candidates are allowed per country/request; Dave must reconcile the existing attempts.')
                            if state['attempts']>=2:raise RetrievalFailure('interrupted','Retrieval was interrupted twice. Existing attempt history is preserved; Dave must reconcile it.')
                            state.update(status='fetching',attempts=state['attempts']+1,started_at=env.now());state.pop('waiting',None);state.pop('retry_at',None)
                            state['history'].append({'at':env.now(),'event':'retrieval_started','attempt':state['attempts']});durable(state_path,state);attempted=True
                            raw=self.fetch(job['asset']['original_url']);info=image_info(raw)
                            temporary=regular(folder/'.original.partial')
                            with temporary.open('wb') as output:os.chmod(temporary,0o600);output.write(raw);output.flush();os.fsync(output.fileno())
                            os.replace(temporary,original)
                        info=image_info(raw)
                        receipt={'schema_version':VERSION,'job_id':job['job_id'],'input_sha256':packet['sha256'],'request':job['request'],'country_code':job['country_code'],
                                 'status':'downloaded','original_path':str(original.relative_to(self.workspace.directory)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'image':info,'asset':job['asset'],
                                 'retrieved_at':env.now(),'provenance_review':'pending Ali verification','independent_review':'pending','release':'not_granted'}
                        receipt_path=regular(folder/'receipt.json')
                        if receipt_path.exists():
                            receipt=env.loads(receipt_path.read_bytes())
                            if receipt['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('Recovered original no longer matches its receipt')
                        else:durable(receipt_path,receipt)
                        state.update(status='downloaded',receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),receipt_path=str(receipt_path.relative_to(self.workspace.directory)));state.pop('error',None)
                    except (RetrievalFailure,ValueError,OSError) as error:
                        state.update(status='failed',error={'code':getattr(error,'code','invalid_image'),'message':str(error)[:500],
                                     'owner':'Dave / Ali','action':'Reuse existing text/reviews. Dave routes a different permitted licensed candidate or records the exact remaining capability; do not resubmit research or bypass source restrictions.'})
                    state['history'].append({'at':env.now(),'event':state['status']});durable(state_path,state)
                    self.notify(job,entry,state,folder)
                    if attempted:return
                except (ValueError,OSError,KeyError,TypeError) as error:
                    diagnostic=private_directory(self.root/'invalid')
                    name=hashlib.sha256(path.name.encode()).hexdigest()+'.json'
                    value={'file':path.name,'error':str(error)[:500],'request_id':job['request']['id'] if job else None,'country_code':job['country_code'] if job else None}
                    target=regular(diagnostic/name)
                    if not target.exists() or env.loads(target.read_bytes())!=value:durable(target,value)

    def notify(self,job,entry,state,folder):
        path=regular(folder/'event.json');event=env.loads(path.read_bytes()) if path.exists() else {}
        if event.get('status') in ('delivered','task_closed') or self.clock()<event.get('retry_at',0):return
        marker='Grad-Compass asset outcome '+job['job_id']+' '+state['status']
        try:
            if state['status']=='downloaded':
                receipt_path=regular(folder/'receipt.json');raw=receipt_path.read_bytes();receipt=env.loads(raw)
                original=regular(folder/'original');image=original.read_bytes()
                if (hashlib.sha256(raw).hexdigest()!=state['receipt_sha256'] or receipt.get('job_id')!=job['job_id']
                    or receipt.get('input_sha256')!=state['input_sha256'] or receipt.get('request')!=job['request']
                    or receipt.get('asset')!=job['asset'] or receipt.get('country_code')!=job['country_code']
                    or receipt.get('original_path')!=str(original.relative_to(self.workspace.directory))
                    or receipt.get('sha256')!=hashlib.sha256(image).hexdigest() or receipt.get('bytes')!=len(image)):
                    raise ValueError('Saved asset bytes or receipt binding changed; no completion event was sent')
            client,task=self.client(job,entry)
            if task['status'] in ('done','cancelled'):durable(path,{'status':'task_closed','at':env.now()});return
            comments=client.call('/issues/'+job['task_id']+'/comments')
            if not isinstance(comments,list):raise ValueError('Unsupported asset event readback')
            matches=[c for c in comments if marker in (c.get('body') or '').splitlines()]
            if not matches:
                if state['status']=='downloaded':
                    detail='Original retrieved by the normal app. Exact private receipt '+str((self.workspace.directory/state['receipt_path']).absolute())+' SHA256 '+state['receipt_sha256']+'. Resolve receipt original_path relative to this request profile. Ali verifies the supplied source/license/identification/caption/alt, Alex reviews exact bytes, Marry validates and delivers after Dave release. Retrieval is not factual/human approval or release. Reuse completed text; no repeat download.'
                else:detail='Bounded photo retrieval failed: '+state['error']['message']+' '+state['error']['action']
                value={'body':marker+'\n'+detail,'clientRequestId':str(uuid5(NAMESPACE_URL,marker)),'resume':False,'reopen':False,'interrupt':False}
                # The same accepted task receives an input event, never a new
                # request/agent/issue or an execution retry endpoint.
                client.call('/issues/'+job['task_id']+'/comments',value)
                comments=client.call('/issues/'+job['task_id']+'/comments')
                matches=[c for c in comments if marker in (c.get('body') or '').splitlines()]
                if not matches:raise ValueError('Asset outcome awaits saved event readback')
            durable(path,{'status':'delivered','comment_id':matches[0]['id'],'at':env.now()})
        except (ValueError,OSError,KeyError,TypeError) as error:
            message=str(error) if isinstance(error,ValueError) else 'Original outcome is saved. Paperclip notification will reconcile on reconnect; no new download or research is started.'
            durable(path,{'status':'pending','retry_at':self.clock()+60,'message':message,'error_kind':'validation' if isinstance(error,ValueError) else 'connection'})


def summaries(workspace):
    root=workspace.directory/'asset-jobs';rows=[]
    if not root.exists():return rows
    for p in (root/'jobs').glob('*/state.json'):
        try:
            state=env.loads(regular(p).read_bytes());event_path=regular(p.parent/'event.json');event=env.loads(event_path.read_bytes()) if event_path.exists() else {}
            rows.append({k:state.get(k) for k in ('job_id','request_id','country_code','status','error','waiting','receipt_path','attempts') }|{'event_status':event.get('status'),'event_message':event.get('message'),'event_error_kind':event.get('error_kind')})
        except (ValueError,OSError,TypeError):continue
    for p in (root/'invalid').glob('*.json'):
        try:
            error=env.loads(regular(p).read_bytes())
            if error.get('resolved_at'):continue
            rows.append({'request_id':error.get('request_id'),'country_code':error.get('country_code'),'status':'failed','error':{'code':'invalid_job','message':error['error'],'action':'Dave / Marry must correct this exact asset job binding. No download or new research was started.'},'file':error['file']})
        except (ValueError,OSError,KeyError,TypeError):continue
    return rows
