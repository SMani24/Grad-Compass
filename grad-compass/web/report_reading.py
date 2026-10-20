"""Profile-local reading preferences and exact-version positions, never research state."""
from contextlib import closing
import re
from web.local import atomic_json,regular
from web import research_envelopes as env

DEFAULTS={'width':'comfortable','sidebar_open':True,'positions':{}}


def preferences(workspace,payload=None):
    with workspace.state_lock,closing(workspace.connect()):
        path=regular(workspace.directory/'report-reading.json')
        value=env.loads(path.read_bytes()) if path.exists() else {**DEFAULTS,'positions':{}}
        if payload is not None:
            if not isinstance(payload,dict) or set(payload)-{'width','sidebar_open','position'}:raise ValueError('Choose a reading preference')
            if 'width' in payload:
                if payload['width'] not in ('comfortable','wide'):raise ValueError('Choose Comfortable or Wide')
                value['width']=payload['width']
            if 'sidebar_open' in payload:
                if type(payload['sidebar_open']) is not bool:raise ValueError('Choose whether to show saved requests')
                value['sidebar_open']=payload['sidebar_open']
            if 'position' in payload:
                p=payload['position']
                if not isinstance(p,dict) or not {'key','anchor','offset'}<=set(p)<={'key','anchor','offset','document'} or not isinstance(p['key'],str) or not re.fullmatch('[a-f0-9]{64}',p['key']):raise ValueError('Choose the exact report version')
                from web.report_packages import get
                report=get(workspace,p['key'])
                tree=report['content'];identity=p['key']
                if 'document' in p:
                    from web.report_editions import get as get_edition
                    tree=get_edition(workspace,report,p['document'])['content'];identity+=':'+p['document']
                anchors={'top',*[b['id'] for b in tree['blocks'].values()]}
                if p['anchor'] not in anchors or type(p['offset']) is not int or not -10000<=p['offset']<=10000:raise ValueError('Choose a passage in this report version')
                value['positions'][identity]={'anchor':p['anchor'],'offset':p['offset']}
            atomic_json(path,value)
        return value
