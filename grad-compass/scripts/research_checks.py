"""Manual-control demonstration of synthetic watchlist/research round trips."""
import json
import time


def verify_research(window,capture=None):
    def run(source):return window.run_js(source)
    def wait(source,check,label):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            raw=run(source)
            value=json.loads(raw) if isinstance(raw,str) else raw
            if value is not None and check(value):return value
            time.sleep(.05)
        raise AssertionError(f"Research UI check failed ({label}): {value}")
    def click(name):run(f"document.getElementById({json.dumps(name)}).click()")
    def screenshot(name):
        if capture:
            time.sleep(.5);capture(name)
    run("document.querySelector('.brand').click()")
    click("countries-mode")
    run("document.querySelector('.country-card[data-country=\"FRA\"]').click()")
    wait("JSON.stringify(document.getElementById('country-note')!==null)",bool,"country note")
    click("watch-detail-FRA")
    wait("JSON.stringify(document.getElementById('watch-detail-FRA').getAttribute('aria-pressed'))",lambda value:value=="true","watched empty country")
    run("document.getElementById('country-note').value='Synthetic private note; do not treat this as research evidence.'")
    click("save-country-note")
    wait("JSON.stringify(document.querySelector('.private-note-status').textContent)",lambda text:text.startswith("Note saved"),"private note saved")
    run("document.getElementById('country-decision').value='Shortlisted';document.getElementById('country-decision').dispatchEvent(new Event('change'))")
    wait("JSON.stringify(document.querySelector('.decision-status').textContent)",lambda text:text.startswith("Saved in this workspace. Research review"),"separate decision")
    run("document.querySelector('.country-card[data-country=\"CAN\"]').click()")
    wait("JSON.stringify(!!document.getElementById('watch-detail-CAN'))",bool,"second country")
    click("watch-detail-CAN")
    wait("JSON.stringify(document.getElementById('watch-detail-CAN').getAttribute('aria-pressed'))",lambda value:value=="true","second watched country")
    run("document.getElementById('country-list-scope').value='watched';document.getElementById('country-list-scope').dispatchEvent(new Event('change'))")
    wait("JSON.stringify(document.querySelectorAll('.country-card').length)",lambda count:count==2,"watchlist filter")
    for code in ("CAN","FRA"):
        run(f"document.querySelector('.country-watch-controls input[data-research-country=\"{code}\"]').click()")
    wait("JSON.stringify(document.getElementById('research-selected').textContent)",lambda text:text.endswith("(2)"),"multi-country selection")
    screenshot("watchlist")
    print("Watchlist UI passed: empty-country watch, independent note/assessment, watchlist filtering and multi-selection.",flush=True)
