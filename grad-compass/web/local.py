"""Persistent owner-private local workspace, separate from all legacy/sample data."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import threading
from uuid import uuid4

from core.paths import validate_data_directory
from web.server import DemoWorkspace
from web import research_envelopes as env
from web.research import ResearchWorkspace

LOCAL_MARKER = 'grad-compass-local-v1'
RESEARCH_MARKER = 'grad-compass-local-research-v1'


def private_directory(path):
    path=Path(path)
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise ValueError('Local storage cannot use symbolic links')
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.stat().st_uid != os.getuid(): raise ValueError('Local storage must belong to this user')
    path.chmod(0o700)
    return path


def regular(path):
    path=Path(path)
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink!=1)):
        raise ValueError('Local data must use regular unlinked files')
    return path


def atomic_json(path,value):
    regular(path)
    temporary=path.with_name('.'+path.name+'-'+str(uuid4()))
    descriptor=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(descriptor,'wb') as output: output.write((env.compact(value)+'\n').encode('utf-8'))
        os.replace(temporary,path)
    finally:
        if temporary.exists(): temporary.unlink()


class LocalWorkspace(DemoWorkspace):
    operational=True

    def __init__(self,directory,previous=None):
        if any(p.is_symlink() for p in (Path(directory),*Path(directory).parents)):
            raise ValueError('Local storage cannot use symbolic links')
        self.directory=private_directory(validate_data_directory(directory))
        self.database=self.directory/'grad_compass.db'
        self.state_lock=threading.RLock();self._research=None
        regular(self.database)
        if not self.database.exists():
            fd=os.open(self.database,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600);os.close(fd)
            with closing(sqlite3.connect(self.database)) as db,db:
                db.executescript('''CREATE TABLE app_local_guard(marker TEXT NOT NULL);
                    CREATE TABLE local_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                    CREATE TABLE locations(institution_id TEXT NOT NULL,revision TEXT NOT NULL,body TEXT NOT NULL,
                        PRIMARY KEY(institution_id,revision));''')
                db.execute('INSERT INTO app_local_guard VALUES(?)',(LOCAL_MARKER,))
        with closing(self.connect()):pass
        with closing(self.writer()) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS removed_institutions(institution_id TEXT PRIMARY KEY,name TEXT NOT NULL,removed_at TEXT NOT NULL)')
        private_directory(self.directory/'inbox');private_directory(self.directory/'batches')
        if previous: self._preserve_previous(Path(previous))

    def connect(self):
        for suffix in ('','-wal','-shm','-journal'):regular(Path(str(self.database)+suffix))
        if not self.database.is_file():raise ValueError('Local workspace database is missing')
        db=sqlite3.connect(self.database.as_uri()+'?mode=ro',uri=True)
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        try:
            if [r[0] for r in db.execute('SELECT marker FROM app_local_guard')]!=[LOCAL_MARKER]:raise ValueError()
        except (sqlite3.Error,ValueError):
            db.close();raise ValueError('A marked operational local workspace is required') from None
        return db

    def writer(self):
        with closing(self.connect()):pass
        db=sqlite3.connect(self.database.as_uri()+'?mode=rw',uri=True)
        db.row_factory=sqlite3.Row
        return db

    @property
    def research(self):
        with self.state_lock:
            if self._research is None:self._research=LocalResearch(self)
            return self._research

    def _preserve_previous(self,previous):
        with self.state_lock,closing(self.connect()) as db:
            if db.execute("SELECT 1 FROM local_meta WHERE key='previous_preserved'").fetchone():return
        if not (previous/'grad_compass.db').is_file():return
        old=DemoWorkspace(previous)  # Marker/path guards, read-only; never legacy production.
        archive=private_directory(self.directory/'sample-history')
        for name in ('grad_compass.db','research.sqlite'):
            source=regular(previous/name)
            if source.exists():
                target=regular(archive/name)
                if not target.exists():
                    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
                    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(target)) as dst:src.backup(dst)
        with self.research.lock,closing(self.research.connect()) as target,target:
            if (archive/'research.sqlite').is_file():
                with closing(sqlite3.connect((archive/'research.sqlite').as_uri()+'?mode=ro',uri=True)) as src:
                    src.row_factory=sqlite3.Row
                    if src.execute('SELECT marker FROM app_research_guard').fetchone()[0]!='grad-compass-research-demo-v1':raise ValueError('Invalid sample archive')
                    target.executemany('INSERT OR IGNORE INTO country_personal(code,watched,note) VALUES(?,?,?)',
                                      [(r['code'],r['watched'],r['note']) for r in src.execute('SELECT * FROM country_personal')])
                    if src.execute("SELECT 1 FROM sqlite_master WHERE name='research_preferences'").fetchone():
                        row=src.execute('SELECT body FROM research_preferences WHERE id=1').fetchone()
                        if row:target.execute('INSERT OR IGNORE INTO research_preferences VALUES(1,?)',(row[0],))
        for name in ('country-decisions.json','display-preferences.json'):
            source=regular(previous/name)
            if source.is_file():
                value=env.loads(source.read_bytes());atomic_json(archive/name,value)
                if not (self.directory/name).exists():atomic_json(self.directory/name,value)
        with closing(self.writer()) as db,db:db.execute("INSERT INTO local_meta VALUES('previous_preserved',?)",(env.now(),))

    def archived_requests(self,identity=None):
        path=regular(self.directory/'sample-history/research.sqlite')
        if not path.is_file():return {'requests':[]} if identity is None else None
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='research_requests'").fetchone():return {'requests':[]}
            if identity is None:
                values=[env.saved(r['body']) for r in db.execute('SELECT body FROM research_requests ORDER BY rowid DESC')]
                return {'requests':[{**v,'state':'sample_archive','legacy':True} for v in values]}
            env.identifier(identity)
            row=db.execute('SELECT body FROM research_requests WHERE id=?',(identity,)).fetchone()
            if not row:return None
            request={**env.saved(row['body']),'legacy':True}
            results=[{'envelope':env.saved(r['body']),'changes':[]} for r in db.execute('SELECT body FROM research_results WHERE request_id=? ORDER BY revision',(identity,))]
            feedback=[env.saved(r['body']) for r in db.execute('SELECT body FROM research_feedback WHERE request_id=?',(identity,))]
            ack=db.execute('SELECT body FROM research_acks WHERE request_id=?',(identity,)).fetchone()
            return {'request':request,'results':results,'feedback':feedback,'acknowledgement':env.saved(ack['body']) if ack else None,'archive':True}

    def records(self):
        institutions={};programs={};batches={}
        with closing(self.research.connect()) as db:
            for row in db.execute('SELECT body FROM research_results ORDER BY rowid'):
                result=self.research._body(row)
                for association in result.get('public_associations',[]):
                    key=(association['batch_id'],association['manifest_sha256'])
                    if key not in batches:batches[key]=self.research.public_batch(*key)
                    batch=batches[key]
                    for record in batch['institutions']:
                        if record['id']==association['institution_id']:institutions[record['id']]={'record':record,'result':result}
                    if association.get('program_id'):
                        for record in batch['programs']:
                            if record['id']==association['program_id']:programs[record['id']]={'record':record,'result':result}
        return institutions,programs

    def location(self,identity):
        with closing(self.connect()) as db:row=db.execute('SELECT body FROM locations WHERE institution_id=? ORDER BY rowid DESC LIMIT 1',(identity,)).fetchone()
        return env.loads(row[0]) if row else {'status':'unresolved','latitude':None,'longitude':None,'uncertainty':'No verified campus location supplied.'}

    def save_location(self,identity,value):
        env.identifier(identity)
        if value.get('status') not in ('verified','unresolved'):raise ValueError('State the location verification status')
        env.utc(value.get('observed_at'))
        if not value.get('campus') or not value.get('uncertainty'):raise ValueError('Keep campus identity and location uncertainty')
        if value['status']=='verified':
            if any(type(value.get(k)) not in (int,float) or not math.isfinite(value[k]) or abs(value[k])>limit for k,limit in (('latitude',90),('longitude',180))):raise ValueError('Use verified campus coordinates')
            if not value.get('source_url','').startswith('https://') or not value.get('locator'):raise ValueError('Keep official location provenance')
        else:value={**value,'latitude':None,'longitude':None}
        revision=env.fingerprint(value)
        with self.state_lock,closing(self.writer()) as db,db:db.execute('INSERT OR IGNORE INTO locations VALUES(?,?,?)',(identity,revision,env.compact(value)))
        return value

    @staticmethod
    def private_record(result,kind,identity):
        candidate=result.get('candidate',{})
        bindings=candidate.get('public_record_bindings',[])
        key=next((r['key'] for r in bindings if r['kind']==kind and r['id']==identity),None)
        return next((r for r in candidate.get('institutions' if kind=='institution' else 'programs',[]) if r['key']==key),{})

    def overview(self):
        institutions,_=self.records();values=[]
        removed={row['id'] for row in self.removed_universities()}
        for identity,item in institutions.items():
            if identity in removed:continue
            r=item['record'];location=self.location(identity);private=self.private_record(item['result'],'institution',identity)
            values.append({'id':'local-'+identity,'name':r['name'],'country_code':r['country_code'],'city':r.get('city'),
                'latitude':location.get('latitude'),'longitude':location.get('longitude'),'location':location,'deadline':None,'status':'Researching',
                'portal_url':r['official_url'],'faculty_count':0,'synthetic':False,
                'research':{'external_id':identity,'revision':r['record_revision'],'review':r['review']['state'],'storage':'received',
                            'facts':r['facts'],'private':private,'human_approval':private.get('human_approval','unknown')}})
        return {'synthetic':False,'operational':True,'universities':sorted(values,key=lambda r:r['name'])}

    def removed_universities(self):
        with closing(self.connect()) as db:
            return [dict(row) for row in db.execute('SELECT institution_id AS id,name,removed_at FROM removed_institutions ORDER BY name')]

    def remove_university(self,identity):
        env.identifier(identity)
        with self.state_lock,self.research.lock:
            if any(row['id']==identity for row in self.removed_universities()):return {'changed':False}
            item=next((u for u in self.overview()['universities'] if u['research']['external_id']==identity),None)
            if item is None:raise ValueError('Choose a university in this profile')
            backup=self.backup()
            with closing(self.writer()) as db,db:
                db.execute('INSERT INTO removed_institutions VALUES(?,?,?)',(identity,item['name'],env.now()))
            return {'changed':True,'backup':backup['name']}

    def restore_university(self,identity):
        env.identifier(identity)
        with self.state_lock,closing(self.writer()) as db,db:
            changed=db.execute('DELETE FROM removed_institutions WHERE institution_id=?',(identity,)).rowcount>0
        return {'changed':changed}

    def university(self,identity):
        institution=next((u for u in self.overview()['universities'] if u['id']==identity),None)
        if not institution:return None
        _,programs=self.records();values=[]
        for pid,item in programs.items():
            r=item['record']
            if r['institution_id']!=institution['research']['external_id']:continue
            values.append({'id':'local-program-'+pid,'external_id':pid,'name':r['name'],'degree_level':r['degree_level'],
                'official_url':r['official_url'],'requirements':r.get('requirements',[]),'revision':r['record_revision'],
                'review':r['review']['state'],'storage':'received','private':self.private_record(item['result'],'program',pid),
                'research_results':self.research.links('program',pid)})
        return {'university':institution,'professors':[],'tasks':[],'programs':values,
                'research_results':self.research.links('institution',institution['research']['external_id'])}

    def backup(self):
        with self.state_lock,self.research.lock:
            root=private_directory(self.directory/'backups')
            target=private_directory(root/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
            for source in (self.database,self.research.database):
                dest=target/source.name
                fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
                with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src,closing(sqlite3.connect(dest)) as dst:src.backup(dst)
            for name in ('country-decisions.json','display-preferences.json','panel-widths.json','report-annotations.json','report-reading.json','research-selection.json','export-preferences.json','dispatch-outbox.json','report-delivery-order.json','paperclip-connection.local.json'):
                source=regular(self.directory/name)
                if source.is_file():atomic_json(target/name,env.loads(source.read_bytes()))
            for name in ('research-handoff','inbox','batches','received-batches','sample-history','reports','report-cache','editorial-cache','report-projections','report-receipts'):
                source=self.directory/name
                if source.exists():
                    for path in source.rglob('*'):
                        if path.is_symlink():raise ValueError('Backup storage cannot use links')
                        if path.is_file():
                            regular(path);relative=path.relative_to(self.directory);dest=target/relative
                            private_directory(dest.parent);shutil.copyfile(path,dest);dest.chmod(0o600)
            files={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*') if p.is_file()}
            atomic_json(target/'backup.json',{'schema_version':'local-backup-1','created_at':env.now(),'sha256':files})
            return {'name':target.name,'files':len(files),'message':'Private local backup saved.'}


class LocalResearch(ResearchWorkspace):
    synthetic=False
    marker=RESEARCH_MARKER

    def submit(self,payload):
        if not isinstance(payload,dict) or "bounds" not in payload:raise ValueError('Choose explicit institution and program limits')
        return super().submit(payload)

    def demo_response(self,*args,**kwargs):raise ValueError('The local workspace receives real producer handoffs; samples remain in the archive')

    def public_batch(self,identity,digest=None):
        from core.exchange_importer import _read_batch
        env.identifier(identity)
        root=self.directory/'batches'/('batch-'+identity)
        if digest is not None:
            env.digest_reference(digest)
            retained=self.directory/'received-batches'/digest/('batch-'+identity)
            if retained.exists():root=retained
        if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('Batch storage cannot use links')
        manifest,institutions,programs,actual=_read_batch(root)
        if manifest['batch_id']!=identity or (digest is not None and actual!=digest):raise ValueError('The batch no longer matches its exact receipt')
        if identity==env.BATCH_ID:raise ValueError('The invented sample batch belongs in the separate sample workspace')
        return {'manifest':manifest,'institutions':institutions,'programs':programs,'digest':actual}

    def receive(self,transport,before_record=None):
        # Keep received public bytes independently of the mutable handoff folder.
        # The existing importer remains the sole exchange 1.0.0 structural validator.
        with self.lock:
            value=self._validate_response(transport)
            for association in value.get('public_associations',[]):
                identity=association['batch_id'];digest=association['manifest_sha256']
                parent=private_directory(self.directory/'received-batches'/digest)
                target=parent/('batch-'+identity)
                if not target.exists():
                    source=self.directory/'batches'/target.name
                    temporary=private_directory(parent/('.receive-'+str(uuid4())))
                    try:
                        for name in ('manifest.json','institutions.jsonl','programs.jsonl'):
                            shutil.copyfile(regular(source/name),temporary/name);(temporary/name).chmod(0o600)
                        from core.exchange_importer import _read_batch
                        if _read_batch(temporary)[3]!=digest:raise ValueError('Batch bytes changed while receiving')
                        os.rename(temporary,target)
                    finally:
                        if temporary.exists():shutil.rmtree(temporary)
                self.public_batch(identity,digest)
            return super().receive(transport,before_record=before_record)

    def _validate_response(self,transport):
        from web.local_contract import validate_response
        value=env.verify(transport,synthetic=False,max_bytes=4_000_000)
        current=self.request(value.get('request_id'));request=current['request']
        validate_response(value,request,self.public_batch)
        if value['envelope_kind']=='result':
            previous=[r['envelope'] for r in current['results']]
            if any(r['result_id']!=value['result_id'] for r in previous):raise ValueError('A request has one result revision sequence; prepare a refresh for a new result')
            if value['revision']>1:
                prior=next((r for r in previous if r['revision']==value['previous_result_revision'] and r['digest']==value['previous_result_digest']),None)
                if prior is None:raise ValueError('Receive the exact earlier result revision/digest first')
                if prior['completion']=='complete' and not self._allow_completed_revision(value,prior):
                    raise ValueError('A complete result requires a new refresh request outside operational country conditions')
            for old in previous:
                for finding in value['findings']:
                    same=next((f for f in old['findings'] if f['finding_id']==finding['finding_id'] and f['finding_revision']==finding['finding_revision']),None)
                    if same is not None and same!=finding:raise ValueError('A finding revision cannot be reused with changed contents')
            institutions=set();programs=set()
            for result in [*previous,value]:
                for association in result['public_associations']:
                    institutions.add(association['institution_id'])
                    if association.get('program_id'):programs.add(association['program_id'])
            if len(institutions)>request['bounds']['institutions'] or len(programs)>request['bounds']['programs']:
                raise ValueError('Cumulative returned records exceed this request’s limits')
        return value

    def _allow_completed_revision(self,value,prior):
        current=self.request(value['request_id']);request=current['request']
        if request['scope']!='country_conditions' or value['completion']!='complete':return False
        old={f['finding_id']:f for f in prior['findings']}
        for finding in value['findings']:
            previous=old.get(finding['finding_id'])
            if previous is not None and previous!=finding:
                older=[f for row in current['results'] if row['envelope']['revision']<value['revision']
                       for f in row['envelope']['findings'] if f['finding_id']==finding['finding_id']]
                if any(f['finding_revision']==finding['finding_revision'] or f['record_revision']==finding['record_revision'] for f in older):
                    raise ValueError('Changed completed country findings need fresh finding and country record revisions')
        return True

    def preview_response(self,transport_json):
        if not isinstance(transport_json,str) or len(transport_json.encode('utf-8'))>8_000_000:raise ValueError('Choose a bounded producer transport file')
        return self._validate_response(env.loads(transport_json))

    def latest_country(self,code):
        latest=None;history=[]
        with closing(self.connect()) as db:
            for row in db.execute('SELECT body FROM research_results ORDER BY rowid DESC'):
                result=self._body(row)
                findings=[f for f in result['findings'] if f['kind']=='country' and f['country_code']==code]
                if not findings:continue
                origin={'request_id':result['request_id'],'result_id':result['result_id'],'revision':result['revision'],'digest':result['digest'],
                        'finding_id':findings[0]['finding_id'],'finding_revision':findings[0]['finding_revision']}
                history.append(origin)
                if latest is None:
                    rows=[{**f,'origin':{**origin,'finding_id':f['finding_id'],'finding_revision':f['finding_revision']}} for f in findings]
                    sources=[];uncertainties=[];seen=set()
                    for finding in findings:
                        for source in finding['sources']:
                            key=env.compact(source)
                            if key not in seen:seen.add(key);sources.append(source)
                        for caveat in finding['uncertainties']:
                            if caveat not in uncertainties:uncertainties.append(caveat)
                    states={f['review_status'] for f in findings}
                    latest={**findings[0],'findings':rows,'origin':origin,'sources':sources,'uncertainties':uncertainties,
                            'summary':f'{len(findings)} research findings received. Inspect the field-specific evidence, caveats and actual review states below.',
                            'review_status':next(iter(states)) if len(states)==1 else 'mixed',
                            'funding_routes':None,'costs':None,'work_rules':None}
        return {**latest,'history':history} if latest else None

    def links(self,kind,external_id):
        values=[]
        with closing(self.connect()) as db:
            for row in db.execute('SELECT body FROM research_results ORDER BY rowid DESC'):
                result=self._body(row)
                for finding in result['findings']:
                    if finding['kind']==kind and finding.get('external_id')==external_id:
                        values.append({'request_id':result['request_id'],'result_id':result['result_id'],'revision':result['revision'],
                                       'digest':result['digest'],'finding_id':finding['finding_id'],'finding_revision':finding['finding_revision']})
        return values

    def scan_inbox(self,paths=None,before_record=None):
        inbox=private_directory(self.directory/'inbox');packets=[];outcomes=[]
        for path in sorted(inbox.glob('*.json') if paths is None else paths):
            try:
                regular(path)
                if path.stat().st_size>8_000_000:raise ValueError('Producer file is too large')
                before=path.stat();raw=path.read_bytes();after=path.stat()
                if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):continue
                packet=env.loads(raw)
                if not isinstance(packet,dict) or set(packet)!={'body','sha256'}:raise ValueError('Expected a finalized {body, sha256} response transport')
                value=env.verify(packet,synthetic=False,max_bytes=4_000_000)
                packets.append((value,packet,path.name))
            except (ValueError,OSError) as error:outcomes.append({'file':path.name,'error':str(error)})
        packets.sort(key=lambda r:(0 if r[0].get('envelope_kind')=='acknowledgement' else 1,r[0].get('revision',0),r[0].get('request_id','')))
        for value,packet,name in packets:
            try:
                result=self.receive(packet,before_record=before_record);outcomes.append({'file':name,'changed':result['changed'],'kind':value['envelope_kind'],'request_id':value['request_id']})
            except (ValueError,OSError,sqlite3.Error) as error:outcomes.append({'file':name,'error':str(error)})
        return {'outcomes':outcomes,'received':sum(bool(v.get('changed')) for v in outcomes),'errors':sum('error' in v for v in outcomes)}


def create_local_server(workspace,port=0,profiles=None,clipboard=None,desktop_exports=None):
    from web.inbox import InboxServer
    import secrets
    from web.server import handler_for
    workspace.backup()
    return InboxServer(('127.0.0.1',port),handler_for(workspace,session_token=secrets.token_urlsafe(24),profiles=profiles,clipboard=clipboard,desktop_exports=desktop_exports),workspace,profiles)
