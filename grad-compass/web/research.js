"use strict";
/* App-owned personal state; producer requests and evidence remain separate. */
(() => {
  const get = id => document.getElementById(id);
  let data = {countries:{}};
  let session;
  const selected = new Set();
  const busy = new Set();
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const personal = code => data.countries[code] || {watched:false,note:""};
  const status = text => { get("research-toolbar-status").textContent = text; };
  function toolbar() {
    get("research-selected").disabled = selected.size === 0;
    get("research-selected").textContent = `Research selected (${selected.size})`;
  }
  function hydrate(next, token) {
    data = next || {countries:{}};
    if (token) session = token;
    for (const code of selected) if (!personal(code).watched) selected.delete(code);
    for (const button of document.querySelectorAll("[data-saved-country]")) {
      const code = button.dataset.savedCountry;
      button.textContent = personal(code).watched ? "Remove from saved" : "Save country";
      button.setAttribute("aria-pressed", String(personal(code).watched));
      button.setAttribute("aria-label", `${button.textContent}: ${code}`);
    }
    toolbar();
  }
  async function post(path, payload) {
    const response = await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","X-Grad-Compass-Session":session,"X-Grad-Compass-Workspace":window.GradCompassWorkspace?.session || session},body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save. Please retry.");
    return result;
  }
  async function saveCountry(payload) {
    hydrate(await post("/api/research/country",payload));
    window.dispatchEvent(new Event("grad-compass:personal-updated"));
  }
  function watchButton(code, context) {
    const button = node("button",personal(code).watched ? "Remove from saved" : "Save country","watch-toggle");
    button.type = "button"; button.id = `watch-${context}-${code}`;
    button.dataset.savedCountry = code;
    button.setAttribute("aria-pressed",String(personal(code).watched));
    button.setAttribute("aria-label",`${personal(code).watched ? "Remove from saved" : "Save country"}: ${code}`);
    button.addEventListener("click",async () => {
      if (busy.has(code)) return;
      const restoreFocus = document.activeElement === button;
      busy.add(code); button.disabled = true;
      try {
        const watch = !personal(code).watched;
        await saveCountry({country_code:code,watched:watch});
        button.textContent = watch ? "Remove from saved" : "Save country";
        button.setAttribute("aria-pressed",String(watch));
        button.setAttribute("aria-label",`${watch ? "Remove from saved" : "Save country"}: ${code}`);
        status(watch ? "Added to Saved countries. Research and assessment are unchanged." : "Removed from saved. Your note and assessment are kept.");
        if (restoreFocus && (document.activeElement===button || document.activeElement===document.body)) get(button.id)?.focus({preventScroll:true});
      } catch(error) { status(error.message); }
      finally { busy.delete(code); button.disabled = false; }
    });
    return button;
  }
  function selection(code) {
    const label = node("label",undefined,"research-selection");
    const input = node("input"); input.type="checkbox";input.dataset.researchCountry=code;
    input.checked=selected.has(code); input.disabled=!personal(code).watched;
    input.addEventListener("change",() => { if(input.checked) selected.add(code); else selected.delete(code);
      for (const other of document.querySelectorAll("[data-research-country]")) if(other.dataset.researchCountry===code) other.checked=input.checked;
      toolbar(); });
    label.append(input,node("span","Select for research")); return label;
  }
  function cardControls(code) {
    const box=node("div",undefined,"country-watch-controls");box.append(watchButton(code,"card"));
    if(personal(code).watched) box.append(selection(code));
    return box;
  }
  function detailControls(code) {
    const box=node("section",undefined,"country-watch-detail");box.append(watchButton(code,"detail"));
    const editor=node("details");editor.id="country-note-editor";editor.append(node("summary",personal(code).note ? "Private note · edit" : "Add a private note"));
    const label=node("label","Private note");label.htmlFor="country-note";
    const note=node("textarea");note.id="country-note";note.value=personal(code).note;note.maxLength=4000;note.rows=3;
    note.placeholder="Your context — kept separately from research evidence";
    const save=node("button","Save note","quiet-action");save.id="save-country-note";save.type="button";
    const message=node("p",data.synthetic===false ? "Notes stay in your private local workspace." : "Notes stay in this local synthetic workspace.","private-note-status");message.setAttribute("role","status");
    save.addEventListener("click",async()=>{
      save.disabled=true;note.disabled=true;
      try { await saveCountry({country_code:code,note:note.value});message.textContent="Note saved. Research and assessment are unchanged."; }
      catch(error){message.textContent=error.message;}
      finally{save.disabled=false;note.disabled=false;}
    });
    editor.append(label,note,save,message);box.append(editor);return box;
  }
  const preferenceFields = ["intake","intake_alternatives","degree_routes","instruction_language","country_restrictions","funding_priorities","research_limits"];
  const preferenceLabels = {intake:"Intake",intake_alternatives:"Alternatives",degree_routes:"Degree routes",instruction_language:"Language",country_restrictions:"Country restrictions",funding_priorities:"Funding",research_limits:"Shared limits"};
  const scopeLabels = {country_conditions:"Update country conditions",universities_programs:"Find universities and programs",refresh:"Refresh or follow up"};
  const countryLabel = code => typeof BY_CODE !== "undefined" ? BY_CODE[code]?.name || code.replaceAll("_"," ") : code;
  const dateLabel = value => new Date(value).toLocaleString();
  const requestDialog = get("request-dialog");
  const researchDialog = get("research-dialog");
  let draft;
  let current;
  let currentRevision;
  let currentFinding;
  let openSequence = 0;
  function summary(preferences) {
    const values = preferenceFields.filter(key=>preferences?.[key]).map(key=>`${preferenceLabels[key]}: ${preferences[key]}`);
    return values.length ? values.join(" · ") : "Shared preferences are unknown until you enter them. You may leave undecided values blank.";
  }
  async function reload() {
    const response=await fetch("/api/research",{cache:"no-store"});
    if(!response.ok) throw new Error("Could not load research requests. Please retry.");
    const value=await response.json();hydrate(value,value.session);return value;
  }
  async function openRequest(context={}) {
    try {
      await reload();
      draft={countries:context.countries || [...selected],parent_request_id:context.parent_request_id || null,parent_request_revision:context.parent_request_revision ?? null,parent_request_digest:context.parent_request_digest || null,prior_results:context.prior_results || [],submission_key:crypto.randomUUID()};
      if(!draft.countries.length) { status("Save countries and select them for research first.");return; }
      get("request-form").reset();get("request-bounds").hidden=data.synthetic!==false;
      get("request-max-institutions").value=context.bounds?.institutions ?? 5;get("request-max-programs").value=context.bounds?.programs ?? 5;get("request-form").dataset.submitting="false";
      get("request-countries").textContent=draft.countries.map(countryLabel).join(" · ");
      get("request-scope").value=context.scope || "country_conditions";
      get("request-scope").querySelector('option[value="refresh"]').disabled=!draft.parent_request_id;
      get("request-lineage").hidden=!draft.parent_request_id;
      get("request-lineage").textContent="Following up on a saved request/result. Earlier snapshots remain unchanged.";
      for(const key of preferenceFields) get("request-"+key).value=data.preferences?.[key] || "";
      get("request-preference-summary").textContent=summary(data.preferences);
      get("request-preferences").open=!data.has_preferences;
      get("request-context").value=context.context || "";
      get("request-form-status").textContent="This will be saved locally for manual handoff, not sent to an agent.";
      requestDialog.showModal();
    } catch(error) {status(error.message);}
  }
  function closeRequest() {
    if(get("request-form").dataset.submitting!=="true") requestDialog.close();
  }
  get("cancel-request").addEventListener("click",closeRequest);
  get("close-request").addEventListener("click",closeRequest);
  requestDialog.addEventListener("cancel",event=>{if(get("request-form").dataset.submitting==="true") event.preventDefault();});
  get("request-form").addEventListener("submit",async event=>{
    event.preventDefault();if(!draft || get("request-form").dataset.submitting==="true")return;
    const payload={...draft,scope:get("request-scope").value,preferences:Object.fromEntries(preferenceFields.map(key=>[key,get("request-"+key).value || null])),
      ...(data.synthetic===false ? {bounds:{institutions:Number(get("request-max-institutions").value),programs:Number(get("request-max-programs").value)}} : {}),remember_preferences:!get("request-only").checked,limits:get("request-limits").value || null,context:get("request-context").value || null};
    get("request-form").dataset.submitting="true";get("request-submit").disabled=true;get("cancel-request").disabled=true;get("close-request").disabled=true;
    try {
      const saved=await post("/api/research/submit",payload);
      await reload();
      requestDialog.close();
      await openRequests(saved.request.request_id);
    } catch(error) {get("request-form-status").textContent=error.message+" Retry confirms the same submission without duplicates.";}
    finally {get("request-form").dataset.submitting="false";get("request-submit").disabled=false;get("cancel-request").disabled=false;get("close-request").disabled=false;}
  });
  function action(text,handler,id) {
    const button=node("button",text);button.type="button";if(id)button.id=id;
    button.addEventListener("click",async()=>{
      button.disabled=true;
      try {await handler();}catch(error){get("research-message").textContent=error.message;get("research-message").className="research-error";}
      finally{button.disabled=false;}
    });return button;
  }
  function technical(title,values) {
    const details=node("details",undefined,"request-technical");details.append(node("summary",title));
    for(const [key,value] of Object.entries(values))details.append(node("p",`${key}: ${value ?? "Unknown"}`));return details;
  }
  async function handoff(requestId,feedbackId) {
    const exported=await post("/api/research/export",{request_id:requestId,...(feedbackId?{feedback_id:feedbackId}:{})});
    let box=get("research-handoff-box");
    if(!box){box=node("section");box.id="research-handoff-box";get("research-request-detail").prepend(box);}
    box.replaceChildren(node("h3",feedbackId?"Feedback handoff ready":"Request handoff ready"),node("p","Prepared locally. Copy this reference to Dave manually; copying it does not record acknowledgement."));
    const prompt=node("textarea",undefined,"handoff-text");prompt.id="research-handoff";prompt.readOnly=true;prompt.value=exported.prompt;prompt.rows=5;
    const copy=action("Copy handoff",async()=>{
      try {await navigator.clipboard.writeText(prompt.value);get("research-message").textContent="Copied. No delivery or acknowledgement has been assumed.";}
      catch {prompt.focus();prompt.select();get("research-message").textContent="Select and copy the handoff text manually.";}
    },"copy-research-handoff");
    box.append(prompt,copy);box.scrollIntoView({block:"nearest"});
  }
  function renderList(identity,items=data.requests,archive=false) {
    const list=get("research-request-list");list.replaceChildren();
    if(!items?.length){list.append(node("p","No requests saved yet."));return;}
    for(const item of items){
      const row=node("button",undefined,"request-row");row.type="button";row.dataset.request=item.request_id;row.setAttribute("aria-current",String(item.request_id===identity));
      row.append(node("strong",scopeLabels[item.scope]),node("span",item.countries.map(countryLabel).join(", ")),node("span",stateLabel(item.state)),node("span",dateLabel(item.created_at)));
      row.addEventListener("click",()=>openRequests(item.request_id,null,null,archive));list.append(row);
    }
  }
  function stateLabel(state) {
    return {prepared:"Prepared locally — not acknowledged",accepted:"Acknowledged — no execution progress reported",rejected:"Acknowledgement rejected",needs_clarification:"Clarification requested",results_received:"Results received — review findings"}[state] || state;
  }
  async function openRequests(identity=null,revision=null,finding=null,archive=false) {
    const sequence=++openSequence;
    if(!researchDialog.open)researchDialog.showModal();
    get("research-message").className="";get("research-message").textContent="Loading…";
    get("research-request-detail").dataset.request="";
    get("research-request-detail").replaceChildren(node("p","Loading the selected request…"));
    try {
      await reload();if(sequence!==openSequence)return;
      const archiveItems=archive ? (await (await fetch("/api/local/history")).json()).requests : null;
      const items=archive ? archiveItems : data.requests;
      identity=identity || items?.[0]?.request_id;
      renderList(identity,items,archive);
      if(!identity){get("research-request-detail").replaceChildren(node("p",archive ? "No sample requests were saved. The original sample workspace remains preserved." : "Save countries and select them for research in the map panel to prepare your first request."));get("research-message").textContent=archive ? "Sample history · read only." : "";return;}
      const response=await fetch((archive ? "/api/local/history/" : "/api/research/requests/")+encodeURIComponent(identity),{cache:"no-store"});
      if(!response.ok)throw new Error("Could not load this request.");
      const detail=await response.json();if(sequence!==openSequence)return;
      current=detail;currentRevision=revision;currentFinding=finding;
      renderDetail();get("research-message").textContent=archive ? "Sample history · read only. These are invented examples, separate from real research." : data.synthetic===false ? "Private local research. Dave runs only when you manually invoke him." : "Manual synthetic pilot. No real research or automatic agent execution.";
    }catch(error){get("research-message").textContent=error.message;get("research-message").className="research-error";}
  }
  function renderDetail() {
    const request=current.request;
    const section=get("research-request-detail");section.dataset.request=request.request_id;section.replaceChildren();
    const item=data.requests.find(item=>item.request_id===request.request_id);
    section.append(node("h3",scopeLabels[request.scope]),node("p",request.countries.map(countryLabel).join(" · ")),
      node("p",current.archive ? "Sample history · read only" : stateLabel(item?.state || "prepared"),"request-state"));
    const snapshot=node("details",undefined,"request-technical");snapshot.append(node("summary","Preference snapshot — fixed for this request"));
    for(const key of preferenceFields)snapshot.append(node("p",`${preferenceLabels[key]}: ${request.preferences[key] || "Unknown"}`));
    snapshot.append(node("p",`Request-specific limits: ${request.limits || "Unknown"}`),node("p",`Context: ${request.context || "None supplied"}`));section.append(snapshot);
    const actions=node("div",undefined,"result-actions");
    actions.append(action("Prepare private handoff",()=>handoff(request.request_id),"prepare-research-handoff"),
      action("Prepare follow-up",()=>openRequest({countries:request.countries,scope:"refresh",bounds:request.bounds,parent_request_id:request.request_id,parent_request_revision:request.revision,parent_request_digest:request.digest,prior_results:current.results.length ? [{result_id:current.results.at(-1).envelope.result_id,revision:current.results.at(-1).envelope.revision,digest:current.results.at(-1).envelope.digest,finding_id:null,finding_revision:null}]:[]}),"request-follow-up"));
    if(request.parent_request_id)actions.append(action("View parent request",()=>openRequests(request.parent_request_id,null,null,!!current.archive)));
    if(request.legacy) { for(const id of ["prepare-research-handoff","request-follow-up"]) actions.querySelector("#"+id).disabled=true; section.append(node("p","Legacy synthetic history — original digest semantics preserved. Prepare a new request to use the corrected handoff.")); }
    section.append(actions,technical("Identifiers & exact request binding",{request:request.request_id,revision:request.revision,digest:request.digest}));
    // Response and revision review shares this dialog through its synthetic adapter.
    if(window.GradCompassResearchReview)window.GradCompassResearchReview.render({section,current,revision:currentRevision,finding:currentFinding,openRequests:(id,rev,find)=>openRequests(id,rev,find,!!current.archive),openRequest,handoff,post,reload,action,node,technical,notify:()=>window.dispatchEvent(new Event("grad-compass:discovery-updated"))});
  }
  function resultLink(origin,label="Review source research") {
    const box=node("div",undefined,"result-origin");
    const button=node("button",`${label} · revision ${origin.revision}`);button.type="button";
    button.addEventListener("click",()=>openRequests(origin.request_id,origin.revision,origin.finding_id));box.append(button);return box;
  }
  get("open-research").addEventListener("click",()=>openRequests());
  get("close-research").addEventListener("click",()=>{++openSequence;researchDialog.close();});
  window.addEventListener("grad-compass:prepare-request",event=>openRequest(event.detail));
  window.addEventListener("grad-compass:open-result",event=>openRequests(event.detail.request_id,event.detail.revision,event.detail.finding_id));
  // Changing map filters never changes the pending multi-country selection.
  get("research-selected").addEventListener("click",()=>window.dispatchEvent(new CustomEvent("grad-compass:prepare-request",{detail:{countries:[...selected]}})));
  window.GradCompassResearch=Object.freeze({hydrate,personal,cardControls,detailControls,watchButton,selection,post,openRequest,openRequests,resultLink,openArchive:()=>openRequests(null,null,null,true)});
})();
