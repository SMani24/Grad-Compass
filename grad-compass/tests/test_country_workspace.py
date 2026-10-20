"""Decisions/layout remain profile-local; report availability is scoped metadata."""
from pathlib import Path
import unittest
import test_local as fixtures
import test_profiles as profile_fixtures
from web.profiles import LocalProfiles
from web.panels import preferences
from web.recovery import restore_backup


class CountryWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.LocalTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.profiles=LocalProfiles(self.case.workspace.directory)

    def test_country_report_status_does_not_claim_university_or_exhaustive_coverage(self):
        store=self.case.workspace.research
        self.assertEqual(store.snapshot()['requests'][0]['country_reports'],{})
        self.case.complete()
        request=store.snapshot()['requests'][0]
        self.assertEqual(request['country_reports'],{'CAN':{'review_status':'pending'}})
        self.assertEqual(self.case.workspace.overview()['universities'],[])
        self.assertEqual(request['completion'],'complete')
        self.assertIn('unknown',str(store.request(request['request_id'])['results'][0]['envelope']['findings'][0]['human_approval']))

    def test_decision_requires_both_tokens_then_persists_without_changing_research(self):
        # Use the real managed handler with the exact headers that failed in the UI.
        helper=object.__new__(profile_fixtures.ProfileTests);helper.profiles=self.profiles
        before=self.profiles.workspace.research.snapshot()
        payload={'country_code':'BEL','decision':'Shortlisted'}
        self.assertEqual(helper.http('/api/country-decisions',payload,**{'X-Grad-Compass-Workspace':''})['status'],403)
        self.assertEqual(self.profiles.workspace.country_decisions(),{})
        response=helper.http('/api/country-decisions',payload)
        self.assertEqual(response['status'],200);self.assertEqual(response['payload']['country_decisions'],{'BEL':'Shortlisted'})
        self.assertEqual(self.profiles.workspace.research.snapshot(),before)
        personal=self.profiles.snapshot()['active_id'];other=self.profiles.create('Other')['profile']['id']
        self.profiles.switch(other);self.assertEqual(self.profiles.workspace.country_decisions(),{})
        self.profiles.workspace.country_decisions('BEL','Excluded')
        self.profiles.switch(personal)
        reopened=LocalProfiles(self.case.workspace.directory)
        self.assertEqual(reopened.workspace.country_decisions(),{'BEL':'Shortlisted'})
        self.assertEqual(reopened.workspace.research.snapshot(),before)

    def test_panel_preferences_validation_profile_isolation_and_recovery(self):
        workspace=self.profiles.workspace;before=workspace.research.snapshot()
        self.assertEqual(preferences(workspace),{'left':300,'right':350})
        for value in ({'left':True,'right':350},{'left':259,'right':350},{'left':400,'right':721},{'left':400},['400']):
            with self.assertRaises(ValueError):preferences(workspace,value)
        preferences(workspace,{'left':440,'right':460})
        workspace.country_decisions('BEL','On hold')
        backup=workspace.backup();restored=restore_backup(workspace.directory/'backups'/backup['name'],self.case.root/'restored-panels')
        self.assertEqual(preferences(restored),{'left':440,'right':460})
        self.assertEqual(restored.country_decisions(),{'BEL':'On hold'})
        other=self.profiles.create('Other')['profile']['id'];self.profiles.switch(other)
        self.assertEqual(preferences(self.profiles.workspace),{'left':300,'right':350})
        self.assertEqual(workspace.research.snapshot(),before)

    def test_panel_endpoint_is_profile_guarded_and_rejects_unknown_fields(self):
        helper=object.__new__(profile_fixtures.ProfileTests);helper.profiles=self.profiles
        self.assertEqual(helper.http('/api/panel-widths',{'left':420,'right':440},token='wrong')['status'],403)
        self.assertEqual(helper.http('/api/panel-widths',{'left':420,'right':440,'text_size':'large'})['status'],409)
        self.assertEqual(helper.http('/api/panel-widths',{'left':420,'right':440})['status'],200)
        self.assertEqual(helper.http('/api/panel-widths')['payload']['left'],420)


if __name__=='__main__':unittest.main()
