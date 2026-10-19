"""Owner-local workspaces, with isolated stores and recoverable explicit reset."""
from contextlib import closing,contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import secrets
import threading
from uuid import uuid4

from core.paths import validate_data_directory
from web import research_envelopes as env
from web.local import LocalWorkspace,atomic_json,private_directory,regular


class LocalProfiles:
    def __init__(self,initial_directory,previous=None):
        path=Path(initial_directory)
        if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Profiles cannot use linked storage')
        self.initial=validate_data_directory(path)
        self.directory=private_directory(self.initial.with_name(self.initial.name+'-profiles'))
        self.registry=regular(self.directory/'profiles.json')
        self.lock=threading.RLock();self.session_token=secrets.token_urlsafe(24)
        self._cache={};self._pending_reset=None
        if not self.registry.exists():
            workspace=LocalWorkspace(self.initial,previous)
            identity=str(uuid4())
            self._state={'schema_version':'local-profiles-1','active_id':identity,'profiles':[
                {'id':identity,'name':'Personal','storage':'initial','created_at':env.now()}],'reset_history':[]}
            atomic_json(self.registry,self._state);self._cache['initial']=workspace
        else:self._state=env.loads(self.registry.read_bytes())
        self._validate_registry()
        self.workspace=self._open(self._active())

    def _validate_registry(self):
        state=self._state
        if not isinstance(state,dict) or state.get('schema_version')!='local-profiles-1':raise ValueError('Invalid local profile registry')
        profiles=state.get('profiles')
        if not isinstance(profiles,list) or not 1<=len(profiles)<=20:raise ValueError('Invalid local profile list')
        ids=set();names=set();stores=set()
        for row in profiles:
            if not isinstance(row,dict):raise ValueError('Invalid local profile')
            env.identifier(row.get('id'));self._name(row.get('name'))
            env.utc(row.get('created_at'))
            storage=row.get('storage')
            if storage!='initial':env.identifier(storage)
            if row['id'] in ids or row['name'].casefold() in names or storage in stores:raise ValueError('Duplicate local profile')
            ids.add(row['id']);names.add(row['name'].casefold());stores.add(storage)
        if state.get('active_id') not in ids:raise ValueError('The active profile is missing')
        if not isinstance(state.get('reset_history'),list):raise ValueError('Invalid recovery history')
        for row in state['reset_history']:
            if not isinstance(row,dict):raise ValueError('Invalid recovery record')
            env.identifier(row.get('profile_id'));self._name(row.get('name'));env.utc(row.get('reset_at'))
            if row.get('storage')!='initial':env.identifier(row.get('storage'))
            backup=row.get('backup')
            if not isinstance(backup,str) or not backup.isascii() or not backup.isalnum():raise ValueError('Invalid recovery backup name')

    def _check_current(self):
        if env.loads(regular(self.registry).read_bytes())!=self._state:
            raise ValueError('Profiles changed in another app window. Close this window and reopen Grad Compass')

    @contextmanager
    def request_context(self):
        # Serialize profile transitions across tabs and separately launched app windows.
        with self.lock:
            path=regular(self.directory/'.profiles.lock')
            descriptor=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            with os.fdopen(descriptor,'r+') as stream:
                fcntl.flock(stream,fcntl.LOCK_EX)
                self._check_current()
                yield

    @staticmethod
    def _name(name):
        if not isinstance(name,str) or not name.strip() or len(name)>60 or any(ord(c)<32 for c in name):raise ValueError('Use a profile name of 1–60 characters')
        return name.strip()

    def _active(self):return next(row for row in self._state['profiles'] if row['id']==self._state['active_id'])

    def _open(self,row):
        key=row['storage']
        if key not in self._cache:
            path=self.initial if key=='initial' else self.directory/key
            if not (path/'grad_compass.db').is_file():raise ValueError('Profile data is missing; restore its backup rather than recreate it')
            self._cache[key]=LocalWorkspace(path)
        return self._cache[key]

    def snapshot(self):
        with self.lock:
            recoveries=[]
            for row in self._state['reset_history']:
                directory=self.initial if row['storage']=='initial' else self.directory/row['storage']
                recoveries.append({'name':row['name'],'reset_at':row['reset_at'],'path':str(directory/'backups'/row['backup'])})
            return {'active_id':self._state['active_id'],'profiles':[{k:row[k] for k in ('id','name')} for row in self._state['profiles']],
                    'recovery_backups':recoveries,'backup_directory':str(self.workspace.directory/'backups') if hasattr(self,'workspace') else None}

    def create(self,name):
        with self.lock:
            self._check_current()
            name=self._name(name)
            if len(self._state['profiles'])>=20:raise ValueError('Use at most 20 local profiles')
            if any(row['name'].casefold()==name.casefold() for row in self._state['profiles']):raise ValueError('That profile name is already used')
            identity=str(uuid4());workspace=LocalWorkspace(self.directory/identity)
            # Empty profiles never inherit preview samples or another profile's preferences.
            workspace.research.snapshot()
            row={'id':identity,'name':name,'storage':identity,'created_at':env.now()}
            state={**self._state,'profiles':[*self._state['profiles'],row]}
            atomic_json(self.registry,state);self._state=state;self._cache[identity]=workspace
            return {'profile':{k:row[k] for k in ('id','name')},**self.snapshot()}

    def switch(self,identity):
        env.identifier(identity)
        with self.lock:
            self._check_current()
            row=next((r for r in self._state['profiles'] if r['id']==identity),None)
            if row is None:raise ValueError('Choose an existing local profile')
            if identity!=self._state['active_id']:
                workspace=self._open(row)
                self.workspace.backup()
                state={**self._state,'active_id':identity}
                atomic_json(self.registry,state);self._state=state;self.workspace=workspace
                self.session_token=secrets.token_urlsafe(24);self._pending_reset=None
            return self.snapshot()

    def _revision(self):
        # Detect app writes and newly delivered producer files since reset was reviewed.
        root=self.workspace.directory;hashes={}
        for child in root.iterdir():
            if child.name in ('backups','browser','reviews','sample-history','reference-corrections') or child.name.endswith('.log'):continue
            if child.is_symlink():raise ValueError('Profile storage cannot use links')
            for path in child.rglob('*') if child.is_dir() else (child,):
                if path.is_symlink():raise ValueError('Profile storage cannot use links')
                if path.is_file():hashes[str(path.relative_to(root))]=hashlib.sha256(regular(path).read_bytes()).hexdigest()
        return env.fingerprint({'profile':self._active()['id'],'storage':self._active()['storage'],'files':hashes})

    def reset_preview(self):
        with self.lock,self.workspace.state_lock,self.workspace.research.lock:
            self._check_current()
            workspace=self.workspace;snapshot=workspace.research.snapshot()
            with closing(workspace.research.connect()) as db:
                counts={key:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for key,table in
                        (('requests','research_requests'),('results','research_results'),('feedback','research_feedback'))}
            institutions,programs=workspace.records()
            counts.update(saved_countries=sum(r['watched'] for r in snapshot['countries'].values()),
                          universities=len(institutions),programs=len(programs))
            token=secrets.token_urlsafe(24)
            self._pending_reset={'token':token,'revision':self._revision(),'profile_id':self._active()['id']}
            return {**self._pending_reset,'name':self._active()['name'],'counts':counts}

    def reset(self,profile_id,token,confirmation):
        with self.lock,self.workspace.state_lock,self.workspace.research.lock:
            self._check_current()
            pending=self._pending_reset
            if confirmation!='RESET' or not pending or profile_id!=self._active()['id'] or profile_id!=pending['profile_id'] or token!=pending['token']:
                raise ValueError('Review the current profile and type RESET to confirm')
            if self._revision()!=pending['revision']:
                self._pending_reset=None
                raise ValueError('Profile data changed. Review the reset summary again before confirming')
            workspace=self.workspace;backup=workspace.backup()
            storage=str(uuid4());fresh=LocalWorkspace(self.directory/storage);fresh.research.snapshot()
            old=self._active();row={**old,'storage':storage}
            history=[*self._state.get('reset_history',[]),{'profile_id':profile_id,'name':old['name'],
                'storage':old['storage'],'backup':backup['name'],'reset_at':env.now()}]
            state={**self._state,'profiles':[row if p['id']==profile_id else p for p in self._state['profiles']],'reset_history':history}
            # One atomic pointer change makes reset all-or-nothing. Old files stay recoverable.
            atomic_json(self.registry,state);self._state=state;self._cache[storage]=fresh;self.workspace=fresh
            self.session_token=secrets.token_urlsafe(24);self._pending_reset=None
            return {'reset':True,'backup':backup['name'],'profile_id':profile_id}
