"""Automatic local receipt only. This module never invokes a producer or agent."""
from contextlib import closing, nullcontext
from http.server import ThreadingHTTPServer
import hashlib
import sqlite3
import threading
import time

from web import research_envelopes as env
from web.local import private_directory


class InboxReceiver:
    def __init__(self, workspace, quiet_seconds=1, clock=time.time):
        self.workspace=workspace;self.quiet_seconds=quiet_seconds;self.clock=clock
        self.processed={};self.errors={};self.lock=threading.RLock()
        self.checked_at=None;self.problem=None;self.pending=0

    @staticmethod
    def signature(path):
        value=path.lstat()
        return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)

    def check(self):
        with self.lock,self.workspace.state_lock,self.workspace.research.lock:
            candidates=[];signatures={};pending=0;backed_up=False;received=0
            try:
                inbox=private_directory(self.workspace.directory/'inbox')
                files={p.name:p for p in inbox.glob('*.json') if not p.name.startswith('.')}
                self.errors={name:error for name,error in self.errors.items() if name in files}
                self.processed={name:value for name,value in self.processed.items() if name in files}
                for name,path in sorted(files.items()):
                    try:
                        signature=self.signature(path)
                        # Producers publish atomically. Also tolerate a writer that is still
                        # closing a file; changed bytes are checked again during the read.
                        if self.clock()-path.lstat().st_mtime<self.quiet_seconds:
                            pending+=1;self.errors.pop(name,None);continue
                        if self.processed.get(name)==signature:continue
                        candidates.append(path);signatures[name]=signature
                    except OSError as error:self.errors[name]=str(error)
                def backup_once():
                    nonlocal backed_up
                    if not backed_up:self.workspace.backup();backed_up=True
                receipt=self.workspace.research.scan_inbox(candidates,before_record=backup_once)
                received=receipt['received']
                for outcome in receipt['outcomes']:
                    name=outcome['file']
                    if 'error' in outcome:self.errors[name]=outcome['error']
                    else:
                        self.errors.pop(name,None);self.processed[name]=signatures[name]
                self.workspace.last_receipt=receipt;self.problem=None;self.pending=pending
            except (ValueError,OSError,sqlite3.Error) as error:
                self.problem='Could not check incoming responses: '+str(error)
            self.checked_at=env.now()
            return {**self.status(),'received':received}

    def status(self):
        with self.lock,closing(self.workspace.research.connect()) as db:
            # Receipt identity drives UI updates without exposing payloads on every tick.
            rows=[tuple(row) for row in db.execute('SELECT id,request_id FROM research_acks ORDER BY id')]
            rows.extend(tuple(row) for row in db.execute('SELECT id,revision,request_id FROM research_results ORDER BY request_id,revision'))
            version=hashlib.sha256(env.compact(rows).encode()).hexdigest()
            latest=db.execute('SELECT request_id FROM research_results ORDER BY rowid DESC LIMIT 1').fetchone()
            count=db.execute('SELECT count(DISTINCT request_id) FROM research_results').fetchone()[0]
            errors=[{'file':name,'error':value} for name,value in sorted(self.errors.items())]
            if self.problem:errors.append({'file':'Inbox','error':self.problem})
            return {'version':version,'checked_at':self.checked_at,'pending':self.pending,'errors':errors,
                    'ready_count':count,'latest_request_id':latest[0] if latest else None}


def receiver_for(workspace):
    with workspace.state_lock:
        if not hasattr(workspace,'inbox_receiver'):workspace.inbox_receiver=InboxReceiver(workspace)
        return workspace.inbox_receiver


class InboxServer(ThreadingHTTPServer):
    """A small managed polling thread survives browser timer throttling."""
    def __init__(self,address,handler,workspace,profiles=None,interval=5):
        super().__init__(address,handler)
        self.workspace=workspace;self.profiles=profiles;self.interval=interval
        self._inbox_stop=threading.Event()
        self.check_inbox()
        self._inbox_thread=threading.Thread(target=self._watch_inbox,name='grad-compass-inbox',daemon=True)
        self._inbox_thread.start()

    def check_inbox(self):
        with self.profiles.request_context() if self.profiles else nullcontext():
            workspace=self.profiles.workspace if self.profiles else self.workspace
            return receiver_for(workspace).check()

    def _watch_inbox(self):
        while not self._inbox_stop.wait(self.interval):
            try:self.check_inbox()
            except (ValueError,OSError,sqlite3.Error):
                # A stale separate app window must not write into another profile.
                # Its API returns the actionable close/reopen message instead.
                continue

    def server_close(self):
        self._inbox_stop.set()
        if hasattr(self,'_inbox_thread'):self._inbox_thread.join(timeout=5)
        super().server_close()
