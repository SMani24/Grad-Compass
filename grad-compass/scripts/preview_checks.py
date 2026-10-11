"""Browser navigation regressions run by the synthetic desktop smoke check."""
import json
import time


def verify_navigation(window):
    def run(source):
        return window.run_js(source)

    def snapshot():
        return json.loads(run("""JSON.stringify({
            country: document.getElementById('country').value,
            search: document.getElementById('search').value,
            view: document.getElementById('list-view').getAttribute('aria-pressed') === 'true' ? 'list' : 'map',
            title: document.querySelector('#inspector h2')?.textContent || '',
            inspector: !document.getElementById('inspector').hidden,
            count: document.querySelectorAll('.university-card').length,
            index: history.state.gradCompassIndex,
            forwardDisabled: document.getElementById('nav-forward').disabled
        })"""))

    def expect(**wanted):
        stop_at = time.monotonic() + 5
        while time.monotonic() < stop_at:
            actual = snapshot()
            if all(actual[key] == value for key, value in wanted.items()):
                return actual
            time.sleep(0.05)
        raise AssertionError(f"Navigation state mismatch: expected {wanted}, received {actual}")

    def country(code):
        run(f"document.getElementById('country').value = {json.dumps(code)}; document.getElementById('country').dispatchEvent(new Event('change'));")

    def click(button):
        run(f"document.getElementById({json.dumps(button)}).click()")

    def escape():
        run("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}))")

    # Cross-country back/forward must restore filters and university together.
    country("CAN")
    run("document.querySelector('.university-card').click()")
    expect(country="CAN", title="Northbridge Example University", count=2)
    country("DEU")
    run("document.querySelector('.university-card').click()")
    expect(country="DEU", title="Rivergate Example Institute", count=1)
    click("nav-back")
    expect(country="DEU", inspector=False)
    click("nav-back")
    expect(country="CAN", title="Northbridge Example University", count=2)
    click("nav-forward")
    expect(country="DEU", inspector=False)
    click("nav-forward")
    expect(country="DEU", title="Rivergate Example Institute", count=1)
    escape()
    expect(country="DEU", inspector=False, view="list")
    escape()
    expect(country="", count=3, view="list")
    escape()
    initial = expect(view="map")
    # A search edit is one history stop, not one stop per keystroke.
    for value in ("north", "northbridge"):
        run(f"document.getElementById('search').value = {json.dumps(value)}; document.getElementById('search').dispatchEvent(new Event('input'))")
    expect(search="northbridge", count=1, index=initial["index"] + 1)
    click("nav-back")
    expect(search="", count=3)
    click("nav-forward")
    expect(search="northbridge", count=1)
    click("nav-back")
    expect(search="", count=3)
    country("DEU")
    expect(country="DEU", forwardDisabled=True)
    escape()
    expect(country="", view="map", count=3)
    print("Navigation checks passed: cross-country history, Escape hierarchy, grouped search and forward-branch replacement.", flush=True)
