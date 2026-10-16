"""Exercise map saving independently of location, personal notes and research."""
import json
import time


def verify_country_selection(window, capture=None):
    def run(source):
        return window.run_js(source)

    def wait(source, check=bool, label="selection state"):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            raw = run(source)
            value = json.loads(raw) if isinstance(raw, str) and source.startswith("JSON.stringify(") else raw
            if value is not None and check(value):
                return value
            time.sleep(.05)
        raise AssertionError(f"Country selection failed ({label}): {value}")

    def click(name):
        run(f"document.getElementById({json.dumps(name)}).click()")

    def polygon(code, key=None):
        event = "new MouseEvent('click',{bubbles:true})" if not key else f"new KeyboardEvent('keydown',{{key:{json.dumps(key)},bubbles:true,cancelable:true}})"
        run(f"document.querySelector('.country-outline[data-country=\"{code}\"]').dispatchEvent({event})")

    def count(number):
        wait("document.getElementById('country-selection-count').textContent", lambda text: text == f"{number} selected", "selection count")

    def context():
        return json.loads(run("""JSON.stringify({url:location.href,country:document.getElementById('country').value,
          detail:document.querySelector('#inspector h2')?.textContent,history:history.state})"""))

    geometry = """JSON.stringify((()=>{const r=document.querySelector('.country-outline[data-country="FRA"]').getBoundingClientRect();return [r.x,r.y,r.width,r.height];})())"""

    def settled():
        previous = None
        stable = 0
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            value = json.loads(run(geometry))
            stable = stable + 1 if previous and all(abs(a-b)<.01 for a,b in zip(value,previous)) else 0
            if stable >= 3:
                return value
            previous = value
            time.sleep(.1)
        raise AssertionError("Map animation did not settle")

    def saved_state():
        run("window.__selectionSaved=null;fetch('/api/research').then(r=>r.json()).then(v=>window.__selectionSaved=v)")
        return wait("JSON.stringify(window.__selectionSaved)", label="saved state")

    window.resize(1440,960)
    wait("JSON.stringify(innerWidth)",lambda actual:actual==1440,"desktop resize")
    click("open-settings")
    wait("JSON.stringify(!document.getElementById('text-size').disabled)")
    run("document.getElementById('text-size').value='standard';document.getElementById('text-size').dispatchEvent(new Event('change'))")
    wait("JSON.stringify(!document.getElementById('text-size').disabled && document.getElementById('settings-status').textContent.startsWith('Saved'))")
    click("close-settings")
    run("document.querySelector('.brand').click()")
    click("countries-mode")
    run("document.querySelector('.country-card[data-country=\"FRA\"]').click()")
    wait("document.querySelector('#inspector h2')?.textContent", lambda text:text=="France")
    click("watch-detail-FRA")
    wait("window.GradCompassResearch.personal('FRA').watched")
    run("document.querySelector('#results [data-research-country=\"FRA\"]').click()")
    assert run("document.getElementById('research-selected').textContent") == "Research selected (1)"
    run("document.getElementById('country-note-editor').open=true;document.getElementById('country-note').value='Keep this synthetic note'")
    click("save-country-note")
    wait("document.querySelector('.private-note-status').textContent",lambda text:text.startswith("Note saved"))
    run("document.getElementById('country-decision').value='On hold';document.getElementById('country-decision').dispatchEvent(new Event('change'))")
    wait("document.querySelector('.decision-status').textContent",lambda text:text.startswith("Saved"))
    before = context()
    camera = settled()
    click("select-countries")
    polygon("CAN", "Enter")
    polygon("DEU", " ")
    count(2)
    polygon("DEU")
    polygon("FRA")
    count(2)
    assert context() == before, "Bulk selection changed navigation, filter or inspector"
    assert settled() == camera, "Bulk selection reframed the map"
    assert run("document.querySelector('.country-outline[data-country=\"FRA\"]').getAttribute('fill')") == "#decdf4"
    assert run("document.querySelector('.country-outline[data-country=\"FRA\"]').getAttribute('stroke-dasharray')") == "5 3"
    # Real Leaflet controls remain available, including keyboard panning.
    run("document.querySelector('.leaflet-control-zoom-in').click()")
    zoomed = settled()
    assert zoomed != camera, "Zoom was disabled during selection"
    run("document.getElementById('map').focus()")
    wait("document.activeElement.id",lambda identity:identity=='map','keyboard map focus')
    # Let the browser deliver focus to Leaflet before dispatching the key.
    time.sleep(.15)
    run("document.getElementById('map').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',keyCode:39,bubbles:true,cancelable:true}))")
    assert settled() != zoomed, "Keyboard map panning was disabled during selection"
    assert context() == before
    click("country-selection-list")
    run("document.getElementById('country-selection-search').value='Germany';document.getElementById('country-selection-search').dispatchEvent(new Event('input'));document.querySelector('#country-selection-options input[value=\"DEU\"]').click()")
    count(3)
    run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
    assert not run("document.getElementById('country-selection-dialog').open")
    assert run("document.getElementById('select-countries').getAttribute('aria-pressed')==='true'")
    assert context() == before
    click("list-view")
    count(3)
    click("country-selection-list")
    assert run("document.querySelector('#country-selection-options input[value=\"DEU\"]').checked")
    click("return-country-selection")
    click("map-view")
    assert context()["country"] == before["country"] and context()["detail"] == before["detail"]
    before = context()  # Presentation navigation is deliberate; selection creates no history.
    click("save-selected-countries")
    wait("document.getElementById('country-selection-status').textContent",lambda text:text.startswith("3 countries are"))
    first = saved_state()
    assert first["countries"]["FRA"] == {"watched":True,"note":"Keep this synthetic note"}
    assert all(first["countries"][code]["watched"] for code in ("CAN","DEU"))
    assert first["requests"] == [] and not first["has_preferences"]
    assert run("document.getElementById('research-selected').textContent") == "Research selected (1)"
    assert not run("document.querySelector('#results [data-research-country=\"CAN\"]').checked")
    assert run("document.getElementById('country-decision').value") == "On hold"
    assert run("document.getElementById('watch-detail-FRA').textContent") == "Remove from saved"
    click("save-selected-countries")
    wait("document.getElementById('country-selection-status').textContent",lambda text:text.startswith("3 countries are"))
    assert saved_state() == first, "Saving again changed existing state"
    if capture:
        capture("map-saved-countries")
    click("clear-selected-countries")
    count(0)
    assert run("document.getElementById('research-selected').textContent") == "Research selected (1)"
    assert run("document.getElementById('save-selected-countries').disabled")
    click("done-selecting-countries")
    assert context() == before
    assert run("document.querySelector('.country-outline[data-country=\"FRA\"]').getAttribute('fill')") == "#85c2d4"
    polygon("CAN")
    wait("document.querySelector('#inspector h2')?.textContent", lambda text:text=="Canada")
    assert run("document.getElementById('country').value") == "CAN", "Ordinary country behavior changed"
    click("nav-back")
    wait("document.getElementById('country').value", lambda text:text=="FRA")
    click("nav-forward")
    wait("document.getElementById('country').value", lambda text:text=="CAN")
    run("document.querySelector('.brand').click()")
    click("select-countries")
    click("list-view")
    click("done-selecting-countries")
    assert run("document.activeElement.id") == "list-view"
    click("map-view")
    verify_selection_layouts(window, run, wait, click, capture)
    assert saved_state()["requests"] == [], "Selection or saving initiated research"
    print("Country multi-selection passed: camera/context preserved, keyboard polygons, pan/zoom, atomic save/replay, notes/decisions kept, list alternative, history and 12 size layouts.", flush=True)


