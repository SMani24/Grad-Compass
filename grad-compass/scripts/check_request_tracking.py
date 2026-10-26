"""Normal-desktop request journey. Invented transport or read-only owner evidence."""
import argparse,hashlib,json,os,sys,threading,time,traceback
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4
APP=Path(__file__).resolve().parents[1];sys.path[:0]=[str(APP),str(APP/'scripts'),str(APP/'tests')]
from web.local import atomic_json,private_directory,create_local_server
from web.profiles import LocalProfiles
from web.dispatch import Dispatch
from web.request_tracking import RequestTracker
from web import research_envelopes as env


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--screenshots',type=Path,required=True);parser.add_argument('--restart',action='store_true');parser.add_argument('--owner',action='store_true');parser.add_argument('--request-id');args=parser.parse_args()
    runtime=args.runtime.absolute();out=private_directory(args.screenshots);fake_server=None;fake=None
    if args.owner:
        profiles=LocalProfiles(runtime)
        assert next(x['name'] for x in profiles.snapshot()['profiles'] if x['id']==profiles.snapshot()['active_id'])=='Main-Apply'
    else:
        marker=runtime/'.request-tracking-test'
        if runtime.exists() and not marker.is_file():raise SystemExit('Refusing unmarked test storage')
        private_directory(runtime);marker.touch(mode=0o600);profiles=LocalProfiles(runtime);w=profiles.workspace
        path=runtime/'fake-paperclip.local.json'
        fake=json.loads(path.read_text()) if path.exists() else {'company':str(uuid4()),'agent':str(uuid4()),'online':True,'phase':'running','run':str(uuid4()),'creates':0,'tasks':{},'updated':env.now()}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,value,status=200):
                body=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def do_GET(self):
                if not fake['online']:return self.reply({'error':'Invented offline state'},503)
                if '/companies/' in self.path:return self.reply(list(fake['tasks'].values()) if '/issues?' in self.path else {'id':fake['company']})
                task=next(iter(fake['tasks'].values()));root='/api/issues/'+task['id'];execution={'runId':fake['run'],'agentId':fake['agent'],'execution':{'phase':fake['phase'],'label':fake['phase'],'lastConfirmedActivityAt':fake['updated'],'attempt':3 if fake['phase']=='failed' else 1,'maxAttempts':3,'permittedActions':['inspect_run']},'recoveryAction':{'id':fake['run'],'kind':'stranded_assigned_issue','ownerType':'board','nextAction':'Repair the fixture runtime, then explicitly recover this same task.'} if fake['phase']=='failed' else None}
                if self.path==root:return self.reply({**task,'updatedAt':fake['updated'],'blockedBy':[],'status':{'failed':'blocked','running':'in_progress','completed':'done'}[fake['phase']]})
                if self.path==root+'/execution':return self.reply(execution)
                if self.path==root+'/runs':return self.reply([{'runId':fake['run'],'contextIssueId':task['id'],'agentId':fake['agent'],'status':fake['phase']}])
                if self.path==root+'/comments':return self.reply([{'authorType':'system','metadata':{'sourceRunId':fake['run'],'sections':[{'rows':[{'label':'Failure summary','value':'Not inside a trusted directory and --skip-git-repo-check was not specified.'}]}]}}] if fake['phase']=='failed' else [])
                return self.reply({},404)
            def do_POST(self):
                value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path!='/api/companies/'+fake['company']+'/issues':return self.reply({'error':'No execution action is available in this fixture'},409)
                key=value['idempotencyKey']
                if key not in fake['tasks']:
                    fake['creates']+=1;fake['tasks'][key]={'id':str(uuid4()),'companyId':fake['company'],'assigneeAgentId':fake['agent'],'identifier':'FIXTURE-1','status':'todo','description':value['description'],'title':'Prepare an invented country report'}
                    atomic_json(path,fake)
                self.reply(fake['tasks'][key])
        fake_server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=fake_server.serve_forever,daemon=True).start()
        frozen=private_directory(runtime/'invented-approved');content=b'{"fixture":"no applicant content"}'
        if not (frozen/'receipt.json').exists():
            (frozen/'profile.json').write_bytes(content);(frozen/'COMPLETE').write_text('complete');atomic_json(frozen/'receipt.json',{'profile_id':str(uuid4()),'revision_id':str(uuid4()),'sha256':hashlib.sha256(content).hexdigest(),'receipt_id':str(uuid4()),'approved_at':env.now(),'decision':'accepted','actor_type':'human','reliable_for_discovery':True})
        atomic_json(w.directory/'paperclip-connection.local.json',{'url':'http://127.0.0.1:'+str(fake_server.server_port),'company_id':fake['company'],'dave_id':fake['agent'],'approved_profile_directory':str(frozen),'atomic_idempotency':True})
        if not fake['tasks']:
            from test_local import LocalTests
            f=object.__new__(LocalTests);entry=Dispatch(w).prepare(f.submission(countries=['CAN'],scope='country_conditions',bounds={'institutions':0,'programs':0}));receipt=Dispatch(w).confirm(entry['id'],entry['confirmation_digest']);fake['request']=receipt['request']['id'];atomic_json(path,fake)
    w=profiles.workspace;personal=('country-decisions.json','report-annotations.json','report-reading.json','research-selection.json','panel-widths.json','display-preferences.json','dispatch-outbox.json')
    def inventory():return {n:(hashlib.sha256((w.directory/n).read_bytes()).hexdigest(),(w.directory/n).stat().st_mtime_ns) if (w.directory/n).exists() else None for n in personal}
    before=inventory();research=w.research.snapshot();owner_id=profiles.snapshot()['active_id']
    protected={str(p.relative_to(w.directory)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for folder in ('reports','inbox','research-handoff') for p in (w.directory/folder).rglob('*') if p.is_file()} if args.owner else {}
    server=create_local_server(w,profiles=profiles);threading.Thread(target=server.serve_forever,daemon=True).start()
    os.environ['QT_API']='pyqt6';os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from preview_capture import PreviewCapture
    window=webview.create_window('Grad Compass' if args.owner else 'Grad Compass — isolated request check',f'http://127.0.0.1:{server.server_port}/',width=1440,height=1000,min_size=(390,640));capture=PreviewCapture(window,out,prefix=('owner-' if args.owner else 'fixture-')+('restart-' if args.restart else ''));passed=[]
    watchdog=threading.Timer(240,lambda:os._exit(1));watchdog.daemon=True;watchdog.start()
    def work():
        def js(code):return window.run_js(code)
        def wait(code):
            until=time.monotonic()+30
            while time.monotonic()<until:
                value=js(code)
                if value:return value
                time.sleep(.15)
            raise AssertionError((code,js("document.getElementById('requests-status')?.textContent")))
        def click(id):js('setTimeout(()=>document.getElementById('+json.dumps(id)+')?.click(),0);void 0')
        def shot(name):time.sleep(.7);capture.save(name)
        def set_filter(value):js("document.getElementById('requests-filter').value="+json.dumps(value)+";document.getElementById('requests-filter').dispatchEvent(new Event('change'))")
        def remote_refresh():
            RequestTracker(w).refresh();js('window.GradCompassRequests.read();void 0');time.sleep(.5)
        try:
            window.events.loaded.wait(25);wait("!document.getElementById('open-requests').hidden")
            if args.owner:
                wait("!document.getElementById('requests-notification').hidden");shot('map-failure-notice');click('open-requests');wait("document.getElementById('requests-dialog').open && !!document.querySelector('.tracked-request[data-status=failed]')");shot('all-requests')
                failed=args.request_id or js("document.querySelector('.tracked-request[data-status=failed]').dataset.request");r=next(r for r in RequestTracker(w).snapshot()['requests'] if r['request_id']==failed)
                assert r['status']=='failed' and r['notice']
                set_filter('pending');wait("document.getElementById('requests-list').textContent.includes('No requests match')");shot('pending-filter');set_filter('attention');wait("!!document.querySelector('.tracked-request[data-status=failed]')");shot('failed-request-and-recovery')
                assert js("[...document.querySelectorAll('.tracked-request[data-status=failed] a')].some(a=>a.textContent.includes('recover') && a.href.includes("+json.dumps(r['tracking']['latest']['step']['identifier'])+"))")
                assert not js("[...document.querySelectorAll('.tracked-request[data-status=failed] button')].some(b=>/Edit|Cancel|retry/.test(b.textContent))")
                js("[...document.querySelectorAll('.tracked-request[data-status=failed] button')].find(b=>b.textContent==='View saved request').click()")
                wait("!!document.getElementById('open-request-progress')")
                assert not js("!!document.getElementById('prepare-research-handoff')")
                shot('saved-request-status-link');click('open-request-progress');wait("document.getElementById('requests-dialog').open")
                assert inventory()==before and w.research.snapshot()==research
                assert all((hashlib.sha256((w.directory/name).read_bytes()).hexdigest(),(w.directory/name).stat().st_mtime_ns)==value for name,value in protected.items())
                result={'passed':True,'profile':owner_id,'observed_request':failed,'countries':r['countries'],'task':r['task'],'status':r['status'],'step':r['tracking']['latest']['step'],'run':r['tracking']['latest']['run'],'connection_error':r['tracking'].get('connection_error'),'owner_overlay_bytes_and_mtimes_unchanged':True,'research_unchanged':True,'protected_original_files':len(protected),'protected_original_bytes_and_mtimes_unchanged':True,'real_agents_invoked':False}
            else:
                identity=fake['request'];click('open-requests');wait("!!document.querySelector('.tracked-request[data-request=\""+identity+"\"]')")
                if not args.restart:
                    assert fake['creates']==1;fake['phase']='failed';fake['updated']=env.now();remote_refresh();wait("!!document.querySelector('.tracked-request[data-status=failed]')");shot('later-agent-failure')
                    fake['online']=False;remote_refresh();wait("!!document.querySelector('.request-connection-notice')");shot('unavailable-last-known-state');click('close-requests');wait("!document.getElementById('requests-notification').hidden");shot('persistent-map-notice')
                else:
                    wait("!!document.querySelector('.tracked-request[data-status=failed]') && !!document.querySelector('.request-connection-notice')");shot('failure-persists-offline')
                    fake['online']=True;fake['phase']='running';fake['run']=str(uuid4());fake['updated']=env.now();remote_refresh();wait("!!document.querySelector('.tracked-request[data-status=active]')")
                    from test_local import LocalTests
                    case=object.__new__(LocalTests);case.root=private_directory(runtime/'fixture-build');case.workspace=w;case.store=w.research;case.request=w.research.request(identity)['request']
                    atomic_json(w.directory/'inbox/fixture-ack.json',env.packet(case.ack()))
                    finding=case.country();finding['sources']=[{'source_id':str(uuid4()),'source_revision':'fixture-r1','source_url':'https://example.invalid/evidence','locator':'Invented evidence','observed_at':env.now()}];value=case.result();value['findings']=[finding];atomic_json(w.directory/'inbox/fixture-result.json',env.packet(value))
                    wait("document.querySelector('.tracked-request').textContent.includes('1 received result revision')")
                    saved=w.research.request(identity)['results'][0]['envelope'];from report_fixtures import package
                    root,meta=package(case,saved,code='CAN');from web.report_delivery import publish
                    publish(w,root)
                    notice=next((w.directory/'inbox').glob('report-*.json'));body=env.loads(env.loads(notice.read_bytes())['body']);metadata=w.directory/body['metadata_path'];original=metadata.read_bytes();metadata.unlink()
                    from web.inbox import receiver_for
                    receiver_for(w).check();js('window.GradCompassRequests.read();void 0');wait("!!document.querySelector('.tracked-request .request-persistent-notice')");shot('delivery-error')
                    metadata.write_bytes(original);receiver_for(w).check();fake['phase']='completed';fake['updated']=env.now();remote_refresh();wait("!!document.querySelector('.tracked-request[data-status=complete]')");shot('report-received')
                    assert fake['creates']==1;assert len(w.research.request(identity)['results'])==1
                    assert not receiver_for(w).check()['errors'];assert any(x.get('kind')=='delivery' for x in RequestTracker(w).read()['requests'][identity]['history'])
                result={'passed':True,'profile':owner_id,'request_id':identity,'fake_tasks':fake['creates'],'real_agents_invoked':False,'phase':fake['phase'],'status':next(r['status'] for r in RequestTracker(w).snapshot()['requests'] if r['request_id']==identity)}
                atomic_json(path,fake)
            if not dialog_open(js):click('open-requests');wait("document.getElementById('requests-dialog').open")
            window.resize(390,740);wait('innerWidth===390');js("document.documentElement.style.setProperty('--text-scale',1.5)");time.sleep(.5);assert js('document.body.scrollWidth<=innerWidth');assert js("document.getElementById('requests-dialog').scrollWidth<=document.getElementById('requests-dialog').clientWidth");shot('narrow-large-requests')
            click('close-requests');wait("!document.getElementById('requests-dialog').open");window.resize(1440,1000)
            atomic_json(out/('restart.local.json' if args.restart else 'normal.local.json'),result);passed.append(True);print('Normal desktop request tracking passed.',flush=True)
        except Exception:traceback.print_exc();shot('failure')
        finally:watchdog.cancel();window.confirm_close=False;window.destroy()
    try:webview.start(work,gui='qt',private_mode=True,storage_path=str(out/'browser'))
    finally:
        server.shutdown();server.server_close()
        if fake_server:fake_server.shutdown();fake_server.server_close()
    assert passed,'Native request tracking verification failed'


def dialog_open(js):return js("document.getElementById('requests-dialog').open")


if __name__=='__main__':main()
