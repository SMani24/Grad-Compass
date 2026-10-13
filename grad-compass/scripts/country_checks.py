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
    print("Country modes passed: independent Map/List, country cards, empty-country selection and mode history.",flush=True)