def verify_selection_layouts(window, run, wait, click, capture=None):
    for width in (1440,820,390):
        window.resize(width,640 if width==390 else 960)
        wait("JSON.stringify(innerWidth)",lambda actual:abs(actual-width)<5,"resize")
        for size in ("standard","comfortable","large","extra-large"):
            click("open-settings")
            wait("JSON.stringify(!document.getElementById('text-size').disabled)")
            run(f"document.getElementById('text-size').value={json.dumps(size)};document.getElementById('text-size').dispatchEvent(new Event('change'))")
            wait("JSON.stringify(!document.getElementById('text-size').disabled && document.getElementById('settings-status').textContent.startsWith('Saved'))")
            click("close-settings")
            click("select-countries")
            time.sleep(.25)
            layout = json.loads(run("""JSON.stringify((()=>{
              const rect=e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};};
              const buttons=[...document.querySelectorAll('.map-selection-controls button')].filter(e=>e.getClientRects().length).map(e=>({...rect(e),hit:e.contains(document.elementFromPoint(e.getBoundingClientRect().x+5,e.getBoundingClientRect().y+5))}));
              return {width:innerWidth,height:innerHeight,overflow:document.body.scrollWidth>innerWidth,buttons,tools:rect(document.getElementById('map-selection-controls')),panel:rect(document.querySelector('.results-panel'))};
            })())"""))
            assert not layout["overflow"], (width,size,layout)
            assert layout["tools"]["bottom"] <= layout["panel"]["top"], (width,size,layout)
            for button in layout["buttons"]:
                assert 0 <= button["left"] < button["right"] <= width and 0 <= button["top"] < button["bottom"] <= layout["height"] and button["hit"], (width,size,layout)
            if capture and width==390 and size=="extra-large":
                capture("narrow-large-map")
            click("country-selection-list")
            run("document.getElementById('country-selection-search').value='Canada';document.getElementById('country-selection-search').dispatchEvent(new Event('input'))")
            assert run("document.querySelectorAll('#country-selection-options input').length") == 1
            run("document.querySelector('#country-selection-options input').focus();document.querySelector('#country-selection-options input').click()")
            assert run("document.querySelector('#country-selection-options input').checked")
            assert run("document.getElementById('country-selection-dialog').scrollWidth<=document.getElementById('country-selection-dialog').clientWidth")
            if capture and width==390 and size=="extra-large":
                capture("narrow-large-country-list")
            click("return-country-selection")
            click("done-selecting-countries")
    window.resize(1440,960)
