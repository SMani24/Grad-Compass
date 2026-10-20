"""Desktop country/report review against an isolated copy of existing real research."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback

APP=Path(__file__).resolve().parents[1];sys.path[:0]=[str(APP),str(APP/'scripts')]
from web.local import create_local_server,private_directory,atomic_json
from web.profiles import LocalProfiles


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--screenshots',type=Path,required=True);parser.add_argument('--restart',action='store_true');args=parser.parse_args()
    if not (args.runtime/'.country-review-copy').is_file():raise SystemExit('Use an explicitly marked isolated review copy')
    profiles=LocalProfiles(args.runtime);source=profiles.workspace.research.snapshot();identity='41b6af76-f27e-4c58-a3a8-b835101658f0';history=profiles.workspace.research.request(identity)
    server=create_local_server(profiles.workspace,profiles=profiles);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    os.environ['QT_API']='pyqt6';os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from preview_capture import PreviewCapture
    from PyQt6.QtCore import QObject,pyqtSignal,pyqtSlot,QPoint,Qt
    from PyQt6.QtTest import QTest
    class NativeDrag(QObject):
        requested=pyqtSignal(object)
        def __init__(self):super().__init__();self.requested.connect(self.perform);self.done=threading.Event()
        @pyqtSlot(object)
        def perform(self,value):
            from webview.platforms.qt import BrowserView
            view=BrowserView.instances[window.uid].webview;target=view.focusProxy() or view
            x,y,delta=value;QTest.mousePress(target,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(x,y));QTest.mouseMove(target,QPoint(x+delta,y),100);QTest.mouseRelease(target,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,QPoint(x+delta,y));self.done.set()
        def drag(self,value):self.done.clear();self.requested.emit(value);assert self.done.wait(10)
    drag=NativeDrag();screenshots=private_directory(args.screenshots)
    url=f'http://127.0.0.1:{server.server_port}/';window=webview.create_window('Grad Compass — Belgium country workspace review (isolated copy)',url,width=1440,height=1000,min_size=(390,640));capture=PreviewCapture(window,screenshots,prefix='2026-10-20-'+('restart-' if args.restart else ''))
    passed=[]
    def timeout():os._exit(1)
    watchdog=threading.Timer(240,timeout);watchdog.daemon=True;watchdog.start()
    def work():
        def run(script):return window.run_js(script)
        def wait(script,predicate=bool):
            end=time.monotonic()+25
            while time.monotonic()<end:
                value=run(script)
                if predicate(value):return value
                time.sleep(.1)
            raise AssertionError((script,value))
        def click(identity):run('setTimeout(()=>document.getElementById('+json.dumps(identity)+')?.click(),0);void 0')
        def shot(name):time.sleep(.25);capture.save(name)
        def select_country():
            wait("!!document.querySelector('.country-card[data-country=\"BEL\"]')")
            run("document.querySelector('.country-card[data-country=\"BEL\"]').click()")
            wait("!!document.getElementById('country-decision')")
        def choose(value):
            run('document.getElementById("country-decision").value='+json.dumps(value)+';document.getElementById("country-decision").dispatchEvent(new Event("change"))')
            wait("document.querySelector('.decision-status').textContent.startsWith('Saved')")
        try:
            window.events.loaded.wait(25);wait("!!window.GradCompassWorkspace && document.getElementById('resize-left').hasAttribute('aria-valuenow')")
            select_country()
            assert 'Country report available' in run("document.querySelector('.country-card[data-country=\"BEL\"]').textContent")
            assert 'University discovery not started' in run("document.querySelector('.country-card[data-country=\"BEL\"]').textContent")
            if args.restart:
                assert run("document.getElementById('country-decision').value")=='Shortlisted'
                assert profiles.workspace.country_decisions()['BEL']=='Shortlisted'
                assert profiles.workspace.directory.joinpath('panel-widths.json').is_file()
                widths=json.loads(profiles.workspace.directory.joinpath('panel-widths.json').read_text())
                assert int(run("document.getElementById('resize-left').getAttribute('aria-valuenow')"))==widths['left']
                assert int(run("document.getElementById('resize-right').getAttribute('aria-valuenow')"))==widths['right']
                click('open-settings');wait("document.getElementById('settings-dialog').open");click('reset-panel-widths')
                wait("document.getElementById('panel-save-status').textContent.startsWith('Panel widths saved')")
                assert json.loads(profiles.workspace.directory.joinpath('panel-widths.json').read_text())=={'left':300,'right':350}
                click('close-settings')
                click('read-country-report');wait("!!document.getElementById('country-report')")
                assert profiles.workspace.research.request(identity)==history
                shot('persistent-report')
                wait("!!document.querySelector('.report-photo img')")
                run("document.querySelector('.report-photo img').src='/assets/absent-review-image.jpg'")
                wait("!document.querySelector('.report-photo img')")
                assert run("getComputedStyle(document.querySelector('.photo-fallback')).display")!='none'
                shot('image-fallback');passed.append(True);print('Country restart passed: decisions, independent widths, notes, report and exact research history retained; reset action and missing-image fallback work.',flush=True);return
            choose('On hold');choose('Shortlisted')
            assert run("document.querySelector('.country-card[data-country=\"BEL\"] .decision-badge').textContent")=='Shortlisted'
            run("window.__fetch=window.fetch;window.fetch=(url,options)=>url==='/api/country-decisions'?Promise.resolve(new Response(JSON.stringify({error:'Injected save failure; previous decision preserved'}),{status:503,headers:{'Content-Type':'application/json'}})):window.__fetch(url,options);document.getElementById('country-decision').value='Excluded';document.getElementById('country-decision').dispatchEvent(new Event('change'))")
            wait("document.querySelector('.decision-status').textContent.includes('Injected save failure')");assert run("document.getElementById('country-decision').value")=='Shortlisted';run('window.fetch=window.__fetch')
            assert profiles.workspace.country_decisions()['BEL']=='Shortlisted'
            for side,delta in [('left',90),('right',-65)]:
                coordinates=json.loads(run("JSON.stringify((()=>{const r=document.getElementById('resize-"+side+"').getBoundingClientRect();return [Math.round(r.x+r.width/2),Math.round(r.y+r.height/2)]})())"))
                initial=int(run("document.getElementById('resize-"+side+"').getAttribute('aria-valuenow')"));drag.drag([*coordinates,delta])
                wait("Number(document.getElementById('resize-"+side+"').getAttribute('aria-valuenow'))>"+str(initial))
            run("document.getElementById('resize-left').focus();document.getElementById('resize-left').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}))")
            wait("document.getElementById('panel-save-status').textContent.startsWith('Panel widths saved')")
            shot('map-panels-and-decision')
            context=run("JSON.stringify({url:location.href,pane:document.querySelector('.leaflet-map-pane').style.transform,left:getComputedStyle(document.documentElement).getPropertyValue('--results-width'),right:getComputedStyle(document.documentElement).getPropertyValue('--inspector-width'),country:document.getElementById('country').value})")
            click('read-country-report');wait("document.getElementById('country-report')?.dataset.country==='BEL'")
            assert run("document.getElementById('research-dialog').getBoundingClientRect().width>=innerWidth*.95")
            assert not run("document.getElementById('report-history').open")
            assert run("document.getElementById('research-result-revision').value")=='2'
            assert run("document.querySelectorAll('#report-sources .report-source').length")==21
            wait("!!document.querySelector('.report-photo img') && document.querySelector('.report-photo img').naturalWidth>0")
            run("document.getElementById('research-dialog').scrollTop=0");shot('belgium-report-header')
            run("document.getElementById('report-funding').scrollIntoView({block:'start'})");shot('belgium-funding-and-citations')
            click('toggle-report-notes');wait("!document.querySelector('.report-annotation-panel').hidden")
            run("document.getElementById('report-personal-note').value='Private isolated review note'")
            run("document.querySelector('.report-annotation-panel button').click()")
            wait("document.querySelector('.report-annotation-panel').textContent.includes('Country note saved')")
            click('close-research');wait("!document.getElementById('research-dialog').open")
            assert context==run("JSON.stringify({url:location.href,pane:document.querySelector('.leaflet-map-pane').style.transform,left:getComputedStyle(document.documentElement).getPropertyValue('--results-width'),right:getComputedStyle(document.documentElement).getPropertyValue('--inspector-width'),country:document.getElementById('country').value})")
            # Repeated layout checks run inside the renderer to avoid slow IPC loops.
            for width in (1440,820,390):
                window.resize(width,1000 if width>390 else 740);wait('innerWidth',lambda v:v==width)
                print('Country report layout:',width,'all four text sizes',flush=True)
                run("""window.__reportMatrix={done:false};void(async()=>{
                  const pause=()=>new Promise(r=>setTimeout(r,120));const until=async test=>{const end=performance.now()+18000;while(!test()){if(performance.now()>end)throw Error('Report transition timed out');await pause();}};
                  for(const scale of [1,1.15,1.3,1.5]){
                    document.documentElement.style.setProperty('--text-scale',scale);await pause();
                    document.getElementById('read-country-report').click();await until(()=>!!document.getElementById('country-report') && document.getElementById('research-dialog').open);
                    const d=document.getElementById('research-dialog');if(d.scrollWidth>d.clientWidth)throw Error('Report overflow '+scale);
                    if(document.querySelector('.country-report').scrollWidth>document.querySelector('.country-report').clientWidth)throw Error('Country reading column overflow '+scale);
                    document.getElementById('close-research').click();await until(()=>!d.open);
                    if(document.body.scrollWidth>innerWidth)throw Error('Map overflow '+scale);
                  }window.__reportMatrix.done=true;
                })().catch(e=>window.__reportMatrix.error=e.message)""")
                wait('window.__reportMatrix.done || window.__reportMatrix.error');assert run('window.__reportMatrix.done'),run('window.__reportMatrix.error')
            click('read-country-report');wait("!!document.getElementById('country-report')");run("document.getElementById('research-dialog').scrollTop=0");shot('narrow-extra-large-report')
            assert profiles.workspace.research.request(identity)==history
            assert profiles.workspace.research.snapshot()['countries']['BEL']['note']=='Private isolated review note'
            passed.append(True);print('Country workspace passed: actual pointer resizing, keyboard resizing, profile-local saves/error rollback, card consistency, map return, latest report/sources, note saving and 12 readable layouts. Exact research history unchanged.',flush=True)
        except Exception:
            traceback.print_exc();shot('failure')
        finally:window.destroy()
    try:webview.start(func=work,gui='qt',private_mode=True,storage_path=str(args.runtime/'browser'))
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5);watchdog.cancel()
        for p in screenshots.glob('2026-10-20-*.png'):p.chmod(0o600)
    if not passed:raise SystemExit(1)


if __name__=='__main__':main()
