"""Native ordinary workflow check in a marked invented profile. Never invokes Dave."""
import argparse,json,os,sys,threading,time,traceback
from pathlib import Path
from uuid import uuid4
APP=Path(__file__).resolve().parents[1];sys.path[:0]=[str(APP),str(APP/'scripts'),str(APP/'tests')]
from web.local import LocalWorkspace,create_local_server,private_directory,atomic_json
from web.profiles import LocalProfiles
from web import dispatch
from web.export_preferences import preference,destination
from web import report_packages as reports


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--screenshots',type=Path,required=True);parser.add_argument('--restart',action='store_true');args=parser.parse_args()
    runtime=args.runtime.absolute();marker=runtime/'.ordinary-workflow-test'
    if runtime.exists() and not marker.is_file():raise SystemExit('Refusing unmarked storage')
    private_directory(runtime);marker.touch(mode=0o600)
    output=private_directory(args.screenshots);profiles=LocalProfiles(runtime);w=profiles.workspace
    frozen=private_directory(runtime/'invented-profile');profile=frozen/'profile.json'
    if not profile.exists():
        profile.write_bytes(b'{"fixture":"invented"}');(frozen/'COMPLETE').write_text('complete')
        import hashlib
        atomic_json(frozen/'receipt.json',{'profile_id':str(uuid4()),'revision_id':str(uuid4()),'sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),'receipt_id':str(uuid4()),'approved_at':'2026-10-25T00:00:00Z','decision':'accepted','actor_type':'human','reliable_for_discovery':True})
        atomic_json(runtime/'paperclip-connection.local.json',{'url':'http://127.0.0.1:1','company_id':str(uuid4()),'dave_id':str(uuid4()),'approved_profile_directory':str(frozen),'atomic_idempotency':True})
    conf=dispatch.config(w);fakefile=runtime/'fake-paperclip.local.json';fake=json.loads(fakefile.read_text()) if fakefile.exists() else {'online':False,'tasks':{},'creates':0,'lose_ack':False}
    class FakePaperclip:
        def __init__(self,connection):pass
        def available(self):
            if not fake['online']:raise OSError('invented offline')
            return {'id':conf['company_id']}
        def reconcile(self,marker):return next((x for x in fake['tasks'].values() if marker in x['description']),None)
        def create(self,payload):
            key=payload['idempotencyKey']
            if key not in fake['tasks']:
                fake['creates']+=1;fake['tasks'][key]={'id':str(uuid4()),'identifier':'FIXTURE-'+str(fake['creates']),'status':'todo','description':payload['description'],'companyId':conf['company_id'],'assigneeAgentId':conf['dave_id']};atomic_json(fakefile,fake)
            if fake['lose_ack']:fake['lose_ack']=False;atomic_json(fakefile,fake);raise OSError('invented lost acknowledgement')
            return fake['tasks'][key]
    dispatch.Paperclip=FakePaperclip
    downloads=private_directory(runtime/'user-exports');chosen=private_directory(runtime/'chosen-exports')
    if not args.restart:preference(w,str(downloads))
    if not (runtime/'fixture-report-key.local.json').exists():
        from test_local import LocalTests
        from report_fixtures import receive_country,package
        case=object.__new__(LocalTests);case.root=private_directory(runtime/'fixture-build');case.workspace=w;case.store=w.research
        result=receive_country(case,code='CHL');root,meta=package(case,result,code='CHL')
        from PIL import Image
        photo=root/'photo.jpg';Image.new('RGB',(800,500),(23,86,107)).save(photo)
        meta['assets']=[{'kind':'photo','relative_path':'photo.jpg','sha256':reports.digest(photo.read_bytes()),'media_type':'image/jpeg','caption':'Invented fixture image; no real location claim','alt':'Invented teal fixture','credit':'Fixture author','creator':'Fixture author','license':'Fixture permission','license_url':'https://example.invalid/license','source_url':'https://example.invalid/photo','crop':{'x':.5,'y':.5}}];meta['asset_delivery']={'state':'available'};atomic_json(root/'metadata.local.json',meta)
        from web.report_delivery import publish
        publish(w,root)
        from web.inbox import InboxReceiver
        assert not InboxReceiver(w,quiet_seconds=0).check()['errors']
        atomic_json(runtime/'fixture-report-key.local.json',{'request':case.request['request_id']})
    os.environ['QT_API']='pyqt6';os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    from desktop_exports import DesktopExports
    from desktop_downloads import DesktopDownloads
    from preview_capture import PreviewCapture
    from unittest.mock import patch
    exports=DesktopExports();server=create_local_server(w,profiles=profiles,desktop_exports=exports);threading.Thread(target=server.serve_forever,daemon=True).start()
    import webview
    window=webview.create_window('Grad Compass — isolated ordinary workflow',f'http://127.0.0.1:{server.server_port}/',width=1440,height=1000,min_size=(390,640));capture=PreviewCapture(window,output,prefix='ordinary-'+('restart-' if args.restart else ''))
    names=[]
    def target(name):
        path=destination(profiles.workspace,name);names.append(str(path));return str(path)
    handler=DesktopDownloads(window,choose_path=target,workspace=lambda:profiles.workspace);passed=[]
    watchdog=threading.Timer(240,lambda:os._exit(1));watchdog.daemon=True;watchdog.start()
    def work():
        def js(code):return window.run_js(code)
        def wait(code):
            until=time.monotonic()+30
            while time.monotonic()<until:
                value=js(code)
                if value:return value
                time.sleep(.1)
            raise AssertionError((code,js("document.getElementById('request-form-status')?.textContent")))
        def click(id):js('setTimeout(()=>document.getElementById('+json.dumps(id)+')?.click(),0);void 0')
        def choose(id,value):js('document.getElementById('+json.dumps(id)+').value='+json.dumps(value)+';document.getElementById('+json.dumps(id)+').dispatchEvent(new Event("change"))')
        def search(text):js('document.getElementById("search").value='+json.dumps(text)+';document.getElementById("search").dispatchEvent(new Event("input"))')
        def polygon(code):js('document.querySelector(\'.country-outline[data-country="'+code+'"]\').dispatchEvent(new MouseEvent("click",{bubbles:true}))')
        def shot(name):time.sleep(.6);capture.save(name)
        try:
            handler.install_requested.emit();assert handler.installed.wait(10);window.events.loaded.wait(25);wait('!!window.GradCompassWorkspace?.operational && !!window.GradCompassDispatch');wait("!document.getElementById('open-pending-requests').hidden")
            if not args.restart:
                before=len(w.research.snapshot()['requests']);click('countries-mode');search('France');click('select-countries');click('map-select-matching');wait("document.getElementById('country-selection-count').textContent==='1 selected'")
                click('save-selected-countries');wait("window.GradCompassResearch.personal('FRA').watched");assert len(w.research.snapshot()['requests'])==before;click('done-selecting-countries');wait("document.querySelector('.country-outline[data-country=FRA]').getAttribute('stroke-dasharray')==='2 2'");shot('saved-country-map')
                click('select-countries');click('map-select-matching');polygon('CAN');wait("document.getElementById('country-selection-count').textContent==='2 selected'");shot('map-selection')
                click('research-map-selection');wait("document.getElementById('request-dialog').open");assert set(json.loads(js("document.getElementById('request-countries').dataset.countryCodes")))=={'FRA','CAN'}
                click('request-submit');wait("document.getElementById('dispatch-confirm-dialog').open");shot('confirmation');click('dispatch-confirm-cancel');wait("!document.getElementById('dispatch-confirm-dialog').open");assert fake['creates']==0 and len(w.research.snapshot()['requests'])==before
                click('request-submit');wait("document.getElementById('dispatch-confirm-dialog').open");click('dispatch-confirm');wait("!document.getElementById('dispatch-confirm-dialog').open && document.getElementById('research-dialog').open");wait("document.getElementById('research-message').textContent.includes('saved')");assert fake['creates']==0
                pending=next(x for x in dispatch.Dispatch(w).snapshot()['entries'] if x['status']=='pending');assert set(pending['payload']['countries'])=={'FRA','CAN'}
                click('close-research');click('open-pending-requests');wait("document.getElementById('requests-dialog').open");shot('offline-pending')
                fake['online']=True;fake['lose_ack']=True;time.sleep(.3);assert fake['creates']==0
                js("[...document.querySelectorAll('#requests-list button')].find(b=>b.textContent==='Review dispatch / retry').click()");wait("document.getElementById('dispatch-confirm-dialog').open");click('dispatch-confirm');wait("!document.getElementById('dispatch-confirm-dialog').open && document.getElementById('research-dialog').open");assert fake['creates']==1
                click('close-research');click('open-pending-requests');wait("document.getElementById('requests-dialog').open");js("[...document.querySelectorAll('#requests-list button')].find(b=>b.textContent==='Review dispatch / retry').click()");wait("document.getElementById('dispatch-confirm-dialog').open");click('dispatch-confirm');wait("document.getElementById('research-message').textContent.includes('FIXTURE-1')");assert fake['creates']==1;shot('reconciled-task');click('close-research')
                click('open-settings');wait("document.getElementById('export-folder').textContent.includes('user-exports')")
                with patch('desktop_exports.QFileDialog.getExistingDirectory',return_value=str(chosen)):
                    click('change-export-folder');wait("document.getElementById('export-folder').textContent.includes('chosen-exports')")
                shot('export-folder');click('close-settings')
            else:
                assert len(fake['tasks'])==fake['creates']==1
                wait("window.GradCompassResearch.personal('FRA').watched")
                click('open-settings');wait("document.getElementById('export-folder').textContent.includes('chosen-exports')");shot('export-folder-persisted');click('close-settings')
                assert any(x['status']=='accepted' for x in dispatch.Dispatch(w).snapshot()['entries'])
            # Whole catalogue, filtered scope, individual exclusion and exact draft.
            click('countries-mode');search('');choose('country-list-scope','all')
            if js("document.getElementById('select-countries').getAttribute('aria-pressed')==='true'"):click('done-selecting-countries')
            click('select-countries');click('map-select-matching');total=js("Number(document.getElementById('country-selection-count').textContent.split(' ')[0])");assert total>170
            polygon('CAN');assert js("Number(document.getElementById('country-selection-count').textContent.split(' ')[0])")==total-1
            click('research-map-selection');wait("document.getElementById('request-dialog').open");scope=json.loads(js("document.getElementById('request-countries').dataset.countryCodes"));assert len(scope)==total-1 and 'CAN' not in scope;assert js("document.getElementById('request-submit').disabled");shot('whole-catalogue-draft');click('cancel-request');click('clear-selected-countries');click('done-selecting-countries')
            # Shared unconfigured-country reader and native user exports.
            search('Chile');wait("!!document.querySelector('.country-card[data-country=CHL]')");js("document.querySelector('.country-card[data-country=CHL]').click()");wait("!!document.getElementById('read-country-report')");click('read-country-report');wait("document.querySelector('.canonical-report')?.dataset.country==='CHL' && document.querySelector('.report-photo img')?.naturalWidth>0");shot('unconfigured-country-reader')
            js("document.getElementById('reader-export-options').open=true");old=len(names);click('reader-download-pdf');wait('true')
            until=time.monotonic()+30
            while time.monotonic()<until and (len(names)==old or not Path(names[-1]).exists()):time.sleep(.1)
            assert len(names)>old and Path(names[-1]).is_file() and str(chosen) in names[-1]
            old=len(names);click('reader-download-markdown');until=time.monotonic()+30
            while time.monotonic()<until and (len(names)==old or not Path(names[-1]).exists()):time.sleep(.1)
            assert len(names)>old and Path(names[-1]).is_file();click('close-research')
            window.resize(390,740);wait('innerWidth===390');js("document.documentElement.style.setProperty('--text-scale',1.5)");click('select-countries');time.sleep(.7);assert js('document.body.scrollWidth<=innerWidth');shot('narrow-map-selection');click('country-selection-list');wait("document.getElementById('country-selection-dialog').open");assert js("document.getElementById('country-selection-dialog').scrollWidth<=document.getElementById('country-selection-dialog').clientWidth");shot('narrow-list-alternative')
            atomic_json(output/('restart.local.json' if args.restart else 'normal.local.json'),{'passed':True,'real_agents_invoked':False,'fake_tasks':fake['creates'],'downloads':names,'whole_catalogue_size':total,'exact_scope_size':len(scope),'profile':profiles.snapshot()['active_id']})
            atomic_json(fakefile,fake);passed.append(True);print('Native ordinary workflow passed: exact map scope, explicit confirmation/cancel, offline queue/reconciliation, photo reader and native exports.',flush=True)
        except Exception:traceback.print_exc();shot('failure')
        finally:watchdog.cancel();window.confirm_close=False;window.destroy()
    try:webview.start(work,gui='qt',private_mode=True,storage_path=str(runtime/'browser'))
    finally:server.shutdown();server.server_close()
    assert passed,'Ordinary workflow native check failed'


if __name__=='__main__':main()
