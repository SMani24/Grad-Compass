"""Small profile-local layout preference; independent from research envelopes."""
from contextlib import closing
from web.local import regular,atomic_json
from web import research_envelopes as env

DEFAULTS={'left':300,'right':350}


def preferences(workspace,value=None):
    with workspace.state_lock,closing(workspace.connect()):
        path=regular(workspace.directory/'panel-widths.json')
        if value is None:
            if not path.exists():return dict(DEFAULTS)
            value=env.loads(path.read_bytes())
            write=False
        else:write=True
        if not isinstance(value,dict) or set(value)!=set(DEFAULTS) or any(type(v) is not int or not 260<=v<=720 for v in value.values()):
            raise ValueError('Panel widths must be whole pixels from 260 to 720')
        if write:atomic_json(path,value)
        return dict(value)
