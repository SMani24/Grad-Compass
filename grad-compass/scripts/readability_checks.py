"""Exercise real settings controls, persistence, and layout at each supported size."""
import json
import time


def verify_readability(window, directory, capture=None):
    def run(source):
        return window.run_js(source)

    def wait(check, source, label):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            actual = json.loads(run(source))
            if check(actual):
                return actual
            time.sleep(.05)
        raise AssertionError(f"Readability check failed ({label}): {actual}")

    def click(name):
        run(f"document.getElementById({json.dumps(name)}).click()")

    def screenshot(name):
        if capture:
            time.sleep(.6)
            capture(name)

    def choose(size):
        click("open-settings")
        wait(lambda state: state, "JSON.stringify(!document.getElementById('text-size').disabled)", "preference loaded")
        run(f"document.getElementById('text-size').value={json.dumps(size)};document.getElementById('text-size').dispatchEvent(new Event('change'))")
        wait(lambda state: state, "JSON.stringify(!document.getElementById('text-size').disabled && document.getElementById('settings-status').textContent.startsWith('Saved'))", "preference saved")
        assert json.loads((directory / "display-preferences.json").read_text())["text_size"] == size
        run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
        assert run("document.getElementById('settings-dialog').open") is False

    def check_layout(view):
        time.sleep(.3)
        state = json.loads(run("""JSON.stringify((() => {
            const rect = selector => { const r=document.querySelector(selector).getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}; };
            const controls = [...document.querySelectorAll('.topbar button,.topbar .brand,.view-switch')].map(el => {const r=el.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight;});
            const panel=rect('.results-panel'), header=rect('.topbar'), list=rect('.list-container');
            return {controls:controls.every(Boolean),panel,header,list,width:innerWidth,height:innerHeight,zoom:rect('.leaflet-control-zoom'),overflow:document.body.scrollWidth>innerWidth,
                view:document.getElementById('map-view').getAttribute('aria-pressed') === 'true' ? 'map' : 'list',
                root:parseFloat(getComputedStyle(document.documentElement).fontSize),card:parseFloat(getComputedStyle(document.querySelector('.university-name')).fontSize)};
        })())"""))
        assert state["view"] == view, state
        assert state["controls"] and not state["overflow"], state
        assert state["panel"]["bottom"] <= state["height"] and state["panel"]["top"] >= state["header"]["bottom"], state
        assert state["panel"]["height"] > 100, state
        if view == "map" and state["width"] <= 580:
            assert state["zoom"]["bottom"] <= state["panel"]["top"] and state["zoom"]["top"] >= state["header"]["bottom"], state
        if view == "list":
            assert state["list"]["height"] > 100, state
            if state["width"] <= 580:
                assert state["list"]["top"] >= state["panel"]["bottom"], state
        return state

    run("document.querySelector('.brand').click()")
    for size, factor in (("standard",1),("comfortable",1.15),("large",1.3),("extra-large",1.5)):
        choose(size)
        click("map-view")
        state = check_layout("map")
        assert abs(state["root"] - 16 * factor) < .02
        assert abs(state["card"] - 13 * factor) < .02
        click("list-view")
        check_layout("list")
    # A fresh page reads the saved preference even though the webview is private.
    run("window.__readabilityOldPage = true; location.reload()")
    wait(lambda state: state, "JSON.stringify(window.__readabilityOldPage !== true && document.getElementById('text-size') && !document.getElementById('text-size').disabled)", "fresh document")
    wait(lambda state: state == 24, "JSON.stringify(parseFloat(getComputedStyle(document.documentElement).fontSize))", "preference after reload")
    wait(lambda state: state == 3, "JSON.stringify(document.querySelectorAll('.university-card').length)", "reloaded workspace")
    click("map-view")
    check_layout("map")
    screenshot("readability-desktop")
    for width in (1000, 820, 580):
        window.resize(width, 700)
        wait(lambda state: abs(state - width) < 5, "JSON.stringify(innerWidth)", "intermediate viewport")
        check_layout("map")
        click("list-view")
        check_layout("list")
        click("map-view")
    window.resize(390, 640)
    wait(lambda state: state <= 580, "JSON.stringify(innerWidth)", "narrow viewport")
    check_layout("map")
    screenshot("readability-mobile-map")
    click("list-view")
    check_layout("list")
    screenshot("readability-mobile-list")
    run("document.querySelector('.university-card').click()")
    wait(lambda state: state, "JSON.stringify(!!document.querySelector('#inspector h2'))", "large university details")
    detail = json.loads(run("""JSON.stringify((() => {const el=document.getElementById('inspector'),r=el.getBoundingClientRect();return {left:r.left,right:r.right,bottom:r.bottom,height:r.height,viewport:innerWidth,windowHeight:innerHeight,font:getComputedStyle(document.querySelector('#inspector .detail-card p')).fontSize};})())"""))
    assert detail["left"] >= 0 and detail["right"] <= detail["viewport"] and detail["bottom"] <= detail["windowHeight"] and detail["height"] > 100, detail
    assert detail["font"] == "16.5px", detail
    screenshot("readability-details")
    run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
    click("open-settings")
    screenshot("readability-settings")
    click("close-settings")
    click("open-exchange")
    wait(lambda state: state, "JSON.stringify(document.getElementById('exchange-dialog').open)", "research dialog")
    assert run("getComputedStyle(document.querySelector('.exchange-hint')).fontSize") == "16.5px"
    screenshot("readability-research")
    click("close-exchange")
    # Every size also keeps narrow list controls and the list from overlapping.
    for size in ("standard", "comfortable", "large", "extra-large"):
        choose(size)
        check_layout("list")
    from exchange_checks import verify_exchange
    verify_exchange(window)
    print("Readability UI passed: four sizes, saved preference after reload, desktop and narrow layouts, settings and research text.", flush=True)
