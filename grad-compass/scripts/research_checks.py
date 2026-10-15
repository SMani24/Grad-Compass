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
    run("document.getElementById('country-note-editor').open=true")
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
    identity=verify_requests(window,capture)
    verify_round_trip(window,identity,capture)
    verify_research_layouts(window,identity,capture)
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


def verify_round_trip(window,identity,capture=None):
    def run(source):return window.run_js(source)
    def wait(source,check,label):
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            raw=run(source);value=json.loads(raw) if isinstance(raw,str) else raw
            if value is not None and check(value):return value
            time.sleep(.05)
        raise AssertionError(f"Round-trip UI check failed ({label}): {value}")
    def click(name):run(f"document.getElementById({json.dumps(name)}).click()")
    def choose_request():
        click("open-research")
        wait("JSON.stringify(document.querySelectorAll('.request-row').length)",lambda count:count>=2,"request list")
        run(f"document.querySelector('.request-row[data-request=\"{identity}\"]').click()")
        wait("JSON.stringify(document.getElementById('research-request-detail').dataset.request)",lambda value:value==identity,"originating request")
        wait("JSON.stringify(!!document.getElementById('research-response-kind'))",bool,"response controls")
    def response(choice,revision=None):
        run("document.getElementById('research-response-review').open=true")
        run(f"document.getElementById('research-response-kind').value={json.dumps(choice)}")
        click("research-load-response")
        wait("JSON.stringify(document.getElementById('research-response-preview').textContent)",lambda text:text.startswith("Preview only"),"response preview")
        click("research-receive-response")
        if revision:
            wait("JSON.stringify(document.getElementById('research-result-revision')?.value)",lambda value:value==str(revision),"received result revision")
        else:
            wait("JSON.stringify(document.querySelector('.request-state')?.textContent)",lambda text:text.startswith("Acknowledged"),"explicit acknowledgement")
    def screenshot(name,selector=None):
        if capture:
            if selector:run(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'start'}})")
            time.sleep(.6);capture(name)
    choose_request()
    run("document.getElementById('research-response-kind').value='accepted'")
    click("research-load-response")
    wait("JSON.stringify(document.getElementById('research-response-preview').textContent)",lambda text:text.startswith("Preview only"),"acknowledgement preview")
    assert run("document.querySelector('.request-state').textContent").startswith("Prepared locally")
    click("research-receive-response")
    wait("JSON.stringify(document.querySelector('.request-state')?.textContent)",lambda text:text.startswith("Acknowledged"),"explicit accepted acknowledgement")
    assert "no execution progress reported" in run("document.querySelector('.request-state').textContent")
    response("result-1",1)
    wait("JSON.stringify(document.querySelectorAll('.finding-card').length)",lambda count:count==4,"country and university/program findings")
    screenshot("first-results","#research-findings-title")
    # Replay exact receipt through the interface; revision options remain unique.
    response("result-1",1)
    wait("JSON.stringify(document.getElementById('research-message').textContent)",lambda text:text.startswith("Already received"),"result receipt replay")
    assert run("document.getElementById('research-result-revision').options.length")==1
    run("document.querySelector('.finding-card[data-finding=\"country:CAN\"] .feedback-open').click()")
    comment="Please clarify the funding route. This is feedback, not a standing country restriction."
    run(f"document.querySelector('.finding-card[data-finding=\"country:CAN\"] .finding-comment').value={json.dumps(comment)};document.querySelector('.finding-card[data-finding=\"country:CAN\"] .save-finding-feedback').click()")
    wait("JSON.stringify(document.getElementById('research-handoff')?.value)",lambda text:"private feedback file" in text,"feedback handoff")
    assert comment not in run("document.getElementById('research-handoff').value")
    screenshot("feedback-handoff","#research-handoff-box")
    run("document.querySelector('.finding-card[data-finding=\"country:CAN\"] .follow-up-finding').click()")
    wait("JSON.stringify(document.getElementById('request-dialog').open)",bool,"finding follow-up form")
    assert run("document.getElementById('request-scope').value")=="refresh"
    assert run("document.getElementById('request-intake').value")=="Fall 2027"
    assert run("document.getElementById('request-country_restrictions').value")==""
    assert run("document.getElementById('request-context').value")==comment
    screenshot("follow-up-request")
    click("request-submit")
    wait("JSON.stringify(document.querySelectorAll('.request-row').length)",lambda count:count==3,"saved lineage-preserving follow-up")
    run(f"document.querySelector('.request-row[data-request=\"{identity}\"]').click()")
    wait("JSON.stringify(document.getElementById('research-result-revision')?.value)",lambda value:value=="1","original result remains")
    response("result-2",2)
    assert run("document.getElementById('research-result-revision').options.length")==2
    assert run("!!document.querySelector('.material-change[data-field=\"funding_routes\"]') && !!document.querySelector('.material-change[data-field=\"costs\"]')")
    screenshot("revised-changes","#research-material-changes")
    run("document.getElementById('research-result-revision').value='1';document.getElementById('research-result-revision').dispatchEvent(new Event('change'))")
    wait("JSON.stringify(document.querySelector('.finding-card[data-finding=\"country:CAN\"]')?.textContent)",lambda text:"Invented route A" in text and comment in text,"old revision and feedback preserved")
    screenshot("earlier-revision","#research-findings-title")
    click("close-research")
    # Use the unchanged public importer safeguards from the received result.
    run("document.querySelector('.brand').click()")
    choose_request()
    click("research-review-import")
    from exchange_checks import verify_exchange
    verify_exchange(window,capture)
    wait("JSON.stringify(document.querySelectorAll('#inspector .result-origin button').length)",lambda count:count>=2,"findings linked to promoted institution/program panels")
    run("document.querySelector('#inspector .program-card .result-origin button').click()")
    wait("JSON.stringify(document.querySelector('.finding-card.highlighted')?.dataset.finding)",lambda value:value=="program:33333333-3333-4333-8333-333333333333","program finding origin")
    click("close-research")
    click("countries-mode")
    run("document.querySelector('.country-card[data-country=\"FRA\"]').click()")
    wait("JSON.stringify(document.querySelector('.source-revision')?.textContent)",lambda text:"demo-FRA-r2" in text,"updated country evidence")
    assert run("document.getElementById('country-note').value")=="Synthetic private note; do not treat this as research evidence."
    assert run("document.getElementById('country-decision').value")=="Shortlisted"
    assert run("document.getElementById('watch-detail-FRA').getAttribute('aria-pressed')")=="true"
    assert run("document.querySelector('.research-state').textContent")=="Invented evidence · unreviewed demo"
    screenshot("country-result","#inspector .country-summary")
    run("window.__roundTripOld=true;location.reload()")
    wait("JSON.stringify(window.__roundTripOld!==true && !!document.getElementById('country-note'))",bool,"new page after saved round trip")
    wait("JSON.stringify(document.querySelector('.source-revision')?.textContent)",lambda text:"demo-FRA-r2" in text,"result history survives reload")
    assert run("document.getElementById('country-note').value")=="Synthetic private note; do not treat this as research evidence."
    assert run("document.getElementById('country-decision').value")=="Shortlisted"
    run("document.querySelector('#inspector .result-origin button').click()")
    wait("JSON.stringify(document.getElementById('research-result-revision')?.options.length)",lambda count:count==2,"both result revisions persisted")
    click("close-research")
    print("Research round trip passed: prepared → explicit acknowledgement → findings → feedback handoff → follow-up → revised result with material changes; imports, replay, personal state and revision history preserved.",flush=True)


