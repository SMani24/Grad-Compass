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
    verify_requests(window,capture)
    print("Watchlist UI passed: empty-country watch, independent note/assessment, watchlist filtering and multi-selection.",flush=True)


def verify_requests(window,capture=None):
    def run(source):return window.run_js(source)
    def wait(source,check,label):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            raw=run(source);value=json.loads(raw) if isinstance(raw,str) else raw
            if value is not None and check(value):return value
            time.sleep(.05)
        raise AssertionError(f"Request UI check failed ({label}): {value}")
    def click(name):run(f"document.getElementById({json.dumps(name)}).click()")
    def open_form():
        click("research-selected")
        wait("JSON.stringify(document.getElementById('request-dialog').open)",bool,"request form opened")
    def fill(name,value):run(f"document.getElementById({json.dumps(name)}).value={json.dumps(value)}")
    def save(expected):
        click("request-submit")
        wait("JSON.stringify(document.getElementById('research-dialog').open && document.querySelectorAll('.request-row').length)",lambda count:count==expected,"request saved")
        wait("JSON.stringify(document.querySelector('.request-state')?.textContent)",lambda text:text.startswith("Prepared locally"),"local state without acknowledgement")
    open_form()
    assert run("document.getElementById('request-preferences').open")
    fill("request-intake","Cancelled intake")
    click("cancel-request")
    open_form()
    assert run("document.getElementById('request-intake').value")==""
    values={"request-intake":"Fall 2027","request-intake_alternatives":"Spring 2028","request-degree_routes":"Master or PhD",
            "request-instruction_language":"English","request-funding_priorities":"Need a funded route","request-research_limits":"Short evidence summaries",
            "request-limits":"Two examples per country","request-context":"Private synthetic context; not a permanent country restriction"}
    for name,value in values.items():fill(name,value)
    fill("request-scope","universities_programs")
    if capture:time.sleep(.5);capture("first-request")
    save(1)
    identity=run("document.querySelector('.request-row').dataset.request")
    click("prepare-research-handoff")
    wait("JSON.stringify(!!document.getElementById('research-handoff'))",bool,"private handoff")
    prompt=run("document.getElementById('research-handoff').value")
    assert "Fall 2027" not in prompt and "Need a funded route" not in prompt and "Private synthetic context" not in prompt
    assert identity in prompt and "digest" in prompt
    if capture:time.sleep(.5);capture("request-handoff")
    click("close-research")
    open_form()
    assert run("document.getElementById('request-intake').value")=="Fall 2027"
    assert run("document.getElementById('request-intake_alternatives').value")=="Spring 2028"
    assert run("document.getElementById('request-country_restrictions').value")==""
    assert not run("document.getElementById('request-preferences').open")
    assert run("document.getElementById('request-context').value")==""
    if capture:time.sleep(.5);capture("prefilled-request")
    fill("request-intake","Cancelled later change")
    click("cancel-request")
    open_form()
    assert run("document.getElementById('request-intake').value")=="Fall 2027"
    fill("request-intake","Spring 2030")
    run("document.getElementById('request-only').checked=true")
    save(2)
    click("close-research")
    open_form()
    assert run("document.getElementById('request-intake').value")=="Fall 2027","A request-only exception must not change autofill"
    click("cancel-request")
    print("Request UI passed: cancel safety, first submission, private reference-only handoff, autofill and request-only exception.",flush=True)
    return identity
