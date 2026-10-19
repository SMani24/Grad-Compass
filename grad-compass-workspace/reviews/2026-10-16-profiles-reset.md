# University removal, local profiles and reset — 2026-10-16

The user requested a way to remove existing universities, reset application data through Settings and separate testing from personal use. Existing personal data was not removed or reset while developing this increment.

## Behavior

- University details provide **Remove university** with an explicit confirmation. It removes that stable institution and its programs from map/cards/List; original immutable evidence and request history remain in Requests. A backup is saved before removal. Repeating a batch/result does not restore it. **Settings → Removed universities → Restore** restores the same identity and nested programs.
- **Settings → Local profiles** creates empty named workspaces and explicitly switches between them. Existing data becomes **Personal** without copying in test universities. Saved countries, notes, decisions, preferences, requests/results/feedback, hidden institutions, locations and text settings are isolated. The exploration panel labels the active profile even at narrow widths. New profiles never inherit another profile's data or old preview samples.
- **Settings → Reset app data → Reset this profile…** presents a current-data summary and requires typing **RESET**. Cancellation changes no data. A fresh summary is required if app state or incoming producer files changed. A backup failure aborts reset. Other profiles remain intact.
- Reset switches the active profile to a new empty store atomically, with its name/identity retained. Previous files and a verified-in-tests recovery snapshot remain available; Settings lists reset recovery locations. This is a recoverable reset, not secure disk erasure. Old inbox packets cannot repopulate the empty store, and previous selections are not recopied on relaunch. The reset clears profile data and text settings; built-in map geography remains available.
- Profile switching/reset rotates the app mutation token, preventing a stale tab from writing into the newly selected workspace. Profile transitions serialize across app windows; a window with a stale registry asks to close/reopen rather than overwrite another window's state.
- Profiles are local workspace containers, not canonical Applicant Profile revisions. Shared contracts/importer, factual approval ownership, private applicant artifacts and legacy tracked DB/configuration are unchanged. Handoffs reference the exact active-profile request/inbox; there is no automatic invocation.

## Validation

- **83 application Python tests**, including eight focused groups for removal/replay/restoration, backup/registry failure, profile isolation/relaunch, reset/recovery, stale summary rejection, safe names/paths/windows and HTTP/session boundaries. Existing exact-byte/contract and original-data protection tests still pass.
- **22 unchanged exchange tests**, both JavaScript regression files, JavaScript syntax checks and three Qt shortcut/input checks.
- Native desktop check in invented temporary storage: remove/cancel/restore, map marker removal, replay without resurrection, profile creation/switching, preference and text-size isolation, request creation without execution, typed reset/cancel, empty reload, reset recovery and intact original Personal test data.
- Native settings, reset, map-selection toolbar and accessible country-list layouts checked at 1440/820/390 widths with Standard/Comfortable/Large/Extra-large text sizes. Reset uses one modal at a time; Escape/Cancel returns to Settings without clearing data. A bounded watchdog prevents a stalled Qt test from leaving its temporary workspace behind.
- All **146 protected tracked file contents** match the previous HEAD. Profile storage, sidecars, mailbox and review screenshots remain Git-excluded. Existing unrelated Paperclip README work is preserved outside this app commit.

The automated checks delete their temporary data afterward. Optional invented review captures remain local under `runtime/profile-ui-review/`. No personal profile was reset, no personal universities were removed, and no real request was submitted for testing.

## Try it

Close older Grad Compass windows and reopen **Grad Compass** through Pop!_OS. The existing data appears under **Personal**.

1. Open a university, choose **Remove university**, and inspect the confirmation. Cancel or remove intentionally. Settings → Removed universities offers Restore.
2. In Settings → Local profiles, create **Testing**, then choose **Switch profile**. It starts empty. Switch back to Personal to recover its unchanged workspace.
3. To start Personal empty instead, use Settings → Reset app data → Reset this profile…, review the counts and type **RESET** only when ready. Its recovery backup and other profiles remain available.

Reproduce the full disposable review from the repository root:

```bash
grad-compass/envGradCompass/bin/python -B grad-compass/scripts/check_profile_ui.py \
  --screenshots grad-compass-workspace/runtime/profile-ui-review
```

See the [application guide](../../grad-compass/README.md) for normal launch, storage and restore commands. The normal launcher remembers the active profile. An explicit `--local-dir` has a separate adjacent registry and does not copy the normal preview into isolated/recovered storage.

## Final verification — 2026-10-19

The continuation reran all 83 application tests, 22 unchanged exchange tests, both JavaScript regression files, JavaScript syntax checks and three Qt input checks successfully. The native invented-data demonstration passed removal/cancel/restoration/replay, explicit profile switching, typed reset/cancel/recovery, clean page reload and unchanged original Personal test data across all 12 layouts. Its reload probe now waits for a new document safely while the old one is being replaced. Captures were visually reviewed; the Create profile button uses the existing action styling. Temporary test data was cleaned up. Personal runtime data was not opened or changed for this verification.
