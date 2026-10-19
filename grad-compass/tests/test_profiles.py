"""Profile/reset/removal checks use only invented data in temporary storage."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import test_local as fixtures
from web import research_envelopes as env
from web.local import LocalWorkspace
from web.profiles import LocalProfiles
from web.recovery import restore_backup
from web.server import handler_for


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.LocalTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.workspace=self.fixture.workspace;self.store=self.workspace.research
        self.store.save_country({'country_code':'CAN','watched':True,'note':'Keep personal note'})
        self.workspace.country_decisions('CAN','Shortlisted');self.workspace.display_preferences('large')
        self.ack,self.result=self.fixture.complete(public=True)
        self.profiles=LocalProfiles(self.workspace.directory)
        self.workspace=self.profiles.workspace;self.store=self.workspace.research
        self.personal=self.profiles.snapshot()['active_id']
        self.identity=self.workspace.overview()['universities'][0]['research']['external_id']

    def reset(self,preview=None,**changes):
        preview=preview or self.profiles.reset_preview()
        return self.profiles.reset(**{'profile_id':preview['profile_id'],'token':preview['token'],'confirmation':'RESET',**changes})

    def test_remove_hides_parent_programs_and_pins_without_destroying_research(self):
        before=self.store.snapshot();requests=self.store.request(self.fixture.request['request_id'])
        removed=self.workspace.remove_university(self.identity)
        self.assertTrue(removed['changed']);self.assertFalse(self.workspace.remove_university(self.identity)['changed'])
        self.assertEqual(self.workspace.overview()['universities'],[])
        self.assertIsNone(self.workspace.university('local-'+self.identity))
        self.assertEqual(self.store.snapshot(),before);self.assertEqual(self.store.request(self.fixture.request['request_id']),requests)
        self.assertFalse(self.fixture.receive(self.result)['changed'])
        reopened=LocalWorkspace(self.workspace.directory)
        self.assertEqual(reopened.overview()['universities'],[])
        self.assertEqual(reopened.removed_universities()[0]['id'],self.identity)
        self.assertEqual(reopened.country_decisions(),{'CAN':'Shortlisted'})
        recovered=restore_backup(self.workspace.directory/'backups'/removed['backup'],self.fixture.root/'before-removal')
        self.assertEqual(len(recovered.overview()['universities']),1)
        self.workspace.restore_university(self.identity)
        detail=self.workspace.university('local-'+self.identity)
        self.assertEqual(len(detail['programs']),1)
        self.assertFalse(self.workspace.restore_university(self.identity)['changed'])

    def test_remove_validates_identity_and_backup_failure_preserves_visible_data(self):
        for identity in ('../outside',str(uuid4()),None):
            with self.assertRaises(ValueError):self.workspace.remove_university(identity)
        with patch.object(self.workspace,'backup',side_effect=OSError('Test backup failure')):
            with self.assertRaises(OSError):self.workspace.remove_university(self.identity)
        self.assertEqual(len(self.workspace.overview()['universities']),1)
        self.assertEqual(self.workspace.removed_universities(),[])

    def test_profiles_isolate_all_state_and_survive_relaunch(self):
        before=self.store.snapshot();details=self.store.request(self.fixture.request['request_id']);token=self.profiles.session_token
        created=self.profiles.create('Testing');identity=created['profile']['id']
        self.assertEqual(self.profiles.snapshot()['active_id'],self.personal,'Creating alone does not change the active profile')
        self.profiles.switch(identity);testing=self.profiles.workspace
        self.assertNotEqual(self.profiles.session_token,token)
        self.assertEqual(testing.overview()['universities'],[])
        self.assertEqual(testing.research.snapshot()['countries'],{})
        self.assertFalse(testing.research.snapshot()['has_preferences'])
        self.assertEqual(testing.display_preferences(),{'text_size':'standard'})
        self.assertEqual(testing.country_decisions(),{})
        with self.assertRaises(ValueError):testing.research.request(self.fixture.request['request_id'])
        testing.research.save_country({'country_code':'DEU','watched':True,'note':'Testing only'})
        testing.display_preferences('extra-large')
        reopened=LocalProfiles(self.workspace.directory)
        self.assertEqual(reopened.snapshot()['active_id'],identity)
        self.assertEqual(reopened.workspace.research.snapshot()['countries']['DEU']['note'],'Testing only')
        self.profiles.switch(self.personal)
        self.assertEqual(self.profiles.workspace.research.snapshot(),before)
        self.assertEqual(self.profiles.workspace.research.request(self.fixture.request['request_id']),details)
        self.assertEqual(self.profiles.workspace.display_preferences(),{'text_size':'large'})
        self.profiles.switch(identity)
        self.assertEqual(self.profiles.workspace.display_preferences(),{'text_size':'extra-large'})

    def test_reset_clears_active_data_without_reimport_and_preserves_recovery_and_other_profiles(self):
        other=self.profiles.create('Testing')['profile']['id']
        self.profiles.switch(other);self.profiles.workspace.research.save_country({'country_code':'FRA','watched':True})
        other_state=self.profiles.workspace.research.snapshot();self.profiles.switch(self.personal)
        original=self.store.snapshot();request=self.store.request(self.fixture.request['request_id'])
        self.workspace.remove_university(self.identity)
        preview=self.profiles.reset_preview();self.assertEqual(preview['counts']['universities'],1)
        self.assertEqual(preview['counts']['requests'],1);self.assertEqual(preview['counts']['programs'],1)
        self.reset(preview);fresh=self.profiles.workspace
        self.assertNotEqual(fresh.directory,self.workspace.directory)
        self.assertEqual(fresh.research.snapshot()['countries'],{});self.assertEqual(fresh.research.snapshot()['requests'],[])
        self.assertFalse(fresh.research.snapshot()['has_preferences'])
        self.assertEqual(fresh.country_decisions(),{});self.assertEqual(fresh.display_preferences(),{'text_size':'standard'})
        self.assertEqual(fresh.overview()['universities'],[]);self.assertEqual(fresh.removed_universities(),[])
        self.assertEqual(fresh.research.scan_inbox()['received'],0)
        self.assertEqual(fresh.archived_requests(),{'requests':[]})
        recovery=self.profiles.snapshot()['recovery_backups'][0]
        restored=restore_backup(recovery['path'],self.fixture.root/'restored')
        self.assertEqual(restored.research.snapshot(),original)
        self.assertEqual(restored.research.request(self.fixture.request['request_id']),request)
        self.assertEqual(restored.removed_universities()[0]['id'],self.identity)
        reopened=LocalProfiles(self.workspace.directory,previous=self.workspace.directory)
        self.assertEqual(reopened.workspace.research.snapshot()['countries'],{},'Old selections must not be recopied after reset')
        # Late responses for a pre-reset request are rejected, never resurrected.
        inbox=fresh.directory/'inbox/old.json';inbox.write_text(json.dumps(env.packet(self.ack)))
        self.assertEqual(fresh.research.scan_inbox()['errors'],1)
        self.assertEqual(fresh.research.snapshot()['requests'],[])
        self.profiles.switch(other);self.assertEqual(self.profiles.workspace.research.snapshot(),other_state)

    def test_reset_requires_exact_confirmation_and_fresh_bound_summary(self):
        before=self.store.snapshot();preview=self.profiles.reset_preview()
        for changes in ({'confirmation':'reset'},{'token':'wrong'},{'profile_id':str(uuid4())}):
            with self.assertRaises(ValueError):self.reset(preview,**changes)
        self.assertEqual(self.profiles.workspace.research.snapshot(),before)
        self.store.save_country({'country_code':'FRA','watched':True})
        with self.assertRaisesRegex(ValueError,'changed'):self.reset(preview)
        preview=self.profiles.reset_preview()
        (self.workspace.directory/'inbox/new.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'changed'):self.reset(preview)
        self.assertEqual(self.profiles.workspace,self.workspace)
        self.assertTrue(self.workspace.research.snapshot()['countries']['FRA']['watched'])

    def test_failed_reset_backup_or_registry_write_never_switches_or_erases_data(self):
        before=self.store.snapshot();preview=self.profiles.reset_preview()
        with patch.object(self.workspace,'backup',side_effect=OSError('Test backup failure')):
            with self.assertRaises(OSError):self.reset(preview)
        self.assertIs(self.profiles.workspace,self.workspace)
        preview=self.profiles.reset_preview()
        original=self.profiles.registry.read_bytes()
        with patch('web.profiles.atomic_json',side_effect=OSError('Test registry failure')):
            with self.assertRaises(OSError):self.reset(preview)
        self.assertEqual(self.profiles.registry.read_bytes(),original)
        self.assertIs(self.profiles.workspace,self.workspace)
        self.assertEqual(self.store.snapshot(),before)

    def test_profile_names_storage_paths_and_stale_windows_are_checked(self):
        for name in ('','  ','x'*61,'newline\nname',None,'personal'):
            with self.assertRaises(ValueError):self.profiles.create(name)
        stale=LocalProfiles(self.workspace.directory)
        self.profiles.create('Testing')
        with self.assertRaisesRegex(ValueError,'another app window'):stale.create('Lost update')
        with self.assertRaisesRegex(ValueError,'another app window'):
            with stale.request_context():pass
        state=deepcopy(self.profiles._state);state['profiles'][0]['storage']='../outside'
        self.profiles.registry.write_text(json.dumps(state))
        with self.assertRaises(ValueError):LocalProfiles(self.workspace.directory)

    def http(self,path,payload=None,token=None,**headers):
        handler=object.__new__(handler_for(self.profiles.workspace,profiles=self.profiles))
        handler.path=path;handler.server=SimpleNamespace(server_port=8765)
        handler.headers={'Host':'127.0.0.1:8765','Origin':'http://127.0.0.1:8765','X-Grad-Compass-Session':token or self.profiles.session_token,
                         'X-Grad-Compass-Workspace':self.profiles.session_token,
                         'Content-Type':'application/json',**headers}
        result={};handler.respond=lambda status,data:result.update(status=status,payload=data)
        if payload is None:handler.do_GET()
        else:
            raw=json.dumps(payload).encode();handler.headers['Content-Length']=str(len(raw));handler.rfile=io.BytesIO(raw);handler.do_POST()
        return result

    def test_http_scope_guards_and_old_tab_tokens_cannot_write_to_new_profile(self):
        for path,payload in (('/api/local/remove-university',{'id':self.identity}),('/api/local/profiles/create',{'name':'Testing'}),
                             ('/api/local/profiles/switch',{'profile_id':self.personal}),('/api/local/reset',{})):
            for headers in ({'Origin':'https://example.invalid'},{'Host':'example.invalid'},{'X-Grad-Compass-Session':'wrong'}):
                self.assertEqual(self.http(path,payload,**headers)['status'],403)
        self.assertEqual(self.http('/api/local/remove-university',{'id':self.identity,'extra':True})['status'],409)
        self.assertEqual(self.http('/api/local/reset',{})['status'],409)
        created=self.http('/api/local/profiles/create',{'name':'Testing'});self.assertEqual(created['status'],200)
        identity=created['payload']['profile']['id'];old=self.profiles.session_token
        self.assertEqual(self.http('/api/local/profiles/switch',{'profile_id':identity})['status'],200)
        self.assertEqual(self.http('/api/research/country',{'country_code':'CAN','watched':True},token=old)['status'],403)
        # A stale page cannot revive its old form by fetching a fresh CSRF token.
        self.assertEqual(self.http('/api/research/country',{'country_code':'CAN','watched':True},
                                  **{'X-Grad-Compass-Workspace':old})['status'],403)
        self.assertEqual(self.http('/api/workspace')['payload']['profiles']['active_id'],identity)
        self.assertEqual(self.profiles.workspace.research.snapshot()['countries'],{})
        preview=self.http('/api/local/reset-preview')['payload'];old=self.profiles.session_token
        self.assertEqual(self.http('/api/local/reset',{k:v for k,v in {**preview,'confirmation':'RESET'}.items() if k in ('profile_id','token','confirmation')})['status'],200)
        self.assertEqual(self.http('/api/local/backup',{},token=old)['status'],403)


if __name__=='__main__':unittest.main()
