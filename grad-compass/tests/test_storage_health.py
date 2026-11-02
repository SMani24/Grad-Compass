"""Synthetic private-store preflight; never access the owner's applicant files."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from web.storage_health import inspect_private_store, StorageHealthError, OWNED


class StorageHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in OWNED:
            (self.root/name).mkdir(mode=0o700)
        self.profile = self.root/'frozen'/'invented-revision'
        self.profile.mkdir(mode=0o700)
        self.file = self.profile/'profile.json'
        self.file.write_text('{"invented":true}')
        self.file.chmod(0o400)

    def test_unrelated_historical_review_blocks_before_any_private_content_read(self):
        review=self.root/'reviews'/'invented-old-review.md'
        review.write_text('Invented historical content');review.chmod(0o664)
        before=review.stat()
        with patch.object(Path,'read_bytes',side_effect=AssertionError('Preflight opened private bytes')):
            with self.assertRaisesRegex(StorageHealthError,'permissions need owner-local maintenance'):
                inspect_private_store(self.profile)
        self.assertEqual(review.stat().st_mode,before.st_mode)
        self.assertEqual(review.stat().st_mtime_ns,before.st_mtime_ns)
        review.chmod(0o600)
        self.assertEqual(inspect_private_store(self.profile)['state'],'ready')
        self.assertEqual(self.file.stat().st_mode & 0o777,0o400)

    def test_links_additional_grants_and_wrong_owners_remain_security_errors(self):
        link=self.root/'reviews'/'link';link.symlink_to(self.file)
        with self.assertRaisesRegex(StorageHealthError,'unexpected owner or object'):
            inspect_private_store(self.profile)
        link.unlink();link.hardlink_to(self.file)
        with self.assertRaisesRegex(StorageHealthError,'linked files'):
            inspect_private_store(self.profile)
        link.unlink()
        with patch('web.storage_health.os.listxattr',return_value=['system.posix_acl_access']):
            with self.assertRaisesRegex(StorageHealthError,'additional access grants'):
                inspect_private_store(self.profile)
        with patch('web.storage_health.os.getuid',return_value=os.getuid()+1):
            with self.assertRaisesRegex(StorageHealthError,'unexpected owner'):
                inspect_private_store(self.profile)

    def test_adjacent_cv_policy_is_not_silently_redefined(self):
        cv=self.root/'cv';cv.mkdir(mode=0o755);(cv/'invented-public-template').write_text('Synthetic')
        self.assertEqual(inspect_private_store(self.profile)['state'],'ready')

    def test_unavailable_store_and_unreadable_subtrees_fail_closed(self):
        with self.assertRaisesRegex(StorageHealthError,'unavailable'):
            inspect_private_store(self.root/'missing')
        with patch('web.storage_health.os.walk',side_effect=PermissionError('Private path must not escape')):
            with self.assertRaisesRegex(StorageHealthError,'cannot be checked') as error:
                inspect_private_store(self.profile)
        self.assertNotIn('Private path',str(error.exception))
