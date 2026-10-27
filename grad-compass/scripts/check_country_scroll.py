"""Native country-list scroll regression, using an empty disposable profile only."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback

APP = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(APP), str(APP / 'scripts')]
from web.local import create_local_server, private_directory, atomic_json
from web.profiles import LocalProfiles
from web.server import STATIC_FILES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--app-script', type=Path, help='Optional historical app.js for regression reproduction')
    args = parser.parse_args()
    runtime = args.runtime.absolute()
    marker = runtime / '.country-scroll-check'
    if runtime.exists() and not marker.is_file():
        raise SystemExit('Refusing unmarked storage')
    private_directory(runtime)
    marker.touch(mode=0o600)
    profiles = LocalProfiles(runtime / 'local')
    workspace = profiles.workspace
    before = workspace.research.snapshot()
    decisions = workspace.country_decisions()
    if args.app_script:
        STATIC_FILES['/app.js'] = (args.app_script.absolute(), 'text/javascript; charset=utf-8')
    server = create_local_server(workspace, profiles=profiles)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    os.environ['QT_API'] = 'pyqt6'
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows'
    import webview
    from preview_capture import PreviewCapture
    output = private_directory(runtime / 'screenshots')
    window = webview.create_window('Grad Compass — isolated country scroll check',
                                  f'http://127.0.0.1:{server.server_port}/',
                                  width=1440, height=1000, min_size=(390, 640))
    capture = PreviewCapture(window, output, prefix='country-scroll-')
    passed = []
    checks = []
    watchdog = threading.Timer(180, lambda: os._exit(1))
    watchdog.daemon = True
    watchdog.start()

    def work():
        def js(code): return window.run_js(code)

        def wait(code):
            until = time.monotonic() + 25
            while time.monotonic() < until:
                if js(code): return
                time.sleep(.1)
            raise AssertionError(code)

        def click(identity):
            js('document.getElementById(' + json.dumps(identity) + ').click()')

        def shot(name):
            time.sleep(.3)
            capture.save(name)

        def visible(code):
            selector = json.dumps('.country-card[data-country="' + code + '"]')
            return js("(()=>{const list=document.getElementById('results'),card=list.querySelector(" + selector + ");"
                      "if(!card)return false;const a=card.getBoundingClientRect(),b=list.getBoundingClientRect();"
                      "return a.bottom>b.top+2 && a.top<b.bottom-2 && a.right>b.left+2 && a.left<b.right-2;})()")

        def select(code, keyboard=False):
            selector = json.dumps('.leaflet-overlay-pane [data-country="' + code + '"]')
            if keyboard:
                js("document.querySelector(" + selector + ").dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))")
            else:
                js("document.querySelector(" + selector + ").dispatchEvent(new MouseEvent('click',{bubbles:true}))")
            wait("document.getElementById('country').value===" + json.dumps(code) + " && !!document.querySelector('#inspector h2')")
            assert visible(code), ('Selected country not visible', code, js("({top:results.scrollTop,left:results.scrollLeft})"))

        try:
            window.events.loaded.wait(25)
            wait("!!document.querySelector('.leaflet-overlay-pane [data-country=ZAF]') && !!window.GradCompassResearch")
            click('countries-mode')
            wait("document.querySelectorAll('.country-card').length>200")
            # A selected card remains visible after the list is rebuilt.
            js("document.querySelector('.country-card[data-country=ZAF]').scrollIntoView({block:'center'})")
            assert js('results.scrollTop>100')
            js("document.querySelector('.country-card[data-country=ZAF]').click()")
            wait("document.getElementById('country').value==='ZAF' && !!document.querySelector('#inspector h2')")
            assert visible('ZAF'), 'Card selection reset the list instead of retaining the selected country'
            checks.append('card selection retains selected country')
            shot('selected-card')
            # Refreshes preserve the reader's scroll, even away from the focused country.
            js('results.scrollTop=1000')
            top = js('results.scrollTop')
            js("window.dispatchEvent(new Event('grad-compass:personal-updated'))")
            assert abs(js('results.scrollTop') - top) < 2
            checks.append('background list refresh preserves scroll')
            select('USA')
            checks.append('map click reveals offscreen country')
            select('NOR', keyboard=True)
            checks.append('map keyboard selection reveals country')
            click('nav-back')
            wait("document.getElementById('country').value==='USA' && !!document.querySelector('#inspector h2')")
            assert visible('USA')
            checks.append('history navigation reveals country')
            shot('map-selection')
            for width, scale in [(1440, 1.5), (390, 1.5)]:
                window.resize(width, 1000 if width > 390 else 740)
                wait('innerWidth===' + str(width))
                js("document.documentElement.style.setProperty('--text-scale'," + str(scale) + ')')
                select('ZAF')
                if width == 390:
                    assert js('results.scrollLeft>100')
                    # The existing narrow layout overlays details on the list.
                    js("document.querySelector('#inspector .inspector-close').click()")
                    wait("document.getElementById('inspector').hidden")
                    assert visible('ZAF')
                shot(str(width) + '-large-text')
                checks.append(str(width) + 'px large-text selection visible')
            time.sleep(1)
            state = js("JSON.stringify({country:document.getElementById('country').value,top:results.scrollTop,left:results.scrollLeft,url:location.href})")
            click('select-countries')
            js("document.querySelector('.leaflet-overlay-pane [data-country=CAN]').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
            assert js("document.getElementById('country-selection-count').textContent==='1 selected'")
            assert js("JSON.stringify({country:document.getElementById('country').value,top:results.scrollTop,left:results.scrollLeft,url:location.href})") == state
            checks.append('bulk selection leaves focus, scroll and location unchanged')
            assert workspace.research.snapshot() == before
            assert workspace.country_decisions() == decisions
            atomic_json(output / 'receipt.local.json', {'passed': True, 'checks': checks, 'research_unchanged': True, 'decisions_unchanged': True})
            passed.append(True)
            print('Country scroll checks passed: ' + '; '.join(checks), flush=True)
        except Exception:
            traceback.print_exc()
            shot('failure')
        finally:
            watchdog.cancel()
            window.confirm_close = False
            window.destroy()

    try:
        webview.start(work, gui='qt', private_mode=True, storage_path=str(runtime / 'browser'))
    finally:
        server.shutdown()
        server.server_close()
    assert passed, 'Native country scroll checks failed'


if __name__ == '__main__':
    main()
