"""Normal Qt desktop checks, restricted to a marked disposable report copy."""
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
from web.report_reading import preferences


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--screenshots',type=Path,required=True);parser.add_argument('--restart',action='store_true');args=parser.parse_args()
    if not (args.runtime/'.reader-review-copy').is_file():raise SystemExit('Use an explicitly marked disposable report copy')
    profiles=LocalProfiles(args.runtime);workspace=profiles.workspace
    if not args.restart:
        from web.report_packages import catalog
        latest=next(r for r in catalog(workspace)['reports'] if r['metadata']['country_code']=='BEL')
        preferences(workspace,{'width':'comfortable','sidebar_open':True,'position':{'key':latest['key'],**({'document':latest['reader']['id']} if latest.get('reader') else {}),'anchor':'top','offset':0}})
    server=create_local_server(workspace,profiles=profiles)
    threading.Thread(target=server.serve_forever,daemon=True).start();os.environ['QT_API']='pyqt6'
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from desktop_downloads import DesktopDownloads
    from preview_capture import PreviewCapture
    output=private_directory(args.screenshots);downloads=private_directory(output/'downloads'/str(uuid4()));names=[]
    window=webview.create_window('Grad Compass — reader refinement check (isolated copy)',f'http://127.0.0.1:{server.server_port}/',width=1440,height=1000,min_size=(390,640))
    capture=PreviewCapture(window,output,prefix='2026-10-21-reader-'+('restart-' if args.restart else ''))
    def choose(name):names.append(name);return str(downloads/name)
    handler=DesktopDownloads(window,choose_path=choose);passed=[]
    watchdog=threading.Timer(240,lambda:os._exit(1));watchdog.daemon=True;watchdog.start()
    def work():
        def js(code):return window.run_js(code)
        def wait(code,predicate=bool):
            end=time.monotonic()+30;value=None
            while time.monotonic()<end:
                value=js(code)
                if predicate(value):return value
                time.sleep(.1)
            raise AssertionError((code,value))
        def click(identity):js('setTimeout(()=>document.getElementById('+json.dumps(identity)+')?.click(),0);void 0')
        def shot(name):time.sleep(.25);capture.save(name)
        def select(identity,value):js('document.getElementById('+json.dumps(identity)+').value='+json.dumps(value)+';document.getElementById('+json.dumps(identity)+').dispatchEvent(new Event("change"))')
        def download(identity):
            before=len(names);click(identity);wait('true')
            end=time.monotonic()+30
            while time.monotonic()<end and (len(names)<=before or not (downloads/names[-1]).is_file()):time.sleep(.1)
            assert len(names)==before+1 and (downloads/names[-1]).is_file(),names
            return downloads/names[-1]
        try:
            handler.install_requested.emit();assert handler.installed.wait(10)
            window.events.loaded.wait(25);wait("!!document.querySelector('.country-card[data-country=BEL]')")
            js("document.querySelector('.country-card[data-country=BEL]').click()");wait("!!document.getElementById('read-country-report') && !!document.querySelector('.country-overflow')")
            wait("document.querySelector('.country-report-availability').textContent.includes('v2')")
            assert js("document.getElementById('read-country-report').getBoundingClientRect().top<document.getElementById('explore-country').getBoundingClientRect().top")
            assert js("document.getElementById('watch-detail-BEL').closest('details').open===false")
            if not args.restart:
                for side in ('left','right'):
                    old=js('Number(document.getElementById("resize-'+side+'").getAttribute("aria-valuenow"))')
                    maximum=js('Number(document.getElementById("resize-'+side+'").getAttribute("aria-valuemax"))');delta=10 if old+10<=maximum else -10
                    key=('ArrowRight' if side=='left' else 'ArrowLeft') if delta>0 else ('ArrowLeft' if side=='left' else 'ArrowRight')
                    js('document.getElementById("resize-'+side+'").dispatchEvent(new KeyboardEvent("keydown",{key:"'+key+'",bubbles:true}))')
                    wait('Number(document.getElementById("resize-'+side+'").getAttribute("aria-valuenow"))==='+str(old+delta))
                shot('country-actions-and-dividers')
            context=js("JSON.stringify({url:location.href,map:document.querySelector('.leaflet-map-pane').style.transform,left:getComputedStyle(document.documentElement).getPropertyValue('--results-width'),right:getComputedStyle(document.documentElement).getPropertyValue('--inspector-width')})")
            click('read-country-report');wait("!!document.querySelector('.canonical-report .canonical-table') && document.getElementById('reader-status').textContent.includes('loaded')")
            time.sleep(.3)
            if args.restart:
                assert js("document.getElementById('research-dialog').dataset.readingWidth==='wide' && document.getElementById('research-dialog').classList.contains('requests-collapsed')")
                saved=preferences(workspace);position=saved['positions'][js("document.querySelector('.canonical-report').dataset.canonical+':'+document.querySelector('.canonical-report').dataset.document")]
                assert position['anchor'].startswith('regional-guides'),position
                top=js("[...document.querySelectorAll('[data-report-block]')].find(n=>n.dataset.reportBlock==="+json.dumps(position['anchor'])+").getBoundingClientRect().top")
                edge=js("document.querySelector('.reader-toolbar').getBoundingClientRect().height+20")
                assert abs(edge-top-position['offset'])<10,(edge,top,position)
                shot('reading-position');passed.append(True);print('Native restart passed: remembered width/sidebar and exact-version passage position.',flush=True);return
            assert js("document.querySelector('.canonical-report').dataset.readingEdition==='reader'")
            def alignment():
                assert js("[...document.querySelectorAll('.canonical-reading .report-section')].every(section=>{const heading=section.querySelector('h2');return [...section.children].filter(n=>n.matches('.canonical-passage,.report-terms,.report-table-wrap')).every(n=>Math.abs(n.getBoundingClientRect().left-heading.getBoundingClientRect().left)<2);})")
                assert js("document.querySelector('.report-table-wrap').clientWidth<=document.querySelector('.canonical-reading').clientWidth+1")
            alignment()
            assert js("document.querySelector('.reader-selection-actions').hidden")
            assert js("document.querySelector('.canonical-reading [data-report-block]').getBoundingClientRect().top<innerHeight*.7")
            assert js("document.querySelector('.canonical-reading').textContent.includes('fully English-taught') && !document.querySelector('.canonical-reading').textContent.includes('Derived arithmetic and its limits')")
            wait("!!document.querySelector('.inline-evidence')");js("document.querySelector('.inline-evidence').click()");wait("document.getElementById('report-source-dialog').open");assert js("document.querySelectorAll('#report-source-dialog a[href^=https]').length>0");shot('compact-sources');click('close-report-sources')
            click('reader-full-report');wait("document.querySelector('.canonical-report').dataset.readingEdition==='detailed'");assert js("document.querySelector('.canonical-reading').textContent.includes('Derived arithmetic and its limits')");alignment();shot('full-report');click('reader-show-report');wait("document.querySelector('.canonical-report').dataset.readingEdition==='reader'")
            shot('comfortable')
            js("document.querySelector('.reader-options>summary').click()");assert js("document.querySelector('.reader-options').open && document.getElementById('reader-width').getBoundingClientRect().width>0");time.sleep(.5);assert js("document.querySelector('.reader-options').open");shot('reading-options');assert js("document.querySelector('.reader-options').open");js("document.querySelector('.reader-options>summary').click()")
            js("document.querySelector('.reader-exports>summary').click()");assert js("document.getElementById('reader-download-pdf').getBoundingClientRect().width>0 && !document.getElementById('export-personal-annotations').checked");time.sleep(.5);assert js("document.querySelector('.reader-exports').open");shot('export-menu');assert js("document.querySelector('.reader-exports').open");js("document.querySelector('.reader-exports>summary').click()")
            select('reader-width','wide');wait("document.getElementById('research-dialog').dataset.readingWidth==='wide'");click('report-sidebar-toggle');wait("document.getElementById('research-dialog').classList.contains('requests-collapsed')");time.sleep(.3)
            assert js("document.querySelector('.canonical-table').clientWidth>900")
            shot('wide-header')
            select('reader-sections','canonical-funding-attractive-possibilities-important-limits');time.sleep(.3);alignment();assert js("document.querySelector('#canonical-funding-attractive-possibilities-important-limits h2').getBoundingClientRect().top>=document.querySelector('.reader-toolbar').getBoundingClientRect().bottom");shot('wide-funding')
            before_width=js("document.querySelector('.canonical-reading').clientWidth");click('reader-annotations');wait("document.querySelector('.annotation-panel').hidden===false")
            assert js("document.querySelector('.canonical-reading').clientWidth")<before_width
            click('reader-annotations');wait("document.querySelector('.annotation-panel').hidden===true");assert js("document.querySelector('.canonical-reading').clientWidth")==before_width
            # Private annotation is created only in this disposable copy, for explicit export checks.
            js("""(()=>{const block=document.querySelector('#canonical-the-useful-routes [data-report-block]');const node=document.createTreeWalker(block,NodeFilter.SHOW_TEXT);while(node.nextNode() && !node.currentNode.textContent.trim()){}const r=document.createRange();r.selectNodeContents(node.currentNode);getSelection().removeAllRanges();getSelection().addRange(r);document.querySelector('.canonical-reading').dispatchEvent(new KeyboardEvent('keyup',{key:'ArrowRight',shiftKey:true,bubbles:true}));})()""")
            assert js("!document.querySelector('.reader-selection-actions').hidden && !document.getElementById('reader-comment').disabled")
            click('reader-comment');wait("!!document.getElementById('new-annotation-comment-text')");js("document.getElementById('new-annotation-comment-text').value='Disposable reader export comment'");click('save-new-annotation');wait("document.getElementById('reader-status').textContent.includes('saved privately')");click('reader-annotations')
            js("document.getElementById('reader-export-options').open=true")
            default=download('reader-download-markdown');text=default.read_text();assert 'Disposable reader export comment' not in text and 'full costs of one academic year' in text and 'a598ad20db0b' in text and 'finding-level' in text
            js("document.getElementById('export-personal-annotations').checked=true;document.getElementById('export-personal-annotations').dispatchEvent(new Event('change'))")
            private=download('reader-download-markdown');assert 'Disposable reader export comment' in private.read_text()
            pdf=download('reader-download-pdf');assert '-v2-reader-r1-' in pdf.name and pdf.read_bytes().startswith(b'%PDF-')
            js("document.getElementById('reader-export-options').open=false")
            click('reader-show-pdf');wait("document.querySelector('.pdf-page>img')?.naturalWidth>0");js("document.querySelector('.pdf-controls').scrollIntoView({block:'start'})");shot('pdf-reader-cover')
            select('pdf-page','1');wait("document.querySelector('.pdf-page')?.dataset.page==='1' && document.querySelector('.pdf-page>img')?.naturalWidth>0");shot('pdf-reader-second-page')
            click('reader-show-report');wait("!!document.querySelector('.canonical-table')")
            versions=js("[...document.getElementById('canonical-version').options].map(o=>({key:o.value,label:o.textContent}))")
            latest=versions[0]['key'];earlier=next(v['key'] for v in versions if v['label'].startswith('Report v1'))
            select('canonical-version',earlier);wait("document.querySelector('.canonical-report').dataset.canonical==="+json.dumps(earlier)+" && !!document.querySelector('.canonical-table') && document.getElementById('reader-status').textContent.includes('Viewing saved report')")
            oldpdf=download('reader-download-pdf');assert '-v1-reader.pdf' in oldpdf.name
            oldmd=download('reader-download-markdown');assert '-v1-detailed.md' in oldmd.name and 'Canonical report v1' in oldmd.read_text() and '18b0e08c8147' in oldmd.read_text()
            assert js("!document.getElementById('export-personal-annotations').checked")
            select('reader-sections','canonical-at-a-glance');time.sleep(.7)
            select('canonical-version',latest);wait("document.querySelector('.canonical-report').dataset.canonical==="+json.dumps(latest)+" && !!document.querySelector('.canonical-table') && document.getElementById('reader-status').textContent.includes('Viewing saved report')")
            for width in (1440,820,390):
                window.resize(width,1000 if width>390 else 740);wait('innerWidth',lambda v:v==width)
                for scale in (1,1.15,1.3,1.5):
                    js("document.documentElement.style.setProperty('--text-scale',"+str(scale)+")")
                    wait("document.getElementById('research-dialog').scrollWidth<=document.getElementById('research-dialog').clientWidth")
                    assert js("document.querySelector('.canonical-reading').clientWidth>0 && document.querySelector('.reader-options>summary').getBoundingClientRect().width>0");alignment()
                js("document.querySelector('.report-heading').scrollIntoView({block:'start'})");shot('width-'+str(width)+'-large-text')
            window.resize(1440,1000);wait('innerWidth===1440');js("document.documentElement.style.setProperty('--text-scale',1)");select('reader-sections','canonical-regional-guides-to-costs');time.sleep(.8)
            position_identity=latest+':'+js("document.querySelector('.canonical-report').dataset.document");expected=preferences(workspace)['positions'][position_identity];assert expected['anchor'].startswith('regional-guides'),expected
            click('close-research');wait("!document.getElementById('research-dialog').open")
            assert context==js("JSON.stringify({url:location.href,map:document.querySelector('.leaflet-map-pane').style.transform,left:getComputedStyle(document.documentElement).getPropertyValue('--results-width'),right:getComputedStyle(document.documentElement).getPropertyValue('--inspector-width')})")
            click('read-country-report');wait("!!document.querySelector('.canonical-report .canonical-table') && document.getElementById('reader-status').textContent.includes('loaded')");time.sleep(.4)
            assert preferences(workspace)['positions'][position_identity]==expected
            shot('restored-reading-position');passed.append(True)
            atomic_json(output/'desktop-check.local.json',{'passed':True,'layouts':12,'exports':names,'position':expected,'versions':versions})
            print('Native desktop passed: country actions, divider keyboard resizing, sidebar, widths, annotation-space recovery, sections, PDF/Markdown downloads, optional private comments, version exports, 12 layouts and map/reading return.',flush=True)
        except Exception:traceback.print_exc();shot('failure')
        finally:window.confirm_close=False;window.destroy()
    try:webview.start(work,gui='qt');assert passed
    finally:watchdog.cancel();server.shutdown();server.server_close()
    for path in output.rglob('*'):
        if path.is_file():path.chmod(0o600)


if __name__=='__main__':main()
