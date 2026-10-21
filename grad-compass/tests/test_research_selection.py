"""Complete catalogue drafts are private, guarded and independent of research."""
import unittest
import test_local as fixtures
import test_profiles as http_fixtures
from web.profiles import LocalProfiles
from web.research_selection import selection
from web.country_evidence import COUNTRY_CODES
from web.recovery import restore_backup


class ResearchSelectionTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.LocalTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.profiles=LocalProfiles(self.case.workspace.directory)
        self.workspace=self.profiles.workspace

    def test_complete_catalogue_exclusions_clear_and_reopen_preserve_personal_state(self):
        before=self.workspace.research.snapshot()
        self.workspace.research.save_country({'country_code':'BEL','watched':True,'note':'My private note'})
        self.workspace.country_decisions('BEL','On hold')
        codes=sorted(COUNTRY_CODES)
        self.assertGreater(len(codes),200)
        selection(self.workspace,{'countries':codes})
        self.assertEqual(selection(LocalProfiles(self.case.workspace.directory).workspace),{'countries':codes})
        codes.remove('BEL');selection(self.workspace,{'countries':codes})
        self.assertEqual(self.workspace.research.snapshot()['draft_selection'],codes)
        self.assertEqual(self.workspace.research.snapshot()['requests'],before['requests'])
        self.assertEqual(self.workspace.research.snapshot()['preferences'],before['preferences'])
        self.assertEqual(self.workspace.research.snapshot()['countries']['BEL'],{'watched':True,'note':'My private note'})
        self.assertEqual(self.workspace.country_decisions(),{'BEL':'On hold'})
        selection(self.workspace,{'countries':[]});self.assertEqual(selection(self.workspace),{'countries':[]})
        self.assertEqual((self.workspace.directory/'research-selection.json').stat().st_mode&0o777,0o600)

    def test_profile_isolation_backup_and_recovery(self):
        codes=sorted(COUNTRY_CODES);personal=self.profiles.snapshot()['active_id']
        selection(self.workspace,{'countries':codes})
        backup=self.workspace.backup()
        restored=restore_backup(self.workspace.directory/'backups'/backup['name'],self.case.root/'restored-selection')
        self.assertEqual(selection(restored),{'countries':codes})
        other=self.profiles.create('Empty research draft')['profile']['id'];self.profiles.switch(other)
        self.assertEqual(selection(self.profiles.workspace),{'countries':[]})
        selection(self.profiles.workspace,{'countries':['CAN']});self.profiles.switch(personal)
        self.assertEqual(selection(self.profiles.workspace),{'countries':codes})

    def test_invalid_scope_and_guarded_http_do_not_overwrite_draft(self):
        selection(self.workspace,{'countries':['BEL']})
        helper=object.__new__(http_fixtures.ProfileTests);helper.profiles=self.profiles
        for value in ({'countries':['BEL','BEL']},{'countries':['not-a-country']},{'countries':'BEL'},{'countries':[True]}, {'countries':[],'watched':True},[]):
            with self.assertRaises(ValueError):selection(self.workspace,value)
        self.assertEqual(helper.http('/api/research/draft-selection',{'countries':['CAN']},token='wrong')['status'],403)
        self.assertEqual(selection(self.workspace),{'countries':['BEL']})
        self.assertEqual(helper.http('/api/research/draft-selection',{'countries':sorted(COUNTRY_CODES)})['status'],200)
        self.assertEqual(helper.http('/api/research')['payload']['draft_selection'],sorted(COUNTRY_CODES))

    def test_large_draft_is_not_silently_truncated_into_a_request(self):
        from copy import deepcopy
        before=self.workspace.research.snapshot()
        codes=sorted(COUNTRY_CODES);selection(self.workspace,{'countries':codes})
        payload=deepcopy(self.case.submission());payload['countries']=codes
        with self.assertRaisesRegex(ValueError,'between 1 and 20'):
            self.workspace.research.submit(payload)
        self.assertEqual(selection(self.workspace),{'countries':codes})
        self.assertEqual(self.workspace.research.snapshot()['requests'],before['requests'])

    def test_duplicate_json_keys_are_rejected_and_symlinks_are_not_followed(self):
        path=self.workspace.directory/'research-selection.json'
        path.write_text('{"countries":[],"countries":["BEL"]}')
        with self.assertRaises(ValueError):selection(self.workspace)
        path.unlink();target=self.case.root/'outside.json';target.write_text('{"countries":["CAN"]}')
        path.symlink_to(target)
        with self.assertRaises(ValueError):selection(self.workspace,{'countries':[]})
        self.assertEqual(target.read_text(),'{"countries":["CAN"]}')


if __name__=='__main__':unittest.main()
