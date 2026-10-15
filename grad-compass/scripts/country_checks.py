"""Incremental Countries/Universities demonstration through the real map UI."""
import json
import time


def verify_countries(window, capture=None):
    def run(source):
        return window.run_js(source)

    def snapshot():
        return json.loads(run("""JSON.stringify({
          mode:document.getElementById('countries-mode').getAttribute('aria-pressed')==='true'?'countries':'universities',
          view:document.getElementById('map-view').getAttribute('aria-pressed')==='true'?'map':'list',
          country:document.getElementById('country').value,
          countries:document.querySelectorAll('.country-card').length,
          universities:document.querySelectorAll('.university-card').length,
          selected:document.querySelector('.country-card.selected')?.dataset.country,
          title:document.getElementById('exploration-title').textContent,
          detail:document.querySelector('#inspector h2')?.textContent,
          decision:document.getElementById('country-decision')?.value,
          saved:document.querySelector('.decision-status')?.textContent,
          sources:document.querySelectorAll('.country-source').length,
          review:document.querySelector('.research-state')?.textContent,
          fill:document.querySelector('.country-outline[data-country="FRA"]').getAttribute('fill')
        })"""))

    def expect(**wanted):
        stop = time.monotonic() + 10
        while time.monotonic() < stop:
            state = snapshot()
            if all(state.get(key) == value for key,value in wanted.items()):
                return state
            time.sleep(.05)
        raise AssertionError(f"Country exploration mismatch: {wanted}, actual {state}")

    def click(name):
        run(f"document.getElementById({json.dumps(name)}).click()")

    def screenshot(name):
        if capture:
            time.sleep(.6)
            capture(name)

    run("document.querySelector('.brand').click()")
    click("countries-mode")
    state = expect(mode="countries",view="map",title="Explore countries")
    assert state["countries"] > 100
    run("document.getElementById('search').value='France';document.getElementById('search').dispatchEvent(new Event('input'));document.querySelector('.country-card[data-country=\"FRA\"]').click()")
    expect(mode="countries",view="map",country="FRA",countries=1,selected="FRA",fill="#85c2d4")
    expect(detail="France",decision="",sources=1,review="Invented evidence · unreviewed demo")
    run("document.getElementById('country-decision').value='Shortlisted';document.getElementById('country-decision').dispatchEvent(new Event('change'))")
    expect(decision="Shortlisted",saved="Saved in this workspace. Research review is unchanged.")
    assert run("document.querySelector('.country-card.selected .decision-badge').textContent") == "Shortlisted"
    assert run("document.querySelector('.country-coverage').textContent.includes('not unsuitability')")
    # Polygon activation reopens details after an Escape close.
    run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));document.querySelector('.country-outline[data-country=\"FRA\"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))")
    expect(detail="France",decision="Shortlisted")
    screenshot("country-evidence")
    # The handoff changes exploration only; country geometry stays in the same place.
    bounds_probe = """JSON.stringify((() => {const r=document.querySelector('.country-outline[data-country="FRA"]').getBoundingClientRect();return [r.x,r.y,r.width,r.height];})())"""
    previous = None
    stable = 0
    stop = time.monotonic() + 5
    while time.monotonic() < stop:
        before = json.loads(run(bounds_probe))
        stable = stable + 1 if previous and all(abs(a-b)<.01 for a,b in zip(before,previous)) else 0
        if stable >= 3: break
        previous = before
        time.sleep(.1)
    else: raise AssertionError("Country framing animation did not settle")
    click("explore-country")
    expect(mode="universities",view="map",country="FRA",universities=0)
    after = json.loads(run("""JSON.stringify((() => {const r=document.querySelector('.country-outline[data-country="FRA"]').getBoundingClientRect();return [r.x,r.y,r.width,r.height];})())"""))
    assert before == after, (before,after)
    assert run("document.querySelector('#results .empty-state').textContent.includes('does not establish suitability')")
    screenshot("country-to-universities")
    click("nav-back")
    expect(mode="countries",view="map",country="FRA",detail="France",decision="Shortlisted")
    click("list-view")
    expect(mode="countries",view="list",country="FRA")
    assert run("!!document.querySelector('#university-table tr[data-country=\"FRA\"]')")
    screenshot("countries-list")
    click("universities-mode")
    expect(mode="universities",view="list",country="FRA",universities=0)
    click("nav-back")
    expect(mode="countries",view="list",country="FRA",selected="FRA",detail="France",decision="Shortlisted")
    click("nav-forward")
    expect(mode="universities",view="list",country="FRA",universities=0)
    # A genuinely new document reads the saved decision from runtime storage.
    run("window.__countryOldDocument=true;location.reload()")
    stop=time.monotonic()+10
    while time.monotonic()<stop:
        if run("window.__countryOldDocument!==true && !!document.getElementById('countries-mode') && !!document.querySelector('.country-outline[data-country=\"FRA\"]')"):
            break
        time.sleep(.05)
    else: raise AssertionError("Country check reload did not finish")
    click("countries-mode")
    run("document.querySelector('.country-card[data-country=\"FRA\"]').click()")
    expect(detail="France",decision="Shortlisted")
    run("document.getElementById('country-decision').value='Excluded';document.getElementById('country-decision').dispatchEvent(new Event('change'))")
    expect(decision="Excluded",saved="Saved in this workspace. Research review is unchanged.")
    assert run("!!document.querySelector('.country-card[data-country=\"FRA\"]')"), "Personal exclusion must not hide evidence or country access"
    run("document.querySelector('.brand').click()")
    expect(mode="universities",view="map",country="",universities=3)
    # Keyboard activation and two quick selections retain the latest country.
    click("countries-mode")
    run("document.querySelector('.country-card[data-country=\"CAN\"]').click();document.querySelector('.country-card[data-country=\"DEU\"]').click()")
    expect(detail="Germany",country="DEU")
    run("document.querySelector('.country-outline[data-country=\"FRA\"]').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}))")
    expect(detail="France",country="FRA")
    run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
    expect(country="FRA")
    assert run("document.getElementById('inspector').hidden")
    run("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
    expect(country="")
    run("document.querySelector('.brand').click()")
    verify_country_layouts(window, capture)
    print("Country modes passed: independent Map/List, country cards, empty-country selection and mode history.",flush=True)


def verify_country_layouts(window, capture=None):
    """Check country controls/details and handoff at every size and minimum width."""
    def run(source):
        return window.run_js(source)

    def wait(source, check, label):
        stop = time.monotonic() + 10
        while time.monotonic() < stop:
            raw = run(source)
            value = json.loads(raw) if isinstance(raw, str) else raw
            if value is not None and check(value): return value
            time.sleep(.05)
        raise AssertionError(f"Country layout check failed ({label}): {value}")

    def click(name):
        run(f"document.getElementById({json.dumps(name)}).click()")

    def layout(label):
        time.sleep(.25)
        value = json.loads(run("""JSON.stringify((() => {
          const rect=el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,height:r.height};};
          const buttons=[...document.querySelectorAll('.exploration-switch button')].map(rect);
          return {buttons,width:innerWidth,height:innerHeight,header:rect(document.querySelector('.topbar')),panel:rect(document.querySelector('.results-panel')),list:rect(document.querySelector('.list-container')),inspector:rect(document.getElementById('inspector')),root:parseFloat(getComputedStyle(document.documentElement).fontSize),bodyOverflow:document.body.scrollWidth>innerWidth};
        })())"""))
        assert not value["bodyOverflow"], (label,value)
        assert value["panel"]["top"] >= value["header"]["bottom"], (label,value)
        for button in value["buttons"]:
            assert 0 <= button["left"] < button["right"] <= value["width"], (label,value)
        assert value["buttons"][0]["right"] <= value["buttons"][1]["left"], (label,value)
        if run("document.getElementById('list-view').getAttribute('aria-pressed')==='true'"):
            assert value["list"]["height"] >= 100, (label,value)
            if value["width"] <= 580:
                assert value["list"]["top"] >= value["panel"]["bottom"], (label,value)
        return value

    for width in (1440,820,390):
        window.resize(width,640 if width==390 else 960)
        wait("JSON.stringify(innerWidth)",lambda actual:abs(actual-width)<5,"viewport resize")
        for size,factor in (("standard",1),("comfortable",1.15),("large",1.3),("extra-large",1.5)):
            click("open-settings")
            wait("JSON.stringify(!document.getElementById('text-size').disabled)",bool,"settings loaded")
            run(f"document.getElementById('text-size').value={json.dumps(size)};document.getElementById('text-size').dispatchEvent(new Event('change'))")
            wait("JSON.stringify(!document.getElementById('text-size').disabled && document.getElementById('settings-status').textContent.startsWith('Saved'))",bool,"text size saved")
            click("close-settings")
            click("countries-mode")
            click("map-view")
            value=layout("country map")
            assert abs(value["root"]-16*factor)<.02
            run("document.querySelector('.country-card[data-country=\"FRA\"]').click()")
            wait("JSON.stringify(document.querySelector('#inspector h2')?.textContent)",lambda title:title=="France","country details")
            assert abs(float(run("parseFloat(getComputedStyle(document.querySelector('.country-summary')).fontSize)"))-12*factor)<.02
            if capture and size=="extra-large" and width in (1440,390):
                time.sleep(.6);capture(f"country-details-{width}")
            click("explore-country")
            layout("country university map")
            assert run("document.getElementById('country').value") == "FRA"
            click("list-view")
            layout("country university list")
            if capture and size=="extra-large" and width==390:
                time.sleep(.6);capture("country-empty-mobile")
            click("countries-mode")
            layout("country list")
            # A known country with saved results must retain university selection styling.
            run("document.querySelector('.country-card[data-country=\"CAN\"]').click()")
            wait("JSON.stringify(document.querySelector('#inspector h2')?.textContent)",lambda title:title=="Canada","country with universities")
            click("explore-country")
            layout("populated university list")
            run("document.querySelector('.university-card').click()")
            wait("JSON.stringify(document.querySelector('#inspector h2')?.textContent)",lambda title:title=="Northbridge Example University","university details")
            assert run("!!document.querySelector('.university-card.selected') && !!document.querySelector('#university-table tr.selected')")
            run("document.querySelector('.brand').click()")
    print("Country layout checks passed: all four text sizes at desktop/intermediate/minimum widths, country details, empty/populated handoffs and university selection.",flush=True)
