"""Owner-private generated outputs on Linux; no approval or canonical validation.

The caller supplies an already authorized root. As with the local adapter, no
hostile process running as this OS user is supported. No automatic repair occurs.
"""
import ctypes
import errno
import os
from pathlib import Path
import secrets
import stat


class UnsafeOutput(ValueError):
    """Unsafe destination (intentionally excludes private paths/content)."""


def _check(fd, directory=False, links=1):
    info = os.fstat(fd)
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    mode = 0o700 if directory else 0o600
    if (not kind(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != mode
            or (not directory and info.st_nlink != links)):
        raise UnsafeOutput('unsafe output ownership, type, mode or links')
    # Fail closed if ACL inspection is unsupported or unavailable.
    if any(name.startswith('system.posix_acl_') for name in os.listxattr(fd)):
        raise UnsafeOutput('output ACL present')


def _publish(directory, temporary, name):
    """Linux atomic move without replacement; never fall back to hardlinks."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise OSError(errno.ENOSYS, 'exclusive atomic rename unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                       ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(directory, os.fsencode(temporary), directory, os.fsencode(name), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def write_private(root, relative, data):
    """Write bytes immutably; return True on creation, False on identical replay.

    Root and parent directories must already exist, owned by this user, 0700,
    without ACLs. Output is 0600. Conflicting or unsafe existing files fail.
    Final publication is exclusive and atomic; file and directory are fsynced.
    """
    if not isinstance(data, bytes):
        raise TypeError('output must be bytes')
    root = Path(root)
    relative = os.fspath(relative)
    parts = relative.split('/')
    if not root.is_absolute() or '..' in root.parts or any(p in ('', '.', '..') for p in parts):
        raise UnsafeOutput('invalid output path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    temporary = None
    try:
        # Walk without resolving symlinks, including ancestors of authorized root.
        for part in root.parts[1:]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        _check(fd, directory=True)
        for part in parts[:-1]:
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
            _check(fd, directory=True)
        name = parts[-1]

        def replay():
            existing = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            try:
                _check(existing)
            except BaseException:
                os.close(existing)
                raise
            with os.fdopen(existing, 'rb') as stream:
                if stream.read() != data:
                    raise UnsafeOutput('immutable output conflict')
            # A preceding process may have exited after rename but before the
            # directory flush. A replay acknowledgement must also be durable.
            os.fsync(fd)
            return False

        try:
            return replay()
        except FileNotFoundError:
            pass
        temporary = '.private-output-' + secrets.token_hex(16)
        output = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=fd)
        with os.fdopen(output, 'wb') as stream:
            _check(stream.fileno())
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            _publish(fd, temporary, name)
        except FileExistsError:
            return replay()
        temporary = None
        os.fsync(fd)
        return True
    finally:
        try:
            if temporary is not None:
                try:
                    os.unlink(temporary, dir_fd=fd)
                except FileNotFoundError:
                    pass  # Publication may have completed before an exception.
                os.fsync(fd)
        finally:
            os.close(fd)