def verify_research_layouts(window,identity,capture=None):
    def run(source):return window.run_js(source)
    def wait(source,check,label):
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            raw=run(source);value=json.loads(raw) if isinstance(raw,str) else raw
            if value is not None and check(value):return value
            time.sleep(.05)
        raise AssertionError(f"Research layout check failed ({label}): {value}")
    def click(name):run(f"document.getElementById({json.dumps(name)}).click()")
    def dialog_layout(name):
        time.sleep(.2)
        value=json.loads(run(f"""JSON.stringify((()=>{{const el=document.getElementById({json.dumps(name)}),r=el.getBoundingClientRect();return {{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:innerWidth,height:innerHeight,overflow:el.scrollWidth>el.clientWidth+1}};}})())"""))
        assert 0<=value["left"]<value["right"]<=value["width"] and 0<=value["top"]<value["bottom"]<=value["height"] and not value["overflow"],(name,value)
    for width in (1440,390):
        window.resize(width,640 if width==390 else 960)
        wait("JSON.stringify(innerWidth)",lambda actual:abs(actual-width)<5,"window resize")
        for size in ("standard","comfortable","large","extra-large"):
            click("open-settings")
            wait("JSON.stringify(!document.getElementById('text-size').disabled)",bool,"settings loaded")
            run(f"document.getElementById('text-size').value={json.dumps(size)};document.getElementById('text-size').dispatchEvent(new Event('change'))")
            wait("JSON.stringify(!document.getElementById('text-size').disabled && document.getElementById('settings-status').textContent.startsWith('Saved'))",bool,"text size saved")
            click("close-settings")
            click("countries-mode")
            click("map-view")
            run("document.getElementById('country-list-scope').value='watched';document.getElementById('country-list-scope').dispatchEvent(new Event('change'))")
            for code in ("FRA",):
                run(f"{{const selectedBox=document.querySelector('.country-watch-controls input[data-research-country=\"{code}\"]');if(!selectedBox.checked)selectedBox.click();}}")
            click("research-selected")
            wait("JSON.stringify(document.getElementById('request-dialog').open)",bool,"prefilled request")
            dialog_layout("request-dialog")
            assert run("document.getElementById('request-intake').value")=="Fall 2027"
            run("document.getElementById('request-preferences').open=true")
            dialog_layout("request-dialog")
            if capture and size=="extra-large" and width==390:
                run("document.getElementById('request-dialog').scrollTop=0");time.sleep(.5);capture("request-mobile-large")
            click("cancel-request")
            click("open-research")
            wait("JSON.stringify(document.querySelectorAll('.request-row').length)",lambda count:count==3,"persisted requests")
            run(f"document.querySelector('.request-row[data-request=\"{identity}\"]').click()")
            wait("JSON.stringify(document.getElementById('research-request-detail').dataset.request)",lambda selected:selected==identity,"request detail")
            dialog_layout("research-dialog")
            if capture and size=="extra-large" and width==390:
                run("document.getElementById('research-material-changes').scrollIntoView({block:'start'})");time.sleep(.5);capture("results-mobile-large")
            click("close-research")
            click("list-view")
            value=json.loads(run("""JSON.stringify((()=>{const p=document.querySelector('.results-panel').getBoundingClientRect(),list=document.querySelector('.list-container').getBoundingClientRect();return {panelBottom:p.bottom,listTop:list.top,listHeight:list.height,width:innerWidth,overflow:document.body.scrollWidth>innerWidth};})())"""))
            assert not value["overflow"],value
            if width==390:assert value["listTop"]>=value["panelBottom"] and value["listHeight"]>=100,value
            run("document.querySelector('.brand').click()")
    print("Research layout checks passed: four text sizes, desktop/minimum window, prefilled forms, result review and watchlist comparison.",flush=True)
