"""Exercise automatic operational receipt with invented temporary test data only."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
from types import SimpleNamespace

APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'tests'),str(APP/'scripts')]
import test_local as fixtures
from web import research_envelopes as env
from web.local import create_local_server,private_directory
from web.profiles import LocalProfiles


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    case=fixtures.LocalTests();case.setUp();profiles=LocalProfiles(case.workspace.directory)
    # Qt clipboard behavior has an offscreen regression; this UI test must not
    # replace the owner's clipboard with an invented prompt.
    copied=[]
    server=create_local_server(profiles.workspace,profiles=profiles,clipboard=SimpleNamespace(copy_text=copied.append))
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    os.environ['QT_API']='pyqt6'
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from preview_capture import PreviewCapture
    url=f'http://127.0.0.1:{server.server_port}/'
    window=webview.create_window('Grad Compass — Invented automatic receipt review',url,width=1440,height=960,min_size=(390,640))
    capture=PreviewCapture(window,private_directory(args.screenshots),prefix='2026-10-19-inbox-') if args.screenshots else None
    passed=[]
    def exercise():
        def run(script):return window.run_js(script)
        def wait(script,check=bool):
            end=time.monotonic()+25
            while time.monotonic()<end:
                value=run(script)
                if check(value):return value
                time.sleep(.15)
            raise AssertionError((script,value))
        def click(identity):run(f'setTimeout(()=>document.getElementById({json.dumps(identity)})?.click(),0);void 0')
        def shot(name):
            if capture:capture.save(name)
        def deliver(value,name):
            path=profiles.workspace.directory/'inbox'/name;temporary=path.with_name('.'+name+'.tmp')
            temporary.write_text(json.dumps(env.packet(value)));temporary.replace(path)
        try:
            window.events.loaded.wait(20);wait('!!window.GradCompassWorkspace && !!window.GradCompassLocal')
            wait("!!document.querySelector('.country-card[data-country=\"CAN\"]')")
            run("document.querySelector('.country-card[data-country=\"CAN\"]').click()")
            wait("!!document.getElementById('country-note')")
            run("document.getElementById('country-note').value='Unsent country note stays here'")
            click('open-research');wait("!!document.getElementById('prepare-research-handoff')")
            assert run("document.getElementById('prepare-research-handoff').textContent")=='Copy instructions for Dave'
            assert not run("document.getElementById('research-response-review').open")
            click('prepare-research-handoff');wait("!!document.getElementById('research-handoff')")
            wait("document.getElementById('research-message').textContent.startsWith('Copied.')")
            assert copied[-1]==profiles.workspace.research.export(case.request['request_id'])['prompt']
            assert profiles.workspace.research.snapshot()['requests'][0]['state']=='prepared'
            shot('saved-manual-instructions')
            ack=case.ack();hidden=profiles.workspace.directory/'inbox/.ack.tmp';hidden.write_text(json.dumps(env.packet(ack)))
            time.sleep(1);assert profiles.workspace.research.snapshot()['requests'][0]['state']=='prepared'
            hidden.replace(hidden.with_name('ack.json'))
            wait("document.querySelector('.request-state')?.textContent.includes('Acknowledged')")
            assert run("document.getElementById('country-note').value")=='Unsent country note stays here'
            shot('acknowledgement-arrived');print('Acknowledgement appeared automatically.',flush=True)
            partial={**case.result(),'completion':'partial'};deliver(partial,'partial.json')
            wait("document.querySelector('.request-state')?.textContent.includes('Partial results ready')")
            wait("document.querySelectorAll('.finding-card').length===2")
            assert not run("document.getElementById('results-ready').hidden")
            run("document.querySelector('.feedback-open').click();document.querySelector('.finding-comment').value='Keep this unsent feedback draft'")
            final={**partial,'result_revision':2,'previous_result_revision':1,'previous_result_digest':env.packet(partial)['sha256'],'completion':'complete'}
            deliver(final,'final.json')
            wait("!document.getElementById('show-received-results').hidden")
            assert run("document.querySelector('.finding-comment').value")=='Keep this unsent feedback draft'
            click('show-received-results');wait("document.querySelector('.request-state')?.textContent==='Results ready — review findings'")
            wait("document.querySelector('#research-result-revision')?.value==='2'")
            assert run("document.querySelectorAll('.finding-card').length")==2
            shot('final-results-ready');print('Partial/final findings appeared automatically; unsent draft was preserved.',flush=True)
            (profiles.workspace.directory/'inbox/invalid.json').write_text('{}')
            wait("!document.getElementById('inbox-errors').hidden")
            run("document.getElementById('inbox-errors').open=true")
            assert 'transport' in run("document.getElementById('inbox-error-list').textContent")
            window.resize(390,700);wait('innerWidth',lambda value:value==390)
            run("document.documentElement.style.setProperty('--text-scale',1.5)")
            wait("document.getElementById('research-dialog').scrollWidth<=document.getElementById('research-dialog').clientWidth")
            shot('narrow-errors-and-results')
            (profiles.workspace.directory/'inbox/invalid.json').unlink()
            before=profiles.workspace.research.request(case.request['request_id'])
            run("document.documentElement.dataset.beforeReload='yes'");window.load_url(url)
            wait("!!document.documentElement && !document.documentElement.dataset.beforeReload && !!window.GradCompassWorkspace")
            wait("!document.getElementById('results-ready').hidden")
            click('results-ready');wait("document.querySelector('#research-result-revision')?.value==='2'")
            assert profiles.workspace.research.request(case.request['request_id'])==before
            assert len(profiles.workspace.research.snapshot()['requests'])==1
            assert profiles.workspace.research.snapshot()['requests'][0]['result_count']==2
            assert not run("document.getElementById('research-response-review').open")
            passed.append(True);print('Automatic inbox UI passed: saved/manual instructions, hidden-write safety, acknowledgement, partial/final findings, draft protection, visible invalid-packet errors, narrow large text, replay and reopen persistence. No agent was invoked; only invented temporary data was used.',flush=True)
        except Exception:
            traceback.print_exc();shot('failure')
        finally:window.destroy()
    try:webview.start(func=exercise,gui='qt',private_mode=True,storage_path=str(case.root/'browser'))
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5);case.doCleanups()
        if args.screenshots:
            for path in args.screenshots.glob('2026-10-19-inbox-*.png'):path.chmod(0o600)
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
