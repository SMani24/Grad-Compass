"""Native desktop check; requires an explicitly marked disposable report copy."""
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
from web.profiles import LocalProfiles
from web.local import create_local_server,private_directory,atomic_json


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--screenshots',type=Path,required=True);parser.add_argument('--restart',action='store_true');args=parser.parse_args()
    if not args.runtime.joinpath('.canonical-review-copy').is_file():raise SystemExit('Use an explicitly marked disposable copy; this check saves test annotations and feedback')
    class CopySink:
        def copy_text(self,value):self.value=value  # Keep test instructions out of the owner's clipboard.
    profiles=LocalProfiles(args.runtime);server=create_local_server(profiles.workspace,profiles=profiles,clipboard=CopySink());worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    os.environ['QT_API']='pyqt6';os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from preview_capture import PreviewCapture
    from desktop_downloads import DesktopDownloads
    screenshots=private_directory(args.screenshots);window=webview.create_window('Grad Compass — canonical report check (isolated copy)',f'http://127.0.0.1:{server.server_port}/',width=1440,height=1000,min_size=(390,640));capture=PreviewCapture(window,screenshots,prefix='2026-10-20-canonical-'+('restart-' if args.restart else ''))
    from web.report_packages import catalog
    active_report=next(r for r in catalog(profiles.workspace)['reports'] if r['metadata']['country_code']=='BEL')
    from web.report_pdf import ensure_pdf
    expected_pdf=ensure_pdf(profiles.workspace,active_report)['filename']
    download_names=[];downloads_root=private_directory(screenshots/'isolated-downloads'/str(uuid4()))
    def download_path(name):download_names.append(name);return str(downloads_root/name)
    downloads=DesktopDownloads(window,choose_path=download_path)
    passed=[]
    def timeout():os._exit(1)
    watchdog=threading.Timer(240,timeout);watchdog.daemon=True;watchdog.start()
    def work():
        def js(code):return window.run_js(code)
        def wait(code,predicate=bool):
            end=time.monotonic()+30;value=None
            while time.monotonic()<end:
                value=js(code)
                if predicate(value):return value
                time.sleep(.1)
            raise AssertionError((code,value))
        def click(id):js('setTimeout(()=>document.getElementById('+json.dumps(id)+')?.click(),0);void 0')
        def shot(name):time.sleep(.3);capture.save(name)
        try:
            downloads.install_requested.emit();assert downloads.installed.wait(10)
            window.events.loaded.wait(25);wait("!!document.querySelector('.country-card[data-country=\"BEL\"]')");js("document.querySelector('.country-card[data-country=\"BEL\"]').click()");wait("!!document.getElementById('read-country-report')")
            context=js("JSON.stringify({url:location.href,map:document.querySelector('.leaflet-map-pane').style.transform,left:getComputedStyle(document.documentElement).getPropertyValue('--results-width'),right:getComputedStyle(document.documentElement).getPropertyValue('--inspector-width')})")
            click('read-country-report');wait("!!document.querySelector('.canonical-report .canonical-table')")
            assert js("document.querySelector('.canonical-report').dataset.canonical")
            assert js("!!document.querySelector('.canonical-report .report-locator img')")
            assert js("document.querySelectorAll('.inline-evidence').length>0")
            if args.restart:
                click('reader-download-pdf')
                end=time.monotonic()+30
                while time.monotonic()<end and (not download_names or not (downloads_root/expected_pdf).is_file()):time.sleep(.1)
                assert download_names==[expected_pdf]
                assert (downloads_root/download_names[0]).read_bytes().startswith(b'%PDF-')
                click('reader-annotations');wait("document.querySelectorAll('.saved-annotation').length>=2")
                assert 'Edited isolated report comment' in js("document.querySelector('.annotation-panel').textContent+Array.from(document.querySelectorAll('.annotation-panel textarea')).map(n=>n.value).join(' ')")
                assert js("!!document.getElementById('annotation-feedback-draft')")
                js("[...document.querySelectorAll('.annotation-location')].find(n=>n.textContent.includes('PDF page')).click()")
                wait("document.querySelector('.pdf-page')?.dataset.page==='1' && document.querySelectorAll('.pdf-mark').length>0")
                js("const zoom=document.querySelector('select[aria-label=\"PDF zoom\"]');zoom.value='3';zoom.dispatchEvent(new Event('change'))")
                assert js("document.querySelector('.pdf-page').clientWidth>document.querySelector('.pdf-viewport').clientWidth && document.getElementById('research-dialog').scrollWidth<=document.getElementById('research-dialog').clientWidth")
                js("document.querySelector('select[aria-label=\"PDF zoom\"]').value='1';document.querySelector('select[aria-label=\"PDF zoom\"]').dispatchEvent(new Event('change'))")
                shot('annotations-and-pdf');passed.append(True);print('Native restart passed: report/PDF highlights, edited comment, private draft and exact PDF location preserved.',flush=True);return
            wait("document.querySelector('.report-photo img')?.naturalWidth>0");shot('report-header')
            js("document.querySelector('[id*=canonical-funding]').scrollIntoView({block:'start'})");assert js("document.querySelector('.reader-toolbar').getBoundingClientRect().top>=0 && document.querySelector('.reader-toolbar').getBoundingClientRect().top<80");shot('funding-table')
            # Select across actual rich-text nodes; the same browser Range is used by mouse/keyboard selection.
            js("""(()=>{const b=document.querySelector('.canonical-table tbody tr:first-child td:nth-child(2) [data-report-block]');const w=document.createTreeWalker(b,NodeFilter.SHOW_TEXT),nodes=[];while(w.nextNode())nodes.push(w.currentNode);const r=document.createRange();r.setStart(nodes[0],0);r.setEnd(nodes[Math.min(1,nodes.length-1)],nodes[Math.min(1,nodes.length-1)].length);const s=getSelection();s.removeAllRanges();s.addRange(r);document.querySelector('.canonical-reading').dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));})()""")
            wait("!document.getElementById('reader-comment').disabled")
            js("window.__validPassage=getSelection().getRangeAt(0).cloneRange();const invalid=document.createRange();invalid.selectNodeContents(document.querySelector('.canonical-reading'));getSelection().removeAllRanges();getSelection().addRange(invalid);document.querySelector('.canonical-reading').dispatchEvent(new MouseEvent('mouseup',{bubbles:true}))")
            assert js("document.getElementById('reader-highlight').disabled"),'Unsupported selection must not reuse an earlier passage'
            js("getSelection().removeAllRanges();getSelection().addRange(window.__validPassage);document.querySelector('.canonical-reading').dispatchEvent(new MouseEvent('mouseup',{bubbles:true}))")
            click('reader-comment');wait("!!document.getElementById('new-annotation-comment-text')");js("document.getElementById('new-annotation-comment-text').value='Isolated report comment'")
            click('reader-annotations');click('reader-annotations');assert js("document.getElementById('new-annotation-comment-text').value")=='Isolated report comment'
            js("document.getElementById('canonical-version').dispatchEvent(new Event('change'))");assert js("document.getElementById('new-annotation-comment-text').value")=='Isolated report comment';assert js("document.getElementById('reader-status').textContent.includes('Save or cancel')")
            click('save-new-annotation');wait("document.getElementById('reader-status').textContent.includes('saved privately')")
            wait("document.querySelectorAll('.saved-annotation').length===1");js("document.querySelector('.saved-annotation textarea').value='Edited isolated report comment';document.querySelector('.saved-annotation .quiet-action').click()");wait("document.getElementById('reader-status').textContent==='Comment saved.'")
            js("document.querySelector('.annotation-location').click()");shot('report-highlight-and-comment')
            click('reader-show-pdf');wait("!!document.querySelector('.pdf-page') && document.querySelector('.pdf-page>img').naturalWidth>0");shot('pdf-cover')
            js("document.getElementById('pdf-page').value='1';document.getElementById('pdf-page').dispatchEvent(new Event('change'))");wait("document.querySelector('.pdf-page')?.dataset.page==='1' && document.querySelector('.pdf-page>img').naturalWidth>0")
            js("document.querySelector('.pdf-links a[href^=\"#pdf-page-\"]').click()");wait("Number(document.querySelector('.pdf-page')?.dataset.page)>1")
            js("document.getElementById('pdf-page').value='1';document.getElementById('pdf-page').dispatchEvent(new Event('change'))");wait("document.querySelector('.pdf-page')?.dataset.page==='1'")
            js("""(()=>{const words=[...document.querySelectorAll('.pdf-text-layer span')],a=words[3],b=words[6],r=document.createRange();r.setStart(a.firstChild,0);r.setEnd(b.firstChild,b.textContent.length);const s=getSelection();s.removeAllRanges();s.addRange(r);document.querySelector('.canonical-reading').dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));})()""")
            click('reader-highlight');wait("document.querySelectorAll('.saved-annotation').length===2");assert js("document.querySelectorAll('.pdf-mark').length>0");shot('pdf-highlight')
            js("document.querySelectorAll('.saved-annotation input[type=checkbox]').forEach(n=>{n.checked=true;n.dispatchEvent(new Event('change'))})");click('prepare-annotation-feedback');wait("!!document.getElementById('annotation-feedback-text')")
            assert 'SHA-256' in js("document.getElementById('annotation-feedback-text').value");assert 'PDF page 2' in js("document.getElementById('annotation-feedback-text').value");shot('feedback-preview')
            before=len(profiles.workspace.research.request('41b6af76-f27e-4c58-a3a8-b835101658f0')['feedback'])
            click('annotation-follow-up');wait("document.getElementById('request-dialog').open");assert js("document.getElementById('request-only').checked");assert 'SHA-256' in js("document.getElementById('request-context').value");click('cancel-request')
            assert len(profiles.workspace.research.request('41b6af76-f27e-4c58-a3a8-b835101658f0')['feedback'])==before
            click('send-annotation-feedback');wait("!!document.getElementById('research-handoff')")
            assert len(profiles.workspace.research.request('41b6af76-f27e-4c58-a3a8-b835101658f0')['feedback'])==before+1
            click('reader-show-report');wait("!!document.querySelector('.canonical-table')")
            # Twelve supported widths/text scales, including the annotation panel and tables.
            for width in (1440,820,390):
                window.resize(width,1000 if width>390 else 740);wait('innerWidth',lambda v:v==width)
                for scale in (1,1.15,1.3,1.5):
                    js("document.documentElement.style.setProperty('--text-scale',"+str(scale)+")");time.sleep(.05)
                    assert js("document.getElementById('research-dialog').scrollWidth<=document.getElementById('research-dialog').clientWidth"),(width,scale,'reader overflow')
            js("document.querySelector('.canonical-report .report-heading').scrollIntoView({block:'start'})");shot('narrow-large-text')
            click('close-research');wait("!document.getElementById('research-dialog').open")
            window.resize(1440,1000);wait('innerWidth',lambda v:v==1440);js("document.documentElement.style.setProperty('--text-scale',1)")
            assert js("JSON.stringify({url:location.href,map:document.querySelector('.leaflet-map-pane').style.transform,left:getComputedStyle(document.documentElement).getPropertyValue('--results-width'),right:getComputedStyle(document.documentElement).getPropertyValue('--inspector-width')})")==context
            passed.append(True);print('Native report check passed: canonical visuals/citations, screen and PDF selection/highlights/comments, edited comment, explicit feedback/follow-up preview, unchanged preferences and exact map return; 12 layouts.',flush=True)
        except Exception:traceback.print_exc();shot('failure')
        finally:window.destroy()
    try:webview.start(func=work,gui='qt',private_mode=True,storage_path=str(args.runtime/'browser'))
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5);watchdog.cancel()
        for path in screenshots.glob('*.png'):path.chmod(0o600)
    if not passed:raise SystemExit(1)
    atomic_json(screenshots/('restart.local.json' if args.restart else 'desktop.local.json'),{'passed':True,'isolated':True})


if __name__=='__main__':main()
