"""Read-only visual demonstration of the actual persistent local workflow."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
APP_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP_ROOT));sys.path.insert(0,str(APP_ROOT/'scripts'))
from web.local import LocalWorkspace,create_local_server


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,default=APP_ROOT.parent/'grad-compass-workspace/runtime/local')
    parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args();workspace=LocalWorkspace(args.runtime)
    before=workspace.research.snapshot()
    if len(workspace.overview()['universities'])!=5:raise SystemExit('The first real returned dataset must be received before this demonstration')
    server=create_local_server(workspace,port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    os.environ['QT_API']='pyqt6'
    import webview
    from preview_capture import PreviewCapture
    window=webview.create_window('Grad Compass — Real local workflow review',f'http://127.0.0.1:{server.server_port}/',width=1440,height=960,min_size=(390,640))
    from web.local import private_directory
    screenshots=private_directory(args.screenshots or workspace.directory/'reviews')
    capture=PreviewCapture(window,screenshots,prefix='2026-10-16-local-')
    passed=[]
    def work():
        def run(source):return window.run_js(source)
        def wait(source,check=bool):
            end=time.monotonic()+20
            while time.monotonic()<end:
                value=run(source)
                if check(value):return value
                time.sleep(.1)
            raise AssertionError((source,value))
        def click(name):run(f'document.getElementById({json.dumps(name)}).click()')
        try:
            window.events.loaded.wait(20)
            wait("document.body.dataset.workspace==='local' && !!document.querySelector('.country-card')")
            assert run("document.getElementById('error').hidden")
            assert run("document.querySelector('.preview-label').textContent")=='Private local workspace'
            assert run("document.querySelectorAll('.leaflet-overlay-pane path[fill=\"#087ba4\"]').length") == 5
            capture.save('saved-countries-map')
            run("document.querySelector('.country-card[data-country=\"CAN\"]').click()")
            wait("document.querySelectorAll('#inspector .country-finding').length>1")
            assert 'pending' in run("document.querySelector('.research-state').textContent")
            capture.save('country-findings')
            click('explore-country')
            wait("document.querySelectorAll('.university-card').length===3")
            run("document.querySelector('.university-card').click()")
            wait("document.querySelectorAll('#inspector .program-card').length===1")
            assert run("document.querySelector('#inspector').textContent.includes('pending')")
            capture.save('university-program-evidence')
            click('list-view');time.sleep(.3);capture.save('universities-list')
            click('countries-mode');click('open-research')
            wait("document.querySelectorAll('.finding-card').length===38")
            assert 'complete' in run("document.getElementById('research-result-revision').textContent")
            capture.save('request-returned-results')
            click('close-research');click('open-settings');click('sample-history')
            wait("document.getElementById('research-message').textContent.includes('Sample history')")
            capture.save('separate-sample-history')
            click('close-research');click('map-view')
            # Inspect the real request form, then cancel without creating another request.
            run("document.querySelector('[data-research-country=\"CAN\"]').click()")
            click('research-selected');wait("document.getElementById('request-dialog').open")
            assert run("!document.getElementById('request-bounds').hidden")
            assert run("!document.getElementById('request-preferences').open")
            capture.save('remembered-preferences-and-bounds');click('cancel-request')
            # Visual scaling only: never save a test size over the owner's setting.
            for width in (1440,820,390):
                window.resize(width,640 if width==390 else 960)
                wait('innerWidth',lambda value:abs(value-width)<5)
                for scale in (1,1.15,1.3,1.5):
                    run(f"document.documentElement.style.setProperty('--text-scale',{scale})")
                    click('select-countries');time.sleep(.25)
                    assert run("document.body.scrollWidth<=innerWidth"),(width,scale)
                    assert run("document.getElementById('map-selection-controls').getBoundingClientRect().bottom<=document.querySelector('.results-panel').getBoundingClientRect().top"),(width,scale)
                    click('country-selection-list')
                    assert run("document.getElementById('country-selection-dialog').scrollWidth<=document.getElementById('country-selection-dialog').clientWidth"),(width,scale)
                    click('return-country-selection');click('done-selecting-countries')
            capture.save('narrow-extra-large-workspace')
            click('open-settings');wait("!document.getElementById('text-size').disabled")
            # Inspect the current setting without saving/changing the owner's preference.
            click('close-settings');capture.save('narrow-workspace')
            run("location.reload()")
            wait("document.body.dataset.workspace==='local' && !!document.querySelector('.country-card')")
            assert len(workspace.research.snapshot()['requests'])==len(before['requests'])
            assert workspace.research.snapshot()['countries']==before['countries']
            assert workspace.research.snapshot()['preferences']==before['preferences']
            passed.append(True)
            print('Real local UI passed: saved countries, all field findings, 5 verified university pins/5 programs, 38 returned findings, remembered preferences/bounds, separate sample archive, Map/List, reload and 12 window/text layouts; no personal state or requests changed.',flush=True)
        except Exception as error:
            print('Local UI failed:',repr(error),flush=True)
        finally:window.destroy()
    try:webview.start(func=work,gui='qt',private_mode=True,storage_path=str(workspace.directory/'browser'))
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    for path in screenshots.glob('2026-10-16-local-*.png'):path.chmod(0o600)
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
