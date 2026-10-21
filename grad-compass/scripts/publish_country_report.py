"""Publish a finalized country package for an existing saved request; no agent execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from web.local import LocalWorkspace,regular
from web import research_envelopes as env
from web.report_delivery import publish


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--handoff',required=True,type=Path);parser.add_argument('--package',required=True,type=Path);parser.add_argument('--check',action='store_true',help='validate only; publish no finalized files or notice');args=parser.parse_args()
    handoff=args.handoff.absolute()
    if handoff.parent.name!='research-handoff' or handoff.name.endswith('.ref.json'):raise ValueError('Use the exported saved request handoff')
    raw=regular(handoff).read_bytes();request=env.loads(raw);reference=env.loads(regular(handoff.with_suffix('.ref.json')).read_bytes())
    workspace=LocalWorkspace(handoff.parent.parent);saved=workspace.research.request(request['request_id'])['request']
    if reference!={'file':handoff.name,'sha256':hashlib.sha256(raw).hexdigest(),'synthetic':False} or raw!=saved['_transport']['body'].encode():raise ValueError('Saved request handoff exact bytes mismatch')
    meta=env.loads(regular(args.package/'metadata.local.json').read_bytes())
    if meta['request']['id']!=saved['request_id']:raise ValueError('Package belongs to a different saved request')
    print(json.dumps(publish(workspace,args.package,check_only=args.check)))


if __name__=='__main__':main()
