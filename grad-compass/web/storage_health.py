"""Read-only operational preflight; canonical profile validation stays producer-owned.

Match the guarded store's privacy boundaries before dispatch, without opening
applicant documents, repairing access, or inferring factual approval.
"""
import os
from pathlib import Path
import stat

OWNED = ('intake', 'profiles', 'reviews', 'cache', 'sources', 'candidates', 'frozen')


class StorageHealthError(ValueError):
    pass


def inspect_report_output(workspace):
    """Read-only check of app-owned producer output roots, not legacy contents."""
    root=Path(workspace)
    try:
        for path in (root,root/'reports'):
            if any(p.is_symlink() for p in (path,*path.parents)):
                raise StorageHealthError('Private report output contains a link. Technical security review is required before dispatch.')
            info=path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid():
                raise StorageHealthError('Private report output has an unexpected owner or type. Technical security review is required before dispatch.')
            if any(name.startswith('system.posix_acl_') for name in os.listxattr(path,follow_symlinks=False)):
                raise StorageHealthError('Private report output has additional access grants. Technical security review is required before dispatch.')
            if stat.S_IMODE(info.st_mode)!=0o700:
                raise StorageHealthError('Private report output permissions need owner-local maintenance before dispatch (0700 required). Your saved request is retained; no new task was sent.')
        return {'state':'ready'}
    except OSError:
        raise StorageHealthError('Private report output cannot be checked. Restore its existing local directory before retrying this saved request.') from None


def inspect_private_store(profile):
    profile = Path(profile)
    root = profile.parent.parent if profile.parent.name == 'frozen' else profile
    for ancestor in (profile, *profile.parents):
        if ancestor.is_symlink():
            raise StorageHealthError('Private research storage contains a link. Technical security review is required before dispatch.')
    count = 0

    def check(path):
        nonlocal count
        info = path.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)) or info.st_uid != os.getuid():
            raise StorageHealthError('Private research storage has an unexpected owner or object. Technical security review is required before dispatch.')
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise StorageHealthError('Private research storage contains linked files. Technical security review is required before dispatch.')
        if any(name.startswith('system.posix_acl_') for name in os.listxattr(path, follow_symlinks=False)):
            raise StorageHealthError('Private research storage has additional access grants. Technical security review is required before dispatch.')
        if info.st_mode & 0o077:
            raise StorageHealthError('Private research storage permissions need owner-local maintenance before dispatch. Saved requests are retained. Repair the reported storage defect, then review the approved profile reference and retry without submitting duplicate research.')
        count += 1

    try:
        if not profile.is_dir() or not root.is_dir():
            raise StorageHealthError('Approved profile storage is unavailable. Restore its existing location before dispatch.')
        check(root)
        paths = [root / name for name in OWNED if (root / name).exists() or (root / name).is_symlink()] if root != profile else [profile]
        def unreadable(error):
            raise error

        for path in paths:
            check(path)
            for base, directories, files in os.walk(path, followlinks=False, onerror=unreadable):
                for name in directories + files:
                    check(Path(base) / name)
        return {'state': 'ready', 'objects_checked': count}
    except OSError:
        raise StorageHealthError('Private research storage cannot be checked. Restore local access before dispatch; your saved request is retained.') from None
