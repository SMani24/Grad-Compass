"""Demonstrate profile/removal/reset controls with invented data in temporary storage."""
import argparse
import faulthandler
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback

APP_ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP_ROOT),str(APP_ROOT/'tests'),str(APP_ROOT/'scripts')]
import test_local as fixtures
from web.local import create_local_server,private_directory
from web.profiles import LocalProfiles


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args()
    case=fixtures.LocalTests();case.setUp()
    def timeout():
        faulthandler.dump_traceback();case.doCleanups();os._exit(1)
    watchdog=threading.Timer(180,timeout);watchdog.daemon=True;watchdog.start()
    case.store.save_country({'country_code':'CAN','watched':True,'note':'Preserved invented personal note'})
    case.workspace.country_decisions('CAN','Shortlisted');case.workspace.display_preferences('large')
    case.complete(public=True)
    case.workspace.save_location(case.workspace.overview()['universities'][0]['research']['external_id'],{
        'status':'verified','campus':'Invented test campus','latitude':45,'longitude':-75,
        'source_url':'https://example.invalid/test-location','locator':'Invented QA point','observed_at':'2026-10-16T00:00:00Z',
        'uncertainty':'Invented temporary demonstration coordinate, not a real campus'})
    profiles=LocalProfiles(case.workspace.directory);personal=profiles.snapshot()['active_id']
    before=profiles.workspace.research.snapshot();before_details=profiles.workspace.research.request(case.request['request_id'])
    server=create_local_server(profiles.workspace,profiles=profiles)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    os.environ['QT_API']='pyqt6'
    # An unattended test window must not throttle timers when the IDE has focus.
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS']=' '.join((os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS',''),
        '--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'))
    import webview
    from preview_capture import PreviewCapture
    window=webview.create_window('Grad Compass — Invented profile/reset review',f'http://127.0.0.1:{server.server_port}/',width=1440,height=960,min_size=(390,640))
    screenshots=private_directory(args.screenshots) if args.screenshots else None
    capture=PreviewCapture(window,screenshots,prefix='2026-10-16-profiles-') if screenshots else None
    passed=[]

    def work():
        def run(source):return window.run_js(source)
        def wait(source,check=bool):
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                value=run(source)
                if check(value):return value
                time.sleep(.1)
            raise AssertionError((source,value))
        def click(identity):
            # Let Qt finish its evaluation callback before an HTML modal changes focus.
            run(f'setTimeout(()=>document.getElementById({json.dumps(identity)})?.click(),0);void 0')
            dialogs={'open-settings':('settings-dialog',True),'close-settings':('settings-dialog',False),
                     'cancel-reset':('reset-dialog',False),'close-research':('research-dialog',False),
                     'return-country-selection':('country-selection-dialog',False)}
            if identity in dialogs:
                dialog,opened=dialogs[identity]
                wait(f'document.getElementById({json.dumps(dialog)})?.open=== {str(opened).lower()}')
        def ready(name):
            wait("document.querySelector('#active-profile')?.textContent",lambda text:text=='Profile: '+name)
            wait("!!document.querySelector('.country-card')")
            wait("window.GradCompassResearch?.personal('CAN')!==undefined")
        def shot(name):
            if capture:capture.save(name)
        try:
            window.events.loaded.wait(20);ready('Personal')
            click('universities-mode');wait("document.querySelectorAll('.university-card').length===1")
            assert run("document.querySelectorAll('.leaflet-overlay-pane path[fill=\"#087ba4\"]').length") == 1
            run("document.querySelector('.university-card').click()")
            wait("!!document.getElementById('remove-university')");click('remove-university')
            wait("document.getElementById('local-confirm').open");shot('remove-confirmation')
            run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
            assert not run("document.getElementById('local-confirm').open")
            wait("!document.getElementById('remove-university').disabled")
            assert len(profiles.workspace.overview()['universities'])==1
            click('remove-university');wait("document.getElementById('local-confirm').open");click('local-confirm-accept')
            wait("document.querySelectorAll('.university-card').length===0")
            assert run("document.querySelectorAll('.leaflet-overlay-pane path[fill=\"#087ba4\"]').length") == 0
            assert profiles.workspace.research.request(case.request['request_id'])==before_details
            assert not profiles.workspace.research.receive(before_details['results'][0]['envelope']['_transport'])['changed']
            assert not profiles.workspace.overview()['universities']
            click('open-settings');wait("document.querySelectorAll('[data-restore-university]').length===1")
            run("document.querySelector('[data-restore-university]').closest('details').open=true")
            shot('restore-university');run("document.querySelector('[data-restore-university]').click()")
            wait("document.querySelectorAll('.university-card').length===1")
            # Cancel reset on Personal, preserving every personal field.
            click('open-reset');wait("document.getElementById('reset-dialog').open")
            assert run("document.getElementById('confirm-reset').disabled")
            run("document.getElementById('reset-confirmation').value='reset';document.getElementById('reset-confirmation').dispatchEvent(new Event('input'))")
            assert run("document.getElementById('confirm-reset').disabled")
            click('cancel-reset');assert profiles.workspace.research.snapshot()==before
            run("document.getElementById('new-profile-name').value='Testing';document.getElementById('create-profile-form').requestSubmit()")
            wait("document.querySelectorAll('#local-profile option').length===2")
            assert profiles.snapshot()['active_id']==personal
            click('switch-profile');ready('Testing')
            testing=profiles.snapshot()['active_id'];assert testing!=personal
            assert profiles.workspace.research.snapshot()['countries']=={}
            assert profiles.workspace.research.snapshot()['requests']==[]
            assert profiles.workspace.display_preferences()=={'text_size':'standard'}
            run("document.querySelector('.country-card[data-country=\"CAN\"]').click()")
            wait("!!document.getElementById('watch-detail-CAN')");click('watch-detail-CAN')
            wait("window.GradCompassResearch.personal('CAN').watched")
            run("document.getElementById('country-note-editor').open=true;document.getElementById('country-note').value='Temporary invented testing note'")
            click('save-country-note');wait("document.querySelector('.private-note-status').textContent.startsWith('Note saved')")
            run("document.querySelector('[data-research-country=\"CAN\"]').click()")
            click('research-selected');wait("document.getElementById('request-dialog').open")
            run("document.getElementById('request-intake').value='Invented testing intake'")
            click('request-submit');wait("document.getElementById('research-dialog').open && !!document.getElementById('research-request-detail').querySelector('h3')")
            assert len(profiles.workspace.research.snapshot()['requests'])==1
            assert profiles.workspace.research.snapshot()['preferences']['intake']=='Invented testing intake'
            click('close-research');click('open-settings');shot('separate-profiles')
            # Run the DOM/layout matrix in the browser to avoid hundreds of Qt IPC round trips.
            for width in (1440,820,390):
                window.resize(width,640 if width==390 else 960);wait('innerWidth',lambda value:abs(value-width)<5)
                print(f'Profile layout matrix: {width}px, all four text sizes',flush=True)
                run("""
                  window.__profileLayouts={done:false,captureReady:false,captureDone:false};
                  void (async()=>{
                    const get=id=>document.getElementById(id);
                    const pause=()=>new Promise(resolve=>setTimeout(resolve,60));
                    const until=async predicate=>{const end=performance.now()+15000;while(!predicate()){if(performance.now()>end)throw Error('Layout transition timed out');await pause();}};
                    const check=(valid,label)=>{if(!valid)throw Error(label)};
                    for(const scale of [1,1.15,1.3,1.5]){
                      document.documentElement.style.setProperty('--text-scale',scale);await pause();
                      check(get('settings-dialog').scrollWidth<=get('settings-dialog').clientWidth,'Settings overflow at '+scale);
                      get('open-reset').click();await until(()=>get('reset-dialog').open);
                      check(get('reset-dialog').scrollWidth<=get('reset-dialog').clientWidth,'Reset overflow at '+scale);
                      if(innerWidth===390 && scale===1.5 && CAPTURE){window.__profileLayouts.captureReady=true;await until(()=>window.__profileLayouts.captureDone);}
                      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
                      await until(()=>!get('reset-dialog').open && get('settings-dialog').open);
                      get('close-settings').click();await until(()=>!get('settings-dialog').open);
                      get('select-countries').click();await pause();
                      check(document.body.scrollWidth<=innerWidth,'Map overflow at '+scale);
                      await until(()=>get('map-selection-controls').getBoundingClientRect().bottom<=document.querySelector('.results-panel').getBoundingClientRect().top);
                      get('country-selection-list').click();await until(()=>get('country-selection-dialog').open);
                      check(get('country-selection-dialog').scrollWidth<=get('country-selection-dialog').clientWidth,'Country list overflow at '+scale);
                      get('return-country-selection').click();await until(()=>!get('country-selection-dialog').open);
                      get('done-selecting-countries').click();get('open-settings').click();await until(()=>get('settings-dialog').open);
                    }
                    window.__profileLayouts.done=true;
                  })().catch(error=>{window.__profileLayouts.error=error.message});
                """.replace('CAPTURE','true' if capture else 'false'))
                wait('window.__profileLayouts.done || window.__profileLayouts.error || window.__profileLayouts.captureReady')
                if width==390 and capture:
                    state=json.loads(run('JSON.stringify(window.__profileLayouts)'))
                    if state.get('captureReady'):
                        shot('narrow-reset-confirmation');run('window.__profileLayouts.captureDone=true')
                wait('window.__profileLayouts.done || window.__profileLayouts.error')
                state=json.loads(run('JSON.stringify(window.__profileLayouts)'))
                assert state.get('done'),(width,state)
            window.resize(1440,960);run("document.documentElement.style.setProperty('--text-scale',1)")
            click('open-reset');wait("document.getElementById('reset-dialog').open")
            run("document.getElementById('reset-confirmation').value='RESET';document.getElementById('reset-confirmation').dispatchEvent(new Event('input'))")
            run("document.documentElement.dataset.resetReview='waiting'")
            click('confirm-reset')
            # The profile name stays the same: prove a new document and bootstrap have loaded.
            wait("!!document.documentElement && !document.documentElement.dataset.resetReview && !!window.GradCompassWorkspace")
            ready('Testing')
            wait("document.querySelector('#settings-dialog')?.open===false")
            assert profiles.workspace.research.snapshot()['countries']=={}
            assert profiles.workspace.research.snapshot()['requests']==[]
            assert not profiles.workspace.research.snapshot()['has_preferences']
            assert profiles.workspace.country_decisions()=={}
            assert profiles.workspace.display_preferences()=={'text_size':'standard'}
            assert profiles.workspace.overview()['universities']==[]
            assert len(profiles.snapshot()['recovery_backups'])==1
            shot('empty-profile-after-reset')
            click('open-settings');run(f"document.getElementById('local-profile').value={json.dumps(personal)};document.getElementById('local-profile').dispatchEvent(new Event('change'))")
            click('switch-profile');ready('Personal')
            assert profiles.workspace.research.snapshot()==before
            assert profiles.workspace.research.request(case.request['request_id'])==before_details
            assert profiles.workspace.country_decisions()=={'CAN':'Shortlisted'}
            assert profiles.workspace.display_preferences()=={'text_size':'large'}
            assert len(profiles.workspace.overview()['universities'])==1
            shot('personal-data-preserved')
            passed.append(True)
            print('Profile UI passed: remove/cancel/restore/replay, independent profiles, remembered settings, typed reset/cancel/recovery, clean reload, Personal data preserved, and 12 settings/reset/map-selection layouts. Only invented temporary storage was used.',flush=True)
        except Exception as error:
            print('Profile UI failed:',repr(error),flush=True)
            traceback.print_exc()
            print('Diagnostics:',run("JSON.stringify({profile:document.getElementById('active-profile')?.textContent,selected:document.getElementById('local-profile')?.value,status:document.getElementById('profile-status')?.textContent,error:document.getElementById('error-text')?.textContent,disabled:document.getElementById('switch-profile')?.disabled})"),flush=True)
            print('Active test profile:',profiles.snapshot()['active_id'],flush=True)
            shot('failure')
        finally:window.destroy()
    try:webview.start(func=work,gui='qt',private_mode=True,storage_path=str(case.root/'browser'))
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5);case.doCleanups();watchdog.cancel()
        if screenshots:
            for path in screenshots.glob('2026-10-16-profiles-*.png'):path.chmod(0o600)
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
