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
    screenshot("countries-map")
    click("list-view")
    expect(mode="countries",view="list",country="FRA")
    assert run("!!document.querySelector('#university-table tr[data-country=\"FRA\"]')")
    screenshot("countries-list")
    click("universities-mode")
    expect(mode="universities",view="list",country="FRA",universities=0)
    click("nav-back")
    expect(mode="countries",view="list",country="FRA",selected="FRA")
    click("nav-forward")
    expect(mode="universities",view="list",country="FRA",universities=0)
    run("document.querySelector('.brand').click()")
    expect(mode="universities",view="map",country="",universities=3)
    print("Country modes passed: independent Map/List, country cards, empty-country selection and mode history.",flush=True)
