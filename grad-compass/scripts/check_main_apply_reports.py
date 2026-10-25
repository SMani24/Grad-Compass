"""Read-only native receipt through country cards, report navigation and downloads.

Reading-position writes are suppressed for this owner-data probe. All write tests
and nonempty annotation/recovery checks belong in marked disposable profiles.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback

APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'scripts')]
from web.local import create_local_server,private_directory,atomic_json
from web.profiles import LocalProfiles
from web import report_packages as reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local-dir',type=Path,default=APP.parent/'grad-compass-workspace/runtime/local')
    parser.add_argument('--screenshots',type=Path,required=True)
    parser.add_argument('--restart',action='store_true')
    parser.add_argument('--expect-metadata',action='append',default=[],metavar='COUNTRY=SHA256')
    parser.add_argument('--country',action='append',default=[],help='Countries to verify; defaults to DEU/CAN/BEL')
    parser.add_argument('--require-photo',action='append',default=[],metavar='COUNTRY')
    parser.add_argument('--narrow',action='store_true',help='Also inspect the reader at a 390px window, retaining the owner text size')
    parser.add_argument('--allow-findings',action='store_true',help='Allow honestly labelled received findings when no prepared package is published')
    args=parser.parse_args()
    profiles=LocalProfiles(args.local_dir);w=profiles.workspace
    state=profiles.snapshot();active=next(p for p in state['profiles'] if p['id']==state['active_id'])
    if active['name']!='Main-Apply':raise SystemExit('Open Main-Apply before collecting this owner receipt; do not switch profiles for a test')
    personal=('country-decisions.json','display-preferences.json','panel-widths.json','research-selection.json','report-annotations.json','report-reading.json')
    def inventory():return {n:(w.directory/n).read_bytes() if (w.directory/n).exists() else None for n in personal}
    before=inventory();research=w.research.snapshot()
    protected={str(p.relative_to(w.directory)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in (w.directory/'reports').rglob('*') if p.is_file()}
    server=create_local_server(w,profiles=profiles);threading.Thread(target=server.serve_forever,daemon=True).start()
    # Establish expectations after ordinary startup receipt, not from a stale
    # pre-startup catalog. No manual import or forced report selection is used.
    expected=dict(value.split('=',1) for value in args.expect_metadata)
    until=time.monotonic()+25
    while True:
        available=reports.catalog(w)['reports']
        latest={c:next((r for r in available if r['metadata']['country_code']==c and (r['model']['kind']=='prepared_report' or args.allow_findings)),None) for c in (args.country or ('DEU','CAN','BEL'))}
        if all(latest.values()) and all(latest.get(code,{}).get('edition')==digest for code,digest in expected.items()):break
        if time.monotonic()>until:raise AssertionError('Expected finalized packages were not received by normal startup/polling')
        time.sleep(.2)
    os.environ['QT_API']='pyqt6'
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from desktop_downloads import DesktopDownloads
    from preview_capture import PreviewCapture
    out=private_directory(args.screenshots);downloads=private_directory(out/'downloads');names=[]
    window=webview.create_window('Grad Compass',f'http://127.0.0.1:{server.server_port}/',width=1440,height=1000,min_size=(390,640))
    capture=PreviewCapture(window,out,prefix='main-apply-'+('restart-' if args.restart else ''))
    def choose(name):names.append(name);return str(downloads/name)
    handler=DesktopDownloads(window,choose_path=choose);passed=[]
    watchdog=threading.Timer(240,lambda:os._exit(1));watchdog.daemon=True;watchdog.start()
    def work():
        def js(code):return window.run_js(code)
        def wait(code):
            until=time.monotonic()+30
            while time.monotonic()<until:
                value=js(code)
                if value:return value
                time.sleep(.1)
            raise AssertionError((code,js("document.getElementById('reader-status')?.textContent || document.getElementById('research-message')?.textContent")))
        def click(name):js('setTimeout(()=>document.getElementById('+json.dumps(name)+')?.click(),0);void 0')
        def shot(name):
            time.sleep(.6)  # Qt must paint the completed DOM before QWidget.grab().
            capture.save(name)
        def select(name,value):js('document.getElementById('+json.dumps(name)+').value='+json.dumps(value)+';document.getElementById('+json.dumps(name)+').dispatchEvent(new Event("change"))')
        def download(name):
            old=len(names);click(name);until=time.monotonic()+30
            while time.monotonic()<until:
                if len(names)>old and (downloads/names[-1]).is_file():return downloads/names[-1]
                time.sleep(.1)
            raise AssertionError('Native download did not finish')
        def loaded(report):
            wait("document.querySelector('.canonical-report')?.dataset.canonical==="+json.dumps(report['key'])+" && document.getElementById('reader-status')?.textContent.includes('loaded')")
            assert js("document.querySelector('.canonical-report').dataset.request==="+json.dumps(report['metadata']['request']['id']))
            assert js("document.querySelector('.canonical-report').dataset.edition==="+json.dumps(report['edition']))
        try:
            handler.install_requested.emit();assert handler.installed.wait(10)
            window.events.loaded.wait(25);wait('!!window.GradCompassResearch && !!window.GradCompassWorkspace')
            # Preserve owner positions, not an alternate selection/data route.
            js("(()=>{const original=window.fetch;window.fetch=(url,options)=>String(url)==='/api/reports/reading' && options?.method==='POST'?original('/api/reports/reading',{cache:'no-store'}):original(url,options);})();void 0")
            # Requests starts with the latest saved request, which may legitimately
            # still have only received findings. Country cards below must select
            # the latest prepared package for their own request.
            click('countries-mode');click('open-research');wait("!!document.querySelector('.canonical-report') && document.getElementById('reader-status')?.textContent.includes('loaded')")
            assert js("document.querySelector('.canonical-report').dataset.canonical") in {r['key'] for r in reports.catalog(w)['reports']}
            click('close-research');wait("!document.getElementById('research-dialog').open")
            receipt={}
            for code,r in latest.items():
                click('countries-mode');select('country','');select('country-list-scope','all')
                js("document.getElementById('search').value="+json.dumps(r['country_name'])+";document.getElementById('search').dispatchEvent(new Event('input'))")
                wait("!!document.querySelector('.country-card[data-country="+code+"]')")
                js("document.querySelector('.country-card[data-country="+code+"]').click()")
                wait("!!document.getElementById('read-country-report')")
                wait("document.querySelector('.country-report-availability').textContent.includes("+json.dumps(r['model']['version_label'])+")");shot(code.lower()+'-map-action')
                click('read-country-report');loaded(r)
                if r.get('reader'):assert js("document.querySelector('.canonical-report').dataset.document==="+json.dumps(r['reader']['id']))
                assert js("document.getElementById('reader-show-report').disabled==="+json.dumps(not bool(r.get('reader')))+" && !document.querySelector('.report-package-error')")
                selected_review=(r.get('reader') or {}).get('metadata',{}).get('factual_review',r['metadata']['canonical_factual_review'])
                assert js("document.querySelector('.report-badges').textContent.includes("+json.dumps(selected_review['state'].replace('_',' '))+")")
                assert js("document.getElementById('inbox-errors').hidden")
                assert js("document.querySelector('.report-coverage').closest('#reader-report-details')!==null")
                assert js("[...document.querySelectorAll('.canonical-reading>.report-section h2')].every(n=>!n.textContent.includes('Seven-topic coverage'))")
                assert js("document.querySelectorAll('.report-source a').length===new Set([...document.querySelectorAll('.report-source a')].map(a=>a.href)).size")
                if code in args.require_photo:
                    wait("document.querySelector('.report-photo img')?.naturalWidth>0")
                    assert r.get('assets',{}).get('photo'),'Delivered photograph missing'
                    assert js("!!document.querySelector('.report-photo figcaption a')"),'Photo attribution link missing'
                shot(code.lower()+('-prepared-overview' if r.get('reader') else '-received-findings'))
                if not r.get('reader'):
                    js("document.getElementById('reader-report-details').open=true;document.querySelector('.report-coverage').open=true")
                    js("document.querySelector('.report-coverage').scrollIntoView({block:'center'})")
                    shot(code.lower()+'-supplied-coverage')
                    js("document.getElementById('reader-report-details').open=false;document.getElementById('research-dialog').scrollTop=0")
                # Country navigation must agree with the card entry point.
                other=next((c for c in latest if c!=code),None)
                if other:select('report-country-navigation',other);loaded(latest[other])
                select('report-country-navigation',code);loaded(r)
                click('reader-full-report');wait("document.querySelector('.canonical-report').dataset.readingEdition!=='reader'");shot(code.lower()+'-detailed')
                js("document.getElementById('reader-export-options').open=true")
                md=download('reader-download-markdown');pdf=download('reader-download-pdf')
                assert r['metadata']['canonical_document']['sha256'] in md.read_text()
                from web.report_composition import markdown_sections,source_inventory
                detail=r.get('detailed');tree=detail['content'] if detail else r['content']
                for chunk in markdown_sections((detail['document_bytes'] if detail else r['canonical_bytes']).decode()):
                    if chunk['role']=='research':assert chunk['markdown'] in md.read_text()
                for source in source_inventory(r,tree):assert source['url'] in md.read_text()
                assert md.read_text().index('## Sources')<md.read_text().index('## Report details and technical appendix')
                assert not js("!!document.querySelector('.report-locator')")
                receipt[code]={'request_id':r['metadata']['request']['id'],'key':r['key'],'metadata_sha256':r['edition'],'canonical_revision_id':r['metadata']['canonical_document']['revision_id'],'canonical_sha256':r['metadata']['canonical_document']['sha256'],'report_version':r['metadata']['canonical_document']['revision_number'],'reader_revision':r['reader']['metadata']['revision_number'] if r.get('reader') else None,'reader_sha256':r['reader']['metadata']['sha256'] if r.get('reader') else None,'detailed_revision':r['detailed']['metadata']['revision_number'] if r.get('detailed') else r['metadata']['canonical_document']['revision_number'],'detailed_sha256':r['detailed']['metadata']['sha256'] if r.get('detailed') else r['metadata']['canonical_document']['sha256'],'review':r['metadata']['canonical_factual_review']['state'],'reader_review':r['reader']['metadata']['factual_review']['state'] if r.get('reader') else None,'human':r['metadata']['human_approval']['state'],'pdf':pdf.name,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'markdown':md.name,'markdown_sha256':hashlib.sha256(md.read_bytes()).hexdigest(),'annotations_readback':reports.annotations(w,r['key']),'locator_omitted':True}
                receipt[code]['photo']=r.get('assets',{}).get('photo')
                receipt[code]['kind']=r['model']['kind'];receipt[code]['coverage']=r['model']['coverage']
                click('reader-show-pdf');wait("document.querySelector('.pdf-page>img')?.naturalWidth>0");shot(code.lower()+'-pdf')
                if args.narrow:
                    click('reader-show-report' if r.get('reader') else 'reader-full-report');wait("document.querySelector('.canonical-report').dataset.readingEdition==="+json.dumps('reader' if r.get('reader') else 'canonical'))
                    window.resize(390,740);wait('innerWidth===390');js("document.getElementById('research-dialog').scrollTop=0")
                    assert js('document.body.scrollWidth<=innerWidth')
                    shot(code.lower()+'-narrow-overview')
                    if code in args.require_photo:
                        js("document.querySelector('.photo-attribution').open=true")
                        assert js("getComputedStyle(document.querySelector('.report-photo figcaption')).position==='static'")
                        assert js("getComputedStyle(document.querySelector('.report-photo figcaption a')).color!=='rgb(255, 255, 255)'")
                        shot(code.lower()+'-narrow-photo-credits')
                        js("document.querySelector('.photo-attribution').open=false")
                    window.resize(1440,1000);wait('innerWidth===1440')
                # Explicit result history remains a findings view, with honest labels.
                if code=='DEU':
                    select('research-result-revision','1')
                    wait("document.querySelector('.canonical-report')?.dataset.readingEdition==='canonical' && document.getElementById('reader-status')?.textContent.includes('loaded')")
                    click('reader-full-report');wait("document.getElementById('reader-status').textContent.includes('Received findings loaded')")
                    assert js("[...document.querySelectorAll('.canonical-reading [data-report-block]')].filter(n=>n.textContent.startsWith('Finding field: ')).every(n=>n.closest('details') && !n.closest('details').open)")
                    shot('deu-explicit-historical-findings')
                    assert js("!!document.getElementById('open-prepared-report') && !document.getElementById('request-dialog').open");click('open-prepared-report');loaded(r)
                click('close-research');wait("!document.getElementById('research-dialog').open")
            assert inventory()==before,'Personal overlays changed';assert w.research.snapshot()==research,'Research history changed'
            assert all((hashlib.sha256((w.directory/name).read_bytes()).hexdigest(),(w.directory/name).stat().st_mtime_ns)==value for name,value in protected.items()),'Existing producer artifact changed'
            from web.inbox import InboxReceiver
            replay=InboxReceiver(w).check();assert replay['received']==0 and not replay['errors'],replay
            result={'passed':True,'profile':active,'countries':receipt,'personal_overlay_bytes_unchanged':True,'research_unchanged':True,'protected_original_files':len(protected),'protected_original_bytes_and_mtimes_unchanged':True,'replay':replay,'normal_country_card_and_selector_routes':True,'qa_position_writes_suppressed':True,'catalog_errors':reports.catalog(w)['errors']}
            assert not result['catalog_errors'],result['catalog_errors']
            atomic_json(out/('restart.local.json' if args.restart else 'normal.local.json'),result)
            passed.append(True);print('Main-Apply card/selector/default/history/native export receipt passed for '+','.join(latest)+'.',flush=True)
        except Exception:traceback.print_exc();capture.save('failure')
        finally:watchdog.cancel();window.confirm_close=False;window.destroy()
    try:webview.start(work,gui='qt',private_mode=True,storage_path=str(out/'browser'))
    finally:server.shutdown();server.server_close()
    assert passed,'Main-Apply native verification failed'
    for path in out.rglob('*'):
        if path.is_file():path.chmod(0o600)


if __name__=='__main__':main()
