"""Queue a request-bound public original; the normal app downloads and returns its outcome."""
import argparse,hashlib,json
from pathlib import Path
import sys
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from web.local import LocalWorkspace,regular
from web import research_envelopes as env
from web.asset_jobs import enqueue


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff',type=Path,required=True)
    parser.add_argument('--country',required=True);parser.add_argument('--task',required=True);parser.add_argument('--assignee-agent',required=True)
    for field in ('original-url','source-url','license-url','creator','license','caption','alt'):parser.add_argument('--'+field,required=True)
    args=parser.parse_args();handoff=args.handoff.absolute()
    if handoff.parent.name!='research-handoff' or handoff.name.endswith('.ref.json'):raise ValueError('Use the existing saved request handoff')
    raw=regular(handoff).read_bytes();wire=env.loads(raw);ref=env.loads(regular(handoff.with_suffix('.ref.json')).read_bytes())
    workspace=LocalWorkspace(handoff.parent.parent);saved=workspace.research.request(wire['request_id'])['request']
    if ref!={'file':handoff.name,'sha256':hashlib.sha256(raw).hexdigest(),'synthetic':False} or raw!=saved['_transport']['body'].encode():raise ValueError('Exact request handoff mismatch')
    request={'id':saved['request_id'],'revision':saved['revision'],'sha256':saved['digest']}
    asset={field:getattr(args,field) for field in ('original_url','source_url','license_url','creator','license','caption','alt')}
    print(json.dumps(enqueue(workspace,request,args.country,args.task,asset,args.assignee_agent)))


if __name__=='__main__':main()
