"""Normal desktop scope checks; requires a marked disposable local workspace."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
from uuid import uuid4
APP=Path(__file__).resolve().parents[1];sys.path[:0]=[str(APP),str(APP/'scripts')]
from web.local import create_local_server,private_directory,atomic_json
from web.profiles import LocalProfiles
from web.research_selection import selection


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--screenshots',type=Path,required=True);parser.add_argument('--restart',action='store_true');args=parser.parse_args()
    if not (args.runtime/'.reader-review-copy').is_file():raise SystemExit('Use a marked disposable copy')
    profiles=LocalProfiles(args.runtime);workspace=profiles.workspace;before=workspace.research.snapshot();decisions=workspace.country_decisions();reading=(workspace.directory/'report-reading.json').read_bytes();personal=profiles.snapshot()['active_id']
    output=private_directory(args.screenshots)
    server=create_local_server(workspace,profiles=profiles);threading.Thread(target=server.serve_forever,daemon=True).start()
    os.environ['QT_API']='pyqt6';os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from preview_capture import PreviewCapture
    window=webview.create_window('Grad Compass — country selection check (disposable copy)',f'http://127.0.0.1:{server.server_port}/',width=1440,height=960,min_size=(390,640));capture=PreviewCapture(window,output,prefix='2026-10-21-selection-'+('restart-' if args.restart else ''));passed=[]
    watchdog=threading.Timer(180,lambda:os._exit(1));watchdog.daemon=True;watchdog.start()
    def work():
        def js(code):return window.run_js(code)
        def wait(code):
            end=time.monotonic()+30
            while time.monotonic()<end:
                result=js(code)
                if result:return result
                time.sleep(.1)
            raise AssertionError(code)
        def click(identity):js('setTimeout(()=>document.getElementById('+json.dumps(identity)+')?.click(),0);void 0')
        def choose(identity,value,event='change'):js('document.getElementById('+json.dumps(identity)+').value='+json.dumps(value)+';document.getElementById('+json.dumps(identity)+').dispatchEvent(new Event('+json.dumps(event)+'))')
        def shot(name):time.sleep(.6);capture.save(name)
        def saved(codes):
            end=time.monotonic()+20
            while time.monotonic()<end:
                if set(selection(workspace)['countries'])==set(codes) and js("document.getElementById('research-toolbar-status').textContent.includes('selection saved')"):return
                time.sleep(.1)
            raise AssertionError(('selection not saved',codes,selection(workspace)))
        try:
            window.events.loaded.wait(25);wait("!!document.querySelector('.country-card')");click('countries-mode');choose('country-list-scope','all');choose('search','','input')
            codes=js("[...document.querySelectorAll('.country-card')].map(n=>n.dataset.country)");assert len(codes)>200 and len(codes)==len(set(codes))
            map_before=js("JSON.stringify({url:location.href,map:document.querySelector('.leaflet-map-pane').style.transform,focused:document.getElementById('country').value})")
            if args.restart:
                expected=json.loads((output/'selection-expected.local.json').read_text());assert set(selection(workspace)['countries'])==set(expected['countries'])
                assert js("document.getElementById('research-selection-summary').textContent.startsWith('"+str(len(expected['countries']))+" selected')")
                assert js("document.querySelector('[data-research-country=BEL]').checked===false")
                shot('persisted');passed.append(True);print('Native selection restart passed: full draft and individual exclusion restored.',flush=True);return
            if not js("document.getElementById('research-clear-selection').disabled"):click('research-clear-selection');saved([])
            assert js("document.querySelectorAll('[data-research-country]:disabled').length===0")
            assert js("document.getElementById('research-select-matching').textContent==='Select all matching ("+str(len(codes))+")'")
            # The last catalogue entry is outside the viewport; select-all still includes it.
            assert js("[...document.querySelectorAll('.country-card')].at(-1).getBoundingClientRect().top>innerHeight")
            js("[...document.querySelectorAll('.country-card')].at(-1).closest('.country-entry').remove()")
            click('research-select-matching');saved(codes);shot('all-catalogue');js("document.querySelector('[data-research-country=AFG]').scrollIntoView({block:'center'})");shot('individual-checkboxes')
            js("document.querySelector('[data-research-country=BEL]').click()");remaining=[c for c in codes if c!='BEL'];saved(remaining)
            assert js("[...document.querySelectorAll('[data-research-country=BEL]')].every(n=>!n.checked)")
            choose('search','united','input');matching=js("[...document.querySelectorAll('.country-card')].map(n=>n.dataset.country)");assert 1<len(matching)<20
            assert js("document.getElementById('research-selection-summary').textContent.includes('"+str(len(remaining)-len(matching))+" outside this filter')")
            shot('filtered-outside-selection');click('research-clear-selection');saved([]);click('research-select-matching');saved(matching)
            choose('search','Belgium','input');assert js("document.getElementById('research-selection-summary').textContent.includes('"+str(len(matching))+" outside this filter')")
            js("document.querySelector('[data-research-country=BEL]').click()");scope=matching+['BEL'];saved(scope)
            click('research-selected');wait("document.getElementById('request-dialog').open")
            assert set(js("JSON.parse(document.getElementById('request-countries').dataset.countryCodes)"))==set(scope)
            assert all(name in js("document.getElementById('request-countries').textContent") for name in ['Belgium','United'])
            shot('complete-filtered-request-draft');click('cancel-request')
            choose('search','','input');click('research-select-matching');saved(codes);click('research-selected');wait("document.getElementById('request-dialog').open")
            assert js("JSON.parse(document.getElementById('request-countries').dataset.countryCodes).length")==len(codes)
            assert js("document.getElementById('request-submit').disabled && document.getElementById('request-form-status').textContent.includes('Full scope preserved')")
            shot('full-scope-before-submission');click('cancel-request')
            js("document.querySelector('[data-research-country=BEL]').click()");saved(remaining)
            assert js("JSON.stringify({url:location.href,map:document.querySelector('.leaflet-map-pane').style.transform,focused:document.getElementById('country').value})")==map_before
            window.resize(390,740);wait('innerWidth===390');js("document.documentElement.style.setProperty('--text-scale',1.5)");assert js("document.documentElement.scrollWidth<=innerWidth && parseFloat(getComputedStyle(document.documentElement).fontSize)>23");js("document.getElementById('research-selected').scrollIntoView({block:'center'})");shot('narrow-large-text')
            window.resize(1440,960);wait('innerWidth===1440');js("document.documentElement.style.setProperty('--text-scale',1)")
            # Profile change uses the same token-guarded endpoints and normal reload.
            click('open-settings');wait("document.getElementById('settings-dialog').open");test_name='Selection isolation '+uuid4().hex[:6];choose('new-profile-name',test_name)
            js("document.getElementById('create-profile-form').requestSubmit()");wait("document.getElementById('profile-status').textContent.includes('created empty')");other=js("document.getElementById('local-profile').value");click('switch-profile')
            wait("document.getElementById('active-profile')?.textContent==="+json.dumps('Profile: '+test_name));wait("document.getElementById('research-selection-summary').textContent==='0 selected'")
            assert selection(profiles.workspace)=={'countries':[]}
            click('countries-mode');choose('country-list-scope','all');choose('search','Canada','input');wait("!!document.querySelector('[data-research-country=CAN]')");js("document.querySelector('[data-research-country=CAN]').click()")
            wait("document.getElementById('research-toolbar-status').textContent.includes('selection saved')");assert selection(profiles.workspace)=={'countries':['CAN']}
            click('open-settings');choose('local-profile',personal);click('switch-profile');wait("document.getElementById('active-profile')?.textContent!=="+json.dumps('Profile: '+test_name));wait("document.getElementById('research-selection-summary').textContent.startsWith('"+str(len(remaining))+" selected')")
            assert set(selection(profiles.workspace)['countries'])==set(remaining)
            after=workspace.research.snapshot();assert {k:v for k,v in after.items() if k!='draft_selection'}=={k:v for k,v in before.items() if k!='draft_selection'}
            assert workspace.country_decisions()==decisions and (workspace.directory/'report-reading.json').read_bytes()==reading
            atomic_json(output/'selection-expected.local.json',{'countries':remaining,'catalogue_count':len(codes),'other_profile':other})
            passed.append(True);print('Native selection passed: complete catalogue, filtered scope, exclusions, outside-filter count, clear, exact composer scope, guarded bounds, narrow text, profile isolation; no request/research or map changes.',flush=True)
        except Exception:traceback.print_exc();shot('failure')
        finally:watchdog.cancel();window.confirm_close=False;window.destroy()
    webview.start(func=work,gui='qt',debug=False,private_mode=True,storage_path=str(private_directory(args.runtime/'selection-browser')))
    server.shutdown();assert passed,'Native selection checks failed'


if __name__=='__main__':main()
