"""End-to-end UI demonstration; every mutation goes through a visible app control."""
import json
import time

BATCH_ID = "66666666-6666-4666-8666-666666666666"
INSTITUTION = "11111111-1111-4111-8111-111111111111"


def verify_exchange(window, capture=None):
    def run(source):
        return window.run_js(source)

    def snapshot():
        return json.loads(run("""JSON.stringify({
            options: document.getElementById('exchange-batch').options.length,
            stageDisabled: document.getElementById('exchange-stage').disabled,
            previewDisabled: document.getElementById('exchange-preview').disabled,
            promoteDisabled: document.getElementById('exchange-promote').disabled,
            approvalDisabled: document.getElementById('exchange-approve').disabled,
            replayDisabled: document.getElementById('exchange-replay').disabled,
            institutions: document.querySelectorAll('#exchange-institutions tbody tr').length,
            programs: document.querySelectorAll('#exchange-programs tbody tr').length,
            promoted: document.querySelectorAll('#exchange-content .exchange-badge.promoted').length,
            staged: document.querySelectorAll('#exchange-content .exchange-badge.staged').length,
            changes: document.querySelectorAll('.exchange-change').length,
            message: document.getElementById('exchange-message').textContent,
            outcomes: document.getElementById('exchange-outcomes').textContent,
            validation: document.getElementById('exchange-validation').textContent,
            open: document.getElementById('exchange-dialog').open
        })"""))

    def expect(check, label):
        stop_at = time.monotonic() + 10
        while time.monotonic() < stop_at:
            actual = snapshot()
            if check(actual):
                return actual
            time.sleep(0.05)
        raise AssertionError(f"Exchange UI check failed ({label}): {actual}")

    def click(button):
        run(f"document.getElementById({json.dumps(button)}).click()")

    def screenshot(name, selector):
        if capture:
            if selector == ".exchange-header":
                run("document.getElementById('exchange-dialog').scrollTop = 0")
            else:
                run(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'start'}})")
            time.sleep(0.15)
            capture(name)

    click("open-exchange")
    expect(lambda state: state["options"] == 2, "registered finalized fixture")
    run(f"document.getElementById('exchange-batch').value = {json.dumps(BATCH_ID)}; document.getElementById('exchange-batch').dispatchEvent(new Event('change'))")
    expect(lambda state: not state["stageDisabled"], "batch selected")
    click("exchange-stage")
    staged = expect(lambda state: state["institutions"] == 2 and state["programs"] == 3 and not state["previewDisabled"], "distinct staged record types")
    assert staged["promoted"] == 0 and staged["staged"] == 5 and staged["promoteDisabled"]
    assert "5 records validated" in staged["validation"]
    screenshot("staged", ".exchange-header")
    click("exchange-preview")
    expect(lambda state: "Dry run ready" in state["message"] and not state["previewDisabled"], "unmapped dry run")
    assert snapshot()["approvalDisabled"], "Missing explicit mapping must block approval"
    run(f"document.querySelector('.mapping-select[data-record=\"{INSTITUTION}\"]').value = 'create'; document.querySelector('tr[data-record=\"{INSTITUTION}\"] .mapping-save').click()")
    expect(lambda state: "Explicit mapping saved" in state["message"] and not state["previewDisabled"], "explicit create choice")
    click("exchange-preview")
    reviewed = expect(lambda state: state["changes"] == 2 and not state["approvalDisabled"], "exact projected changes")
    assert reviewed["promoteDisabled"], "Promotion must require a separate checked approval"
    assert "1 local institutions" in reviewed["outcomes"] and "0 programs" in reviewed["outcomes"]
    screenshot("dry-run", "#exchange-changes")
    click("exchange-approve")
    expect(lambda state: not state["promoteDisabled"], "explicit approval")
    click("exchange-promote")
    promoted = expect(lambda state: not state["replayDisabled"] and state["promoted"] == 2, "eligible committed promotion")
    assert promoted["staged"] == 3
    assert "2 local institutions" in promoted["outcomes"] and "1 programs" in promoted["outcomes"]
    click("exchange-replay")
    replay = expect(lambda state: "Replay verified: 0 new changes; no duplicates." in state["outcomes"], "idempotent replay")
    assert replay["promoted"] == 2 and replay["staged"] == 3
    screenshot("replay", "#exchange-outcomes")
    run("document.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true, cancelable:true}))")
    expect(lambda state: not state["open"], "Escape closes only the exchange dialog")
    print("Exchange UI passed: select → validate/stage → map → dry run → explicit approval → promotion → replay with zero new changes.", flush=True)
