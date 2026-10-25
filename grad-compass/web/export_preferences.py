"""Profile-local user download destination, separate from managed report caches."""
import os
from pathlib import Path
from web.local import regular,atomic_json
from web import research_envelopes as env


def default_folder():
    # Respect the desktop's XDG Downloads setting without shell expansion.
    config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'user-dirs.dirs'
    download=Path.home()/'Downloads'
    if config.is_file():
        import re
        match=re.search(r'^XDG_DOWNLOAD_DIR="([^"\n]+)"',config.read_text(),re.M)
        if match:
            value=match[1].replace('$HOME',str(Path.home()))
            if Path(value).is_absolute():download=Path(value)
    return download/'GradCompass'


def preference(workspace,folder=None,reset=False):
    with workspace.state_lock:
        path=regular(workspace.directory/'export-preferences.json')
        if reset:
            atomic_json(path,{'folder':None})
        elif folder is not None:
            target=Path(folder)
            if not target.is_absolute() or not target.is_dir() or target.stat().st_uid!=os.getuid() or not os.access(target,os.W_OK|os.X_OK):
                raise ValueError('Choose an existing writable folder owned by you')
            atomic_json(path,{'folder':str(target)})
        saved=env.loads(path.read_bytes()) if path.exists() else {'folder':None}
        if not isinstance(saved,dict) or set(saved)!={'folder'} or saved['folder'] is not None and (not isinstance(saved['folder'],str) or not Path(saved['folder']).is_absolute()):raise ValueError('Invalid export-folder preference')
        folder=Path(saved['folder']) if saved['folder'] else default_folder()
        return {'folder':str(folder),'is_default':saved['folder'] is None,'exists':folder.is_dir()}


def destination(workspace,name):
    folder=Path(preference(workspace)['folder'])
    if not folder.exists():
        if not preference(workspace)['is_default']:raise ValueError('The export folder is missing. Change it in Settings → Exports')
        folder.mkdir(parents=True,exist_ok=True)
    if not folder.is_dir() or folder.stat().st_uid!=os.getuid() or not os.access(folder,os.W_OK|os.X_OK):raise ValueError('The export folder is not writable. Change it in Settings → Exports')
    target=folder/Path(name).name
    count=2
    while target.exists():target=folder/(Path(name).stem+'-'+str(count)+Path(name).suffix);count+=1
    return target
