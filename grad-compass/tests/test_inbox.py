"""Automatic receipt checks use invented data in disposable local workspaces."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import test_local as fixtures
from web import research_envelopes as env
from web.inbox import InboxReceiver,InboxServer,receiver_for
from web.local import LocalWorkspace
from web.profiles import LocalProfiles
from web.server import handler_for


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.LocalTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.workspace=self.fixture.workspace;self.store=self.workspace.research
        self.receiver=InboxReceiver(self.workspace,quiet_seconds=0)

    def deliver(self,value,name='response.json'):
        path=self.workspace.directory/'inbox'/name
        raw=json.dumps(env.packet(value)).encode()
        temporary=path.with_name('.'+name+'.tmp');temporary.write_bytes(raw);temporary.replace(path)
        return path

    def sequence(self):
        ack=self.fixture.ack();partial={**self.fixture.result(),'completion':'partial'}
        digest=env.packet(partial)['sha256']
        final={**deepcopy(partial),'result_revision':2,'previous_result_revision':1,
               'previous_result_digest':digest,'completion':'complete'}
        return ack,partial,final

    def test_ack_partial_final_are_received_automatically_with_original_review_states(self):
        ack,partial,final=self.sequence()
        self.deliver(ack,'ack.json');self.assertEqual(self.receiver.check()['received'],1)
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'accepted')
        with patch('web.inbox.private_directory',side_effect=OSError('Invented unreadable inbox')):
            failed=self.receiver.check();self.assertEqual(failed['received'],0)
            self.assertIn('Could not check',failed['errors'][-1]['error'])
        self.deliver(partial,'partial.json');status=self.receiver.check()
        self.assertEqual(status['ready_count'],1);self.assertEqual(status['received'],1)
        self.assertEqual(self.store.snapshot()['requests'][0]['completion'],'partial')
        self.deliver(final,'final.json');self.assertEqual(self.receiver.check()['received'],1)
        detail=self.store.request(self.fixture.request['request_id'])
        self.assertEqual(len(detail['results']),2)
        self.assertEqual(detail['results'][-1]['envelope']['completion'],'complete')
        finding=detail['results'][-1]['envelope']['findings'][0]
        self.assertEqual(finding['review_status'],'pending');self.assertEqual(finding['human_approval'],{'state':'unknown'})
        self.assertEqual(detail['results'][-1]['envelope']['_transport'],env.packet(final))

    def test_replay_restart_and_closed_app_pending_delivery_make_no_duplicate_changes(self):
        ack,partial,final=self.sequence();self.deliver(ack,'ack.json');self.deliver(partial,'partial.json')
        self.receiver.check();before=self.store.snapshot();version=self.receiver.status()['version']
        with patch.object(self.workspace,'backup',side_effect=AssertionError('Replay must not create backups')):
            self.assertEqual(self.receiver.check()['received'],0)
            replay=InboxReceiver(self.workspace,quiet_seconds=0)
            self.assertEqual(replay.check()['received'],0)
        self.assertEqual(self.store.snapshot(),before);self.assertEqual(replay.status()['version'],version)
        self.deliver(final,'final.json') # Delivered while the previous app/receiver is closed.
        reopened=LocalWorkspace(self.workspace.directory);receiver=InboxReceiver(reopened,quiet_seconds=0)
        self.assertEqual(receiver.check()['received'],1)
        self.assertEqual(len(reopened.research.request(self.fixture.request['request_id'])['results']),2)

    def test_hidden_temporary_recent_and_changing_files_are_not_received(self):
        ack=self.fixture.ack();packet=json.dumps(env.packet(ack))
        inbox=self.workspace.directory/'inbox'
        for name in ('.hidden.json','ack.json.tmp','ack.part'):(inbox/name).write_text(packet)
        clock=[time.time()];receiver=InboxReceiver(self.workspace,clock=lambda:clock[0])
        path=inbox/'ack.json';path.write_text('{unfinished')
        self.assertEqual(receiver.check()['pending'],1);self.assertEqual(receiver.status()['errors'],[])
        path.write_text(packet);clock[0]=time.time()+2
        original=Path.read_bytes
        def changing(value):
            raw=original(value)
            if value==path:value.write_text(packet+' ')
            return raw
        with patch.object(Path,'read_bytes',changing):self.assertEqual(receiver.check()['received'],0)
        self.assertEqual(receiver.check()['received'],1)
        self.assertEqual(len(self.store.snapshot()['requests']),1)

    def test_invalid_digest_duplicate_keys_unknown_request_and_conflicts_remain_visible(self):
        ack=self.fixture.ack();path=self.deliver(ack,'ack.json');self.receiver.check()
        different={**ack,'state':'rejected'};self.deliver(different,'conflict.json')
        self.deliver({**ack,'request_id':str(uuid4())},'unknown.json')
        packet=env.packet(ack);packet['body']+=' '
        (path.parent/'digest.json').write_text(json.dumps(packet))
        raw=env.packet(ack);raw['body']=raw['body'].replace('"state":','"state":"rejected","state":')
        raw['sha256']=hashlib.sha256(raw['body'].encode()).hexdigest()
        (path.parent/'duplicates.json').write_text(json.dumps(raw))
        (path.parent/'malformed.json').write_text('{}')
        status=self.receiver.check();self.assertEqual(len(status['errors']),5)
        self.assertEqual(status['received'],0);self.assertEqual(self.store.snapshot()['requests'][0]['state'],'accepted')
        self.assertIn('Duplicate JSON',' '.join(item['error'] for item in status['errors']))
        (path.parent/'malformed.json').unlink()
        self.assertEqual(len(self.receiver.check()['errors']),4)

    def test_missing_dependencies_retry_and_backup_failure_does_not_record(self):
        ack,partial,final=self.sequence();self.deliver(final,'z-final.json')
        self.assertEqual(len(self.receiver.check()['errors']),1)
        self.deliver(partial,'y-partial.json');self.deliver(ack,'x-ack.json')
        with patch.object(self.workspace,'backup',side_effect=OSError('Invented backup failure')):
            status=self.receiver.check();self.assertEqual(status['received'],0)
            self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')
        status=self.receiver.check();self.assertEqual(status['received'],3);self.assertEqual(status['errors'],[])
        self.assertEqual(self.store.snapshot()['requests'][0]['completion'],'complete')

    def test_periodic_server_receipt_profile_isolation_and_thread_shutdown(self):
        # Exercise the managed worker without requiring a listening socket in unit tests.
        for name in ('__init__','server_close'):
            mocked=patch('web.inbox.ThreadingHTTPServer.'+name,return_value=None)
            mocked.start();self.addCleanup(mocked.stop)
        profiles=LocalProfiles(self.workspace.directory);personal=profiles.snapshot()['active_id']
        profiles.workspace.inbox_receiver=InboxReceiver(profiles.workspace,quiet_seconds=0)
        server=InboxServer(('127.0.0.1',0),handler_for(profiles.workspace,profiles=profiles),profiles.workspace,profiles,interval=.02)
        self.addCleanup(server.server_close)
        def until(predicate):
            end=time.monotonic()+5
            while time.monotonic()<end:
                if predicate():return
                time.sleep(.02)
            self.fail('Automatic receiver did not make progress')
        self.deliver(self.fixture.ack(),'ack.json')
        until(lambda:profiles.workspace.research.snapshot()['requests'][0]['state']=='accepted')
        other=profiles.create('Testing')['profile']['id'];profiles.switch(other)
        self.deliver(self.fixture.result(),'result.json')
        time.sleep(.08);self.assertEqual(profiles.workspace.research.snapshot()['requests'],[])
        profiles.switch(personal)
        until(lambda:profiles.workspace.research.snapshot()['requests'][0]['result_count']==1)
        server.server_close();self.assertFalse(server._inbox_thread.is_alive())

    def test_export_names_exact_profile_inbox_and_atomic_delivery_without_acknowledgement(self):
        exported=self.store.export(self.fixture.request['request_id'])
        self.assertIn(str(self.workspace.directory/'inbox'),exported['prompt'])
        self.assertIn('atomically rename',exported['prompt'])
        self.assertIn('applicant must not relay',exported['prompt'])
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')

    def test_copy_endpoint_only_copies_saved_instructions_with_session_authorization(self):
        copied=[];handler=object.__new__(handler_for(self.workspace,session_token='test-session',clipboard=SimpleNamespace(copy_text=copied.append)))
        handler.path='/api/local/copy-instructions';handler.server=SimpleNamespace(server_port=8765)
        handler.headers={'Host':'127.0.0.1:8765','Origin':'http://127.0.0.1:8765','Content-Type':'application/json'}
        response={};handler.respond=lambda status,data:response.update(status=status,data=data)
        def invoke(payload):
            raw=json.dumps(payload).encode();handler.headers['Content-Length']=str(len(raw));handler.rfile=io.BytesIO(raw);handler.do_POST();return response['status']
        payload={'request_id':self.fixture.request['request_id']}
        self.assertEqual(invoke(payload),403);self.assertEqual(copied,[])
        handler.headers['X-Grad-Compass-Session']='test-session'
        self.assertEqual(invoke({**payload,'text':'Untrusted text'}),409);self.assertEqual(copied,[])
        self.assertEqual(invoke(payload),200)
        self.assertEqual(copied,[self.store.export(payload['request_id'])['prompt']])
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')

    def test_invalid_request_revision_digest_and_prior_revision_are_not_recorded(self):
        ack,partial,final=self.sequence()
        for index,changes in enumerate(({'request_revision':2},{'request_digest':'0'*64},{'synthetic':True})):
            self.deliver({**ack,**changes},f'invalid-{index}.json')
        self.assertEqual(len(self.receiver.check()['errors']),3)
        self.assertEqual(self.store.snapshot()['requests'][0]['state'],'prepared')
        self.deliver(ack,'ack.json');self.deliver(partial,'partial.json');self.receiver.check()
        self.deliver({**final,'previous_result_digest':'0'*64},'invalid-final.json')
        self.assertEqual(self.receiver.check()['received'],0)
        self.assertEqual(self.store.snapshot()['requests'][0]['result_count'],1)


if __name__=='__main__':unittest.main()
