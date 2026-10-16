"""Verify and restore a private backup into a new workspace; never overwrite current data."""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4
from core.paths import validate_data_directory
from web import research_envelopes as env
from web.local import LocalWorkspace,LOCAL_MARKER,RESEARCH_MARKER,regular,private_directory


def restore_backup(source,destination):
    source=Path(source)
    if any(p.is_symlink() for p in (source,*source.parents)):raise ValueError('Use your private, unlinked backup')
    source=source.resolve()
    destination=Path(destination)
    if any(p.is_symlink() for p in (destination,*destination.parents)):raise ValueError('Recovery destination cannot use links')
    destination=validate_data_directory(destination)
    if destination.exists():raise ValueError('Restore to a new, non-existing workspace; current data is preserved')
    if source.stat().st_uid!=os.getuid() or any(p.is_symlink() for p in (source,*source.parents)):raise ValueError('Use your private, unlinked backup')
    manifest=env.loads(regular(source/'backup.json').read_bytes())
    if manifest.get('schema_version')!='local-backup-1' or not isinstance(manifest.get('sha256'),dict):raise ValueError('Use a complete local backup')
    files=manifest['sha256']
    if not {'grad_compass.db','research.sqlite'}<=set(files):raise ValueError('The backup lacks its workspace databases')
    for name,digest in files.items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or path.as_posix()!=name or name=='backup.json':raise ValueError('Invalid backup filename')
        target=source/path
        if any(p.is_symlink() for p in (target,*target.parents)):raise ValueError('Backup members cannot use links')
        if hashlib.sha256(regular(target).read_bytes()).hexdigest()!=digest:raise ValueError('Backup bytes no longer match the saved inventory')
    for name,table,expected in (('grad_compass.db','app_local_guard',LOCAL_MARKER),('research.sqlite','app_research_guard',RESEARCH_MARKER)):
        with closing(sqlite3.connect((source/name).as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('SELECT marker FROM '+table).fetchall()!=[(expected,)]:raise ValueError('The backup database is invalid or from the wrong scope')
    for name in files:
        if name.endswith('.ref.json'):
            reference=env.loads((source/name).read_bytes());body_path=source/Path(name).with_name(Path(name).name.replace('.ref.json','.json'))
            body=body_path.read_bytes();value=env.loads(body)
            if hashlib.sha256(body).hexdigest()!=reference.get('sha256') or reference.get('synthetic') is not value.get('synthetic'):raise ValueError('Backup handoff reference/scope mismatch')
    if not destination.parent.exists():private_directory(destination.parent)
    temporary=destination.parent/('.recover-'+str(uuid4()))
    private_directory(temporary)
    try:
        for name in files:
            dest=temporary/name;private_directory(dest.parent)
            fd=os.open(dest,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'wb') as output:output.write((source/name).read_bytes())
        os.rename(temporary,destination)
    except BaseException:
        shutil.rmtree(temporary,ignore_errors=True)
        raise
    return LocalWorkspace(destination)
