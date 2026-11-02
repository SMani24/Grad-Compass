"""Invented bytes only; never opens production storage."""
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from private_output import UnsafeOutput, write_private


class PrivateOutputTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='private-output-synthetic-')
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def test_permissive_umask_and_replay_conflict(self):
        old = os.umask(0)
        try:
            self.assertTrue(write_private(self.root, 'review', b'invented'))
        finally:
            os.umask(old)
        path = self.root / 'review'
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        inode = path.stat().st_ino
        self.assertFalse(write_private(self.root, 'review', b'invented'))
        with self.assertRaises(UnsafeOutput):
            write_private(self.root, 'review', b'conflict')
        self.assertEqual(path.read_bytes(), b'invented')
        self.assertEqual(path.stat().st_ino, inode)

    def test_unsafe_paths_symlinks_and_hardlinks(self):
        for name in ('../escape', '/absolute', 'a/../escape', './review', 'a//review', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                write_private(self.root, name, b'invented')
        (self.root / 'link').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            write_private(self.root, 'link/review', b'invented')
        (self.root / 'file-link').symlink_to('missing')
        with self.assertRaises(OSError):
            write_private(self.root, 'file-link', b'invented')
        write_private(self.root, 'review', b'invented')
        os.link(self.root / 'review', self.root / 'alias')
        with self.assertRaises(UnsafeOutput):
            write_private(self.root, 'review', b'invented')

    def test_modes_types_owner_and_acl_fail_closed(self):
        self.root.chmod(0o755)
        with self.assertRaises(UnsafeOutput):
            write_private(self.root, 'review', b'invented')
        self.root.chmod(0o700)
        (self.root / 'directory').mkdir(mode=0o700)
        with self.assertRaises(UnsafeOutput):
            write_private(self.root, 'directory', b'invented')
        with patch('private_output.os.geteuid', return_value=os.geteuid()+1):
            with self.assertRaises(UnsafeOutput):
                write_private(self.root, 'review', b'invented')
        with patch('private_output.os.listxattr', return_value=['system.posix_acl_default']):
            with self.assertRaises(UnsafeOutput):
                write_private(self.root, 'review', b'invented')
        with patch('private_output.os.listxattr', side_effect=OSError('unsupported')):
            with self.assertRaises(OSError):
                write_private(self.root, 'review', b'invented')
        self.assertEqual(list(self.root.iterdir()), [self.root / 'directory'])

    def test_interrupted_write_has_no_final_or_temporary(self):
        with patch('private_output.os.fsync', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                write_private(self.root, 'review', b'invented')
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertTrue(write_private(self.root, 'review', b'invented'))

    def test_process_exit_before_publication_leaves_only_private_orphan(self):
        code = """
import os, sys
from unittest.mock import patch
from private_output import write_private
with patch('private_output.os.fsync', side_effect=lambda fd: os._exit(23)):
    write_private(sys.argv[1], 'review', b'invented')
"""
        result = subprocess.run([sys.executable, '-c', code, str(self.root)],
                                env={**os.environ, 'PYTHONPATH': sys.path[0]}, check=False)
        self.assertEqual(result.returncode, 23)
        self.assertFalse((self.root / 'review').exists())
        files = list(self.root.iterdir())
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name.startswith('.private-output-'))
        self.assertEqual(stat.S_IMODE(files[0].stat().st_mode), 0o600)
        self.assertTrue(write_private(self.root, 'review', b'invented'))

    def test_process_exit_after_publication_and_durable_replay(self):
        from workflow import Store
        store = Store(self.root, synthetic=True)
        destination = self.root / 'reviews'
        code = """
import os, sys
from unittest.mock import patch
import private_output
publish = private_output._publish
def exit_after_publish(*args):
    publish(*args)
    os._exit(24)
with patch('private_output._publish', side_effect=exit_after_publish):
    private_output.write_private(sys.argv[1], 'review', b'invented')
"""
        result = subprocess.run([sys.executable, '-c', code, str(destination)],
                                env={**os.environ, 'PYTHONPATH': sys.path[0]}, check=False)
        self.assertEqual(result.returncode, 24)
        self.assertEqual(list(destination.iterdir()), [destination / 'review'])
        self.assertEqual((destination / 'review').stat().st_nlink, 1)
        self.assertFalse(write_private(destination, 'review', b'invented'))
        with self.assertRaises(UnsafeOutput):
            write_private(destination, 'review', b'conflict')
        store.guard()

    def test_durable_publication_replays_in_new_process(self):
        self.assertTrue(write_private(self.root, 'review', b'invented'))
        code = """
import sys
from private_output import write_private
assert write_private(sys.argv[1], 'review', b'invented') is False
"""
        subprocess.run([sys.executable, '-c', code, str(self.root)],
                       env={**os.environ, 'PYTHONPATH': sys.path[0]}, check=True)
        self.assertEqual((self.root / 'review').stat().st_nlink, 1)

    def test_replay_flushes_final_directory_and_reports_durability_failure(self):
        write_private(self.root, 'review', b'invented')
        with patch('private_output.os.fsync', side_effect=OSError('directory flush failed')):
            with self.assertRaises(OSError):
                write_private(self.root, 'review', b'invented')
        self.assertEqual((self.root / 'review').read_bytes(), b'invented')
        self.assertEqual((self.root / 'review').stat().st_nlink, 1)
        self.assertFalse(write_private(self.root, 'review', b'invented'))

    def test_unsupported_atomic_rename_fails_closed(self):
        import errno
        with patch('private_output.ctypes.CDLL', return_value=object()):
            with self.assertRaises(OSError) as error:
                write_private(self.root, 'review', b'invented')
        self.assertEqual(error.exception.errno, errno.ENOSYS)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_concurrent_immutable_publication(self):
        from concurrent.futures import ThreadPoolExecutor
        import private_output
        from threading import Barrier
        barrier = Barrier(2)
        publish = private_output._publish
        def synchronized(*args):
            barrier.wait(timeout=5)
            publish(*args)
        for contents in ((b'invented', b'invented'), (b'invented', b'conflict')):
            with self.subTest(contents=contents):
                destination = 'same' if contents[0] == contents[1] else 'different'
                def write(data):
                    try:
                        return write_private(self.root, destination, data)
                    except UnsafeOutput:
                        return 'conflict'
                with patch('private_output._publish', side_effect=synchronized):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        results = list(pool.map(write, contents))
                self.assertCountEqual(results, [True, False if contents[0] == contents[1] else 'conflict'])
                self.assertEqual((self.root / destination).stat().st_nlink, 1)
        self.assertFalse(any(p.name.startswith('.private-output-') for p in self.root.iterdir()))

    def test_publish_failure_cleanup_and_orphan_is_ignored(self):
        with patch('private_output._publish', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                write_private(self.root, 'review', b'invented')
        self.assertEqual(list(self.root.iterdir()), [])
        orphan = self.root / '.private-output-interrupted'
        orphan.write_bytes(b'partial invented bytes')
        orphan.chmod(0o600)
        self.assertTrue(write_private(self.root, 'review', b'invented'))
        self.assertEqual(orphan.read_bytes(), b'partial invented bytes')


if __name__ == '__main__':
    unittest.main()
