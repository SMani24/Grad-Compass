"""User export destinations never use repository/cache fallbacks."""
from pathlib import Path
from unittest.mock import patch
import unittest
import test_local as fixtures
from web.export_preferences import preference,destination
from web.local import LocalWorkspace


class ExportPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.LocalTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
    def test_initial_folder_collisions_and_missing_custom_folder(self):
        base=self.f.root/'Downloads/GradCompass'
        with patch('web.export_preferences.default_folder',return_value=base):
            self.assertEqual(preference(self.f.workspace)['folder'],str(base));self.assertFalse(base.exists())
            path=destination(self.f.workspace,'report.pdf');self.assertEqual(path,base/'report.pdf');path.write_bytes(b'keep original')
            self.assertEqual(destination(self.f.workspace,'report.pdf'),base/'report-2.pdf');self.assertEqual(path.read_bytes(),b'keep original')
            custom=self.f.root/'chosen';custom.mkdir();preference(self.f.workspace,str(custom));custom.rmdir()
            with self.assertRaisesRegex(ValueError,'missing'):destination(self.f.workspace,'report.md')
            self.assertEqual(preference(self.f.workspace)['folder'],str(custom))
    def test_profile_restart_isolation_reset_and_native_cancel(self):
        chosen=self.f.root/'exports';chosen.mkdir();preference(self.f.workspace,str(chosen))
        self.assertEqual(preference(LocalWorkspace(self.f.workspace.directory))['folder'],str(chosen))
        other=LocalWorkspace(self.f.root/'other');self.assertNotEqual(preference(other)['folder'],str(chosen))
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from desktop_exports import DesktopExports
        import threading
        bridge=DesktopExports();answer={'done':threading.Event()}
        with patch('desktop_exports.QFileDialog.getExistingDirectory',return_value=''):bridge.perform(self.f.workspace,'change',answer)
        self.assertTrue(answer['result']['cancelled']);self.assertEqual(preference(self.f.workspace)['folder'],str(chosen))
        preference(self.f.workspace,reset=True);self.assertTrue(preference(self.f.workspace)['is_default']);self.assertTrue(chosen.exists())
