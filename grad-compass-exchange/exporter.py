"""Manual publisher for the bundled invented fixture only.

No path or data-source argument is accepted. This module never reads the research
engine, application database, or a private registry.
"""

import argparse
import ctypes
import errno
import os
from pathlib import Path
import shutil
import tempfile

from jsonschema import ValidationError

from contract import ROOT, FILES, validate_batch


FIXTURE = ROOT / "examples" / "batch-66666666-6666-4666-8666-666666666666"


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_synced(path, data):
    with open(path, "xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def _rename_no_replace(source, destination):
    """Linux atomic directory publish; fail closed if unavailable."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "atomic no-replace rename unavailable")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(destination))


def _same_batch(left, right):
    try:
        validate_batch(left)
        validate_batch(right)
        return all((left / name).read_bytes() == (right / name).read_bytes()
                   for name in (*FILES, "manifest.json"))
    except (OSError, ValueError, KeyError, ValidationError):
        return False


def publish_synthetic_fixture(outbox, *, before_publish=None):
    """Publish the bundled invented batch; an identical replay is a no-op.

    ``before_publish`` is a test fault hook, called after all staging fsyncs.
    """
    manifest, _, _ = validate_batch(FIXTURE)
    outbox = Path(outbox)
    if outbox.is_symlink() or not outbox.is_dir():
        raise ValueError("outbox must be an existing real directory")
    destination = outbox / f'batch-{manifest["batch_id"]}'
    if destination.exists() or destination.is_symlink():
        if _same_batch(FIXTURE, destination):
            return destination
        raise FileExistsError("batch ID already published with different or invalid bytes")

    staging = Path(tempfile.mkdtemp(prefix=".stage-", dir=outbox))
    try:
        for name in FILES:
            _write_synced(staging / name, (FIXTURE / name).read_bytes())
        _fsync_directory(staging)
        # A manifest is the completion marker, so it is written last.
        _write_synced(staging / "manifest.json", (FIXTURE / "manifest.json").read_bytes())
        _fsync_directory(staging)
        validate_batch(staging)
        if before_publish is not None:
            before_publish()
        try:
            _rename_no_replace(staging, destination)
        except FileExistsError:
            if _same_batch(FIXTURE, destination):
                return destination
            raise FileExistsError("batch ID already published with different or invalid bytes")
        _fsync_directory(outbox)
        return destination
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manually publish the bundled synthetic exchange fixture")
    parser.add_argument("outbox", type=Path, help="existing output directory on one filesystem")
    args = parser.parse_args()
    print(publish_synthetic_fixture(args.outbox))
