"""One real desktop reader across countries; mutations require a marked disposable copy."""
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
from web import report_packages as reports
from web.report_pdf import ensure_pdf,page_data
from web.report_export import markdown,filename


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',required=True,type=Path);p.add_argument('--screenshots',required=True,type=Path);p.add_argument('--restart',action='store_true');p.add_argument('--countries',nargs='+',default=['BEL','DEU','CAN']);p.add_argument('--findings',action='store_true');args=p.parse_args()
    if not (args.runtime/'.shared-report-review-copy').is_file():raise SystemExit('Use a marked disposable integration copy')
    profiles=LocalProfiles(args.runtime);workspace=profiles.workspace
    initial=workspace.research.snapshot();decisions=workspace.country_decisions()
    candidates=reports.catalog(workspace)['reports'];latest={code:next(r for r in candidates if r['metadata']['country_code']==code and r['model']['kind']==('received_findings' if args.findings else 'prepared_report')) for code in args.countries}
    server=create_local_server(workspace,profiles=profiles);threading.Thread(target=server.serve_forever,daemon=True).start()
    os.environ['QT_API']='pyqt6';os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from preview_capture import PreviewCapture
    output=private_directory(args.screenshots);exports=private_directory(output/'exports')
    window=webview.create_window('Grad Compass — shared country reports (isolated review)',f'http://127.0.0.1:{server.server_port}/',width=1440,height=1000,min_size=(390,640));capture=PreviewCapture(window,output,prefix='2026-10-21-shared-'+('restart-' if args.restart else ''));passed=[]
    watchdog=threading.Timer(240,lambda:os._exit(1));watchdog.daemon=True;watchdog.start()
    def work():
        def js(code):return window.run_js(code)
        def wait(code):
            end=time.monotonic()+30
            while time.monotonic()<end:
                v=js(code)
                if v:return v
                time.sleep(.1)
            raise AssertionError(code)
        def click(identity):js('setTimeout(()=>document.getElementById('+json.dumps(identity)+')?.click(),0);void 0')
        def choose(identity,value):js('document.getElementById('+json.dumps(identity)+').value='+json.dumps(value)+';document.getElementById('+json.dumps(identity)+').dispatchEvent(new Event("change"))')
        def shot(name):time.sleep(.6);capture.save(name)
        records={}
        try:
            window.events.loaded.wait(25);wait('!!window.GradCompassWorkspace && !!window.GradCompassResearch')
            for code,report in latest.items():
                js('window.GradCompassResearch.openRequests('+json.dumps(report['metadata']['request']['id'])+',null,'+json.dumps(report['finding']['finding_id'])+');void 0')
                wait("document.querySelector('.canonical-report')?.dataset.canonical==="+json.dumps(report['key'])+" && document.getElementById('reader-status')?.textContent.includes('loaded')")
                assert js("document.querySelector('.canonical-report').dataset.readingEdition==="+json.dumps('canonical' if args.findings else 'reader'))
                if args.findings:assert js("document.getElementById('reader-show-report').disabled && document.querySelector('.report-capability-note').textContent.includes('has not been published')")
                assert js("!!(document.querySelector('.reader-view-switch') && document.getElementById('reader-export-options') && document.getElementById('reader-annotations'))")
                assert js("document.querySelectorAll('.inline-evidence').length>0")
                js("document.getElementById('research-dialog').scrollTop=0");shot(code.lower()+'-overview')
                if code!='BEL':assert js("document.querySelector('.report-photo').textContent.includes('Country photograph not provided')")
                js("document.querySelector('.inline-evidence').click()");wait("document.getElementById('report-source-dialog').open");assert js("document.querySelectorAll('#report-source-dialog a[href^=https]').length>0");shot(code.lower()+'-sources');click('close-report-sources')
                click('reader-full-report');wait("document.querySelector('.canonical-report').dataset.readingEdition!=='reader'")
                assert js("[...document.querySelectorAll('.report-section')].every(s=>{const h=s.querySelector('h2');return [...s.children].filter(n=>n.matches('.canonical-passage,.report-terms,.report-table-wrap')).every(n=>Math.abs(n.getBoundingClientRect().left-h.getBoundingClientRect().left)<2);})")
                section=js("[...document.querySelectorAll('.report-section')].find(s=>s.querySelector('table'))?.id")
                if section:choose('reader-sections',section)
                shot(code.lower()+'-full-table')
                pdf=ensure_pdf(workspace,report);target=exports/pdf['filename'];target.write_bytes(pdf['path'].read_bytes());(exports/filename(report,'-detailed.md')).write_bytes(markdown(workspace,report))
                for page in range(page_data(workspace,report,0)['pages']):(exports/(code.lower()+'-pdf-page-'+str(page+1)+'.png')).write_bytes(page_data(workspace,report,page,image=True))
                records[code]={'key':report['key'],'edition':report['edition'],'canonical_sha256':report['metadata']['canonical_document']['sha256'],'reader_sha256':report['reader']['metadata']['sha256'] if report.get('reader') else None,'pdf_sha256':pdf['sha256'],'review':report['metadata']['canonical_factual_review'],'human':report['metadata']['human_approval']}
                if code==args.countries[-1]:
                    if not args.restart:
                        js("(()=>{const w=document.createTreeWalker(document.querySelector('.canonical-reading'),NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){if(n.textContent.trim().length<35 || n.parentElement.closest('mark,button,a') || !n.parentElement.closest('[data-report-block]'))continue;const r=document.createRange();r.setStart(n,0);r.setEnd(n,30);getSelection().removeAllRanges();getSelection().addRange(r);document.querySelector('.canonical-reading').dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));return;}})()")
                        wait("!document.getElementById('reader-comment').disabled");click('reader-comment');wait("!!document.getElementById('new-annotation-comment-text')");js("document.getElementById('new-annotation-comment-text').value='Disposable shared-country annotation'");click('save-new-annotation');wait("document.getElementById('reader-status').textContent.includes('saved privately')")
                    else:
                        click('reader-annotations');wait("document.querySelector('.annotation-panel').textContent.includes('Disposable shared-country annotation') || [...document.querySelectorAll('.annotation-panel textarea')].some(n=>n.value==='Disposable shared-country annotation')")
                    click('reader-show-pdf');wait("document.querySelector('.pdf-page>img')?.naturalWidth>0");shot(code.lower()+'-pdf')
                    click('reader-full-report' if args.findings else 'reader-show-report');wait("document.querySelector('.canonical-report').dataset.readingEdition==="+json.dumps('canonical' if args.findings else 'reader'))
                    for width in (1440,820,390):
                        window.resize(width,1000 if width>390 else 740);wait('innerWidth==='+str(width))
                        for scale in (1,1.15,1.3,1.5):
                            js("document.documentElement.style.setProperty('--text-scale',"+str(scale)+")")
                            wait("document.getElementById('research-dialog').scrollWidth<=document.getElementById('research-dialog').clientWidth")
                            assert js("document.querySelector('.canonical-reading').clientWidth>0 && document.querySelector('.reader-options>summary').getBoundingClientRect().width>0")
                        js("document.getElementById('research-dialog').scrollTop=0");shot(code.lower()+'-width-'+str(width)+'-large-text')
                    window.resize(1440,1000);wait('innerWidth===1440');js("document.documentElement.style.setProperty('--text-scale',1)")
                click('close-research');wait("!document.getElementById('research-dialog').open")
            assert workspace.research.snapshot()==initial;assert workspace.country_decisions()==decisions
            atomic_json(output/('desktop-restart.local.json' if args.restart else 'desktop.local.json'),{'passed':True,'countries':records,'research_unchanged':True,'decisions_unchanged':True})
            passed.append(True);print('Shared normal-desktop reader passed: '+','.join(args.countries)+', '+('available findings/PDF' if args.findings else 'concise/full/PDF')+', shared controls, source references, missing-photo fallback, tables, narrow text and '+('annotation restart.' if args.restart else 'version-bound comment.'),flush=True)
        except Exception:traceback.print_exc();shot('failure')
        finally:watchdog.cancel();window.confirm_close=False;window.destroy()
    try:webview.start(work,gui='qt',private_mode=True,storage_path=str(args.runtime/'shared-browser'))
    finally:server.shutdown();server.server_close()
    assert passed,'Shared country desktop verification failed'
    for path in output.rglob('*'):
        if path.is_file():path.chmod(0o600)


if __name__=='__main__':main()
