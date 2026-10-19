"""Publish a completed producer response to its saved request's private inbox.

This command only delivers an existing response. It never invokes an agent or
changes factual review or approval state.
"""
import argparse
import os
from pathlib import Path
import stat
import sys
from uuid import uuid4

APP = Path(__file__).resolve().parents[2] / 'grad-compass'
sys.path.insert(0, str(APP))
from web import research_envelopes as env
from web.local import LocalWorkspace, private_directory


def read_regular(path, limit):
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('Private response paths cannot use symbolic links')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
        raise ValueError('Use a bounded, unlinked regular file')
    raw = path.read_bytes()
    if path.stat() != info:
        raise ValueError('The private file changed while being read')
    return raw


def publish(handoff, response):
    handoff = Path(handoff).absolute()
    if handoff.parent.name != 'research-handoff' or not handoff.name.startswith('request-') or handoff.suffix != '.json' or handoff.name.endswith('.ref.json'):
        raise ValueError('Choose an exported request in research-handoff')
    workspace_root = handoff.parent.parent
    if not (workspace_root / 'grad_compass.db').is_file() or not (workspace_root / 'research.sqlite').is_file():
        raise ValueError('The saved local workspace is missing')
    request_raw = read_regular(handoff, 4_000_000)
    reference = env.loads(read_regular(handoff.with_suffix('.ref.json'), 8192))
    if not isinstance(reference, dict) or reference != {
        'file': handoff.name,
        'sha256': __import__('hashlib').sha256(request_raw).hexdigest(),
        'synthetic': False,
    }:
        raise ValueError('The exported request reference does not match its bytes')
    request = env.loads(request_raw)
    workspace = LocalWorkspace(workspace_root)
    saved = workspace.research.request(request.get('request_id'))['request']
    if request_raw != saved['_transport']['body'].encode('utf-8') or saved['request_id'] != handoff.stem.removeprefix('request-'):
        raise ValueError('The exported request does not match the saved request')
    response_raw = read_regular(response, 8_000_000)
    packet = env.loads(response_raw)
    value = workspace.research._validate_response(packet)
    if value['request_id'] != saved['request_id']:
        raise ValueError('The response belongs to a different saved request')
    kind = value['envelope_kind']
    revision = 'ack' if kind == 'acknowledgement' else str(value['revision'])
    inbox = private_directory(workspace_root / 'inbox')
    name = f"response-{saved['request_id']}-{kind}-{revision}-{packet['sha256']}.json"
    target = inbox / name
    if target.exists():
        if read_regular(target, 8_000_000) != response_raw:
            raise ValueError('A finalized response filename has different bytes')
        return target, False
    temporary = inbox / ('.tmp-' + str(uuid4()))
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(response_raw)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, target, follow_symlinks=False)
        except FileExistsError:
            if read_regular(target, 8_000_000) != response_raw:
                raise ValueError('A finalized response filename has different bytes')
            return target, False
        directory = os.open(inbox, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return target, True
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', type=Path, required=True, help='exact exported request-UUID.json')
    parser.add_argument('--response', type=Path, required=True, help='completed {body, sha256} JSON transport')
    args = parser.parse_args()
    target, created = publish(args.handoff, args.response)
    print(('Published' if created else 'Already published') + ': ' + str(target))


if __name__ == '__main__':
    main()
