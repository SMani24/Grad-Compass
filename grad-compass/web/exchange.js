"use strict";

(() => {
  const get = id => document.getElementById(id);
  const dialog = get("exchange-dialog");
  const select = get("exchange-batch");
  let session = null;
  let data = null;
  let busy = false;

  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function message(text, error = false) {
    const element = get("exchange-message");
    element.textContent = text;
    element.className = error ? "exchange-error" : "exchange-notice";
  }
  async function request(path, payload) {
    const response = await fetch(path, payload ? { method: "POST", headers: {
      "Content-Type": "application/json", "X-Grad-Compass-Session": session
    }, body: JSON.stringify(payload) } : { cache: "no-store" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The operation could not complete. Please retry.");
    return result;
  }
  function buttons() {
    const committed = data?.receipt?.promotion_committed;
    const preview = data?.preview;
    select.disabled = busy;
    get("exchange-stage").disabled = busy || !select.value;
    get("exchange-preview").disabled = busy || !data?.receipt || committed;
    get("exchange-approve").disabled = busy || !preview?.ready || committed;
    get("exchange-promote").disabled = busy || !preview?.ready || committed || !get("exchange-approve").checked;
    get("exchange-replay").disabled = busy || !committed;
    dialog.querySelectorAll(".mapping-select,.mapping-save").forEach(element => {
      element.disabled = busy || element.dataset.locked === "true" || committed;
    });
  }
  async function act(action, extras = {}) {
    if (busy) return;
    busy = true; buttons(); message("Working…");
    try {
      data = await request("/api/exchange/" + action, { batch_id: select.value, ...extras });
      get("exchange-approve").checked = false;
      render();
      message(action === "replay" ? (data.replay.no_changes ? "Replay verified: zero new changes." : "Replay changed the workspace; inspect the outcomes.")
        : action === "promote" ? "Eligible promotion committed. Other records remain in staging."
        : action === "map" ? "Explicit mapping saved. No institution was created yet."
        : action === "preview" ? "Dry run ready. Review the changes and held records before approval."
        : data.receipt.promotion_committed ? "Batch revalidated; its earlier promotion outcomes are retained."
        : "Batch validated and staged. No records have been promoted by this validation step.");
    } catch (error) { message(error.message, true); }
    finally { busy = false; buttons(); }
  }
  function table(headers) {
    const element = node("table");
    const head = node("thead"); const row = node("tr");
    for (const title of headers) { const cell = node("th", title); cell.scope = "col"; row.append(cell); }
    head.append(row); element.append(head);
    const body = node("tbody"); element.append(body);
    return { element, body };
  }
  function provenance(record) {
    const details = node("details"); details.append(node("summary", "Sources & revision"));
    details.append(node("p", "ID: " + record.id), node("p", "Revision: " + record.record_revision));
    for (const [field, fact] of Object.entries(record.facts)) {
      details.append(node("p", field + ": " + fact.source_url + " · " + fact.locator + " · " + fact.observed_at));
    }
    return details;
  }
  function storage(row) {
    const cell = node("td");
    cell.append(node("span", row.storage === "promoted" ? "Promoted" : "Staged", "exchange-badge " + row.storage));
    if (row.storage !== "promoted" && row.outcome !== "staged") {
      const reason = { skipped: row.record.review.state === "accepted" ? "Evidence not source checked" : "Awaiting producer acceptance",
        mapping_required: "Explicit mapping required", parent_mapping_required: "Parent institution not promoted", conflict: "Local field conflict" }[row.outcome] || row.outcome.replaceAll("_", " ");
      cell.append(node("p", reason, "exchange-hint"));
    }
    return cell;
  }
  function renderInstitutions() {
    const result = table(["Institution", "Producer review", "Storage", "Explicit mapping"]);
    for (const row of data.institutions) {
      const record = row.record;
      const tr = node("tr"); tr.dataset.record = record.id;
      const name = node("td"); name.append(node("strong", record.name), node("p", record.country_code + " · " + (record.city || "City unknown")), provenance(record));
      const review = node("td"); review.append(node("span", record.review.state, "exchange-badge"), node("p", record.verification.replaceAll("_", " "), "exchange-hint"));
      const mapping = node("td");
      if (row.mapping) {
        const target = data.saved_institutions.find(item => item.id === row.mapping.local_id);
        mapping.append(node("p", row.mapping.create ? "Create new on promotion" : "Linked: " + (target?.name || "Local institution")));
      } else {
        const chooser = node("select", undefined, "mapping-select");
        chooser.setAttribute("aria-label", "Mapping for " + record.name);
        chooser.dataset.record = record.id;
        const unset = node("option", "Choose a mapping…"); unset.value = ""; chooser.append(unset);
        if (record.review.state === "accepted" && record.verification === "source_checked") {
          const create = node("option", "Create a new institution"); create.value = "create"; chooser.append(create);
        }
        for (const local of data.saved_institutions) {
          const option = node("option", "Link: " + local.name); option.value = String(local.id); chooser.append(option);
        }
        const save = node("button", "Save mapping", "mapping-save"); save.type = "button";
        save.setAttribute("aria-label", "Save mapping for " + record.name);
        save.addEventListener("click", () => {
          if (!chooser.value) { message("Choose an explicit mapping first.", true); return; }
          act("map", { external_id: record.id, create: chooser.value === "create", local_id: chooser.value === "create" ? null : Number(chooser.value) });
        });
        mapping.append(chooser, save);
        if (record.review.state !== "accepted") mapping.append(node("p", "May stay unmapped; producer review is pending.", "exchange-hint"));
      }
      tr.append(name, review, storage(row), mapping); result.body.append(tr);
    }
    get("exchange-institutions").replaceChildren(result.element);
  }
  function renderPrograms() {
    const result = table(["Program", "Institution / degree", "Producer review", "Storage", "Intake claims"]);
    for (const row of data.programs) {
      const record = row.record;
      const tr = node("tr"); tr.dataset.record = record.id;
      const name = node("td"); name.append(node("strong", record.name), provenance(record));
      const parent = data.institutions.find(item => item.record.id === record.institution_id);
      const context = node("td"); context.append(node("p", parent?.record.name || record.institution_id), node("p", record.degree_level));
      const review = node("td"); review.append(node("span", record.review.state, "exchange-badge"));
      const claims = node("td");
      const projected = data.preview?.projected.programs.find(item => item.record.id === record.id);
      if (!record.requirements.length) claims.append(node("p", "No claims supplied", "exchange-hint"));
      for (const claim of record.requirements) {
        const key = claim.kind + ":" + claim.intake;
        const outcome = row.requirements[key] || projected?.requirements[key];
        const line = node("p", claim.kind.replaceAll("_", " ") + " · " + claim.intake + ": " + (claim.value ?? "Unknown"));
        if (outcome) line.append(node("span", " · " + (row.requirements[key] ? "Outcome: " : "Preview: ") + outcome));
        claims.append(line);
      }
      tr.append(name, context, review, storage(row), claims); result.body.append(tr);
    }
    get("exchange-programs").replaceChildren(result.element);
  }
  function renderChanges() {
    const container = get("exchange-changes"); container.replaceChildren();
    const preview = data.preview;
    if (!preview) { container.append(node("p", data.receipt.promotion_committed ? "This batch is committed. Replay verifies the same batch without changing it." : "No promotion is enabled until you review a dry run.", "exchange-hint")); return; }
    container.append(node("p", "Evidence freshness: " + preview.freshness_days + " days · Evaluated " + new Date(preview.evaluated_at).toISOString().slice(0, 16).replace("T", " ") + " UTC", "exchange-hint"));
    const held = [...preview.projected.institutions, ...preview.projected.programs].filter(row => row.storage === "staged").length;
    container.append(node("p", preview.changes.length + " proposed changes; " + held + " records will remain in staging."));
    if (!preview.ready) container.append(node("p", "Resolve missing accepted-institution mappings or conflicts, then review another dry run.", "exchange-error"));
    for (const change of preview.changes) {
      const card = node("div", undefined, "exchange-change");
      card.append(node("strong", change.action + " " + (change.kind === "institutions" ? "institution" : "program") + " — " + change.after.name));
      const fields = table(["Field", "Before", "After"]);
      for (const [key, label] of [["name", "Name"], ["country_code", "Country"], ["city", "City"], ["degree_level", "Degree"], ["portal_url", "Website"], ["official_url", "Program website"]]) {
        if (key in change.after) { const row = node("tr"); row.append(node("td", label), node("td", change.before?.[key] ?? "—"), node("td", change.after[key] ?? "Unknown")); fields.body.append(row); }
      }
      if (change.kind === "programs") {
        const target = preview.projected.saved_institutions.find(item => item.id === change.after.university_id);
        const previous = data.saved_institutions.find(item => item.id === change.before?.university_id);
        const row = node("tr"); row.append(node("td", "Institution"), node("td", previous?.name || "—"), node("td", target?.name || "Unmapped")); fields.body.append(row);
      }
      card.append(fields.element);
      if (change.kind === "programs") {
        card.append(node("p", "Eligible intake claims after promotion", "exchange-hint"));
        const claims = JSON.parse(change.after.requirements_json);
        if (!claims.length) card.append(node("p", "No eligible claims. Unknown, stale or expired claims remain in staging.", "exchange-hint"));
        for (const claim of claims) card.append(node("p", claim.kind.replaceAll("_", " ") + " · " + claim.intake + ": " + claim.value, "exchange-hint"));
      }
      container.append(card);
    }
  }
  function renderOutcomes() {
    const container = get("exchange-outcomes"); container.replaceChildren();
    if (!data.receipt) return;
    const committed = data.receipt.promotion_committed;
    const institutionCount = data.institutions.filter(row => row.storage === "promoted").length;
    const programCount = data.programs.filter(row => row.storage === "promoted").length;
    container.append(node("p", committed ? "Committed: " + institutionCount + " institution record(s) and " + programCount + " program record(s) promoted. " + (data.receipt.received - institutionCount - programCount) + " records remain in staging."
      : "Staged only. No batch promotion has been committed."));
    container.append(node("p", "Disposable workspace totals: " + data.saved_institutions.length + " local institutions · " + data.saved_programs.length + " programs."));
    if (data.replay) container.append(node("p", data.replay.no_changes ? "Replay verified: 0 new changes; no duplicates." : "Replay produced a change; review required.", data.replay.no_changes ? "exchange-notice" : "exchange-error"));
    const details = node("details"); details.append(node("summary", "Batch decision & manifest digest"), node("p", data.receipt.batch_id), node("p", data.receipt.manifest_digest), node("p", "Operational decision: " + (data.receipt.decision || "Not decided"))); container.append(details);
  }
  function render() {
    get("exchange-content").hidden = !data?.receipt;
    if (!data?.receipt) return;
    if (data.validation) get("exchange-validation").textContent = data.validation.received + " records validated. " + data.validation.accepted_candidates + " producer-accepted candidates; " + data.validation.pending_or_other + " pending/other records. Schema, provenance format, exact hashes and references passed.";
    renderInstitutions(); renderPrograms(); renderChanges(); renderOutcomes(); buttons();
  }
  get("open-exchange").addEventListener("click", async () => {
    dialog.showModal(); message("Loading the disposable exchange workspace…");
    try {
      const catalog = await request("/api/exchange"); session = catalog.session;
      if (!catalog.enabled) { message("Start the browser preview with an explicit --exchange-dir, or use the Grad Compass desktop launcher.", true); return; }
      if (select.options.length === 1) for (const batch of catalog.batches) { const option = node("option", batch.label + " · " + batch.directory); option.value = batch.id; select.append(option); }
      message("Select the finalized invented batch to begin.");
    } catch (error) { message(error.message, true); }
  });
  get("close-exchange").addEventListener("click", () => dialog.close());
  select.addEventListener("change", async () => {
    data = null; get("exchange-content").hidden = true; get("exchange-approve").checked = false;
    if (!select.value) { buttons(); return; }
    busy = true; buttons();
    try { data = await request("/api/exchange/state/" + select.value); render(); message(data.receipt ? "Existing batch state loaded from the disposable ledger." : "Finalized batch selected. Validate and stage it to inspect records."); }
    catch (error) { message(error.message, true); }
    finally { busy = false; buttons(); }
  });
  for (const action of ["stage", "preview", "replay"]) get("exchange-" + action).addEventListener("click", () => act(action));
  get("exchange-approve").addEventListener("change", buttons);
  get("exchange-promote").addEventListener("click", () => act("promote", { preview_id: data.preview.id, approved: get("exchange-approve").checked }));
})();
