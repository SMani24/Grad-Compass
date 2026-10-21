"""Data-driven, offline country visuals for screen and print."""
import hashlib
import json
from pathlib import Path

STATIC=Path(__file__).parent/'assets'


def country_name(code):
    from web.country_evidence import ALIASES
    geometry=json.loads((Path(__file__).resolve().parents[1]/'ui/data/countries.geo.json').read_text())
    for feature in geometry['features']:
        p=feature['properties']
        if p.get('ISO3166-1-Alpha-3')==code or ALIASES.get(p['name'])==code:return p['name']
    return code


def attach(workspace,report):
    static=json.loads((STATIC/'countries.json').read_text()).get(report['metadata']['country_code'],{})
    def shipped(asset):
        value=dict(asset);path=STATIC/Path(asset['path']).name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=asset['sha256']:return None
        value['_local_path']=str(path)
        return value
    visuals={}
    if static:
        for kind,asset in [('photo',static),('flag',static.get('flag')),('locator',static.get('locator'))]:
            if asset and (kind!='locator' or asset.get('review',{}).get('state') in ('pass','accepted')):
                value=shipped({k:v for k,v in asset.items() if k not in ('flag','locator')})
                if value:visuals[kind]=value
    for kind,asset in report.get('assets',{}).items():
        value=dict(asset);value['_local_path']=str(workspace.directory/'report-cache'/report['key']/report['edition']/'assets'/asset['sha256'])
        value['path']='/api/reports/'+report['key']+'/asset/'+asset['sha256']+'?edition='+report['edition'];visuals[kind]=value
    report['visuals']=visuals;report['country_name']=country_name(report['metadata']['country_code'])
    return report
