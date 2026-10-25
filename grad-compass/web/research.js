"use strict";
/* App-owned personal state; producer requests and evidence remain separate. */
(() => {
  const get = id => document.getElementById(id);
  let data = {countries:{}};
  let session;
  const selected = new Set();
  const busy = new Set();
  let matching=[],selectionLoaded=false,selectionQueue=Promise.resolve(),selectionGeneration=0;
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const personal = code => data.countries[code] || {watched:false,note:""};
  function countryStatus(code,count=0){
    const requests=(data.requests || []).filter(item=>item.countries.includes(code));
    const country=requests.find(item=>item.country_reports?.[code]);
    const report=country?.country_reports[code],prepared=data.preferred_country_reports?.[code] || data.report_preparation?.[country?.request_id]?.[code];
    const discovery=requests.find(item=>item.scope==='universities_programs');
    return {report:prepared?.kind==='prepared_report' ? 'Country report available · '+prepared.version : report ? 'Country findings received · prepared report not yet published' : 'Country research not received',
      review:prepared?.kind==='prepared_report' ? 'Report factual review: '+prepared.review : report ? 'Finding factual review: '+report.review_status : 'Factual review: no report to review',
      prepared:prepared?.kind==='prepared_report'?prepared:null,
      discovery:count ? count+' saved universities · coverage is bounded' : discovery ? 'University discovery: '+stateLabel(discovery.state,discovery.completion) : 'University discovery not started'};
  }
  const status = text => { get("research-toolbar-status").textContent = text; };
  function toolbar() {
    get("research-selected").disabled = selected.size === 0;
    get("research-clear-selection").disabled = selected.size === 0;
    get("research-select-matching").textContent = `Select all matching (${matching.length})`;
    get("research-select-matching").disabled = matching.length === 0;
    const outside=[...selected].filter(code=>!matching.includes(code)).length;
    get("research-selection-summary").textContent = `${selected.size} selected${outside ? ` · ${outside} outside this filter` : ''}`;
    for(const input of document.querySelectorAll('[data-research-country]'))input.checked=selected.has(input.dataset.researchCountry);
    get("research-selected").textContent = `Research selected (${selected.size})`;
  }
  function hydrate(next, token) {
    data = next ? {...next,report_preparation:next.report_preparation || data.report_preparation,preferred_country_reports:next.preferred_country_reports || data.preferred_country_reports} : {countries:{}};
    if (token) session = token;
    if(!selectionLoaded){for(const code of data.draft_selection || [])selected.add(code);selectionLoaded=true;}
    for (const button of document.querySelectorAll("[data-saved-country]")) {
      const code = button.dataset.savedCountry;
      button.textContent = personal(code).watched ? "Remove from saved" : "Save country";
      button.setAttribute("aria-pressed", String(personal(code).watched));
      button.setAttribute("aria-label", `${button.textContent}: ${code}`);
    }
    toolbar();
  }
  async function post(path, payload) {
    const response = await fetch(path,{method:"POST",keepalive:["/api/reports/reading","/api/research/draft-selection"].includes(path),headers:{"Content-Type":"application/json","X-Grad-Compass-Session":session,"X-Grad-Compass-Workspace":window.GradCompassWorkspace?.session || session},body:JSON.stringify(payload)});
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
  function persistSelection(){
    toolbar();const countries=[...selected],generation=++selectionGeneration;
    status('Saving research selection…');
    selectionQueue=selectionQueue.catch(()=>{}).then(()=>post('/api/research/draft-selection',{countries}));
    selectionQueue.then(()=>{if(generation===selectionGeneration)status('Research selection saved. No research has started.');},error=>{if(generation===selectionGeneration)status('Selection not saved. '+error.message+' Change the selection to retry.');});
  }
  function selection(code) {
    const label = node("label",undefined,"research-selection");
    const input = node("input"); input.type="checkbox";input.dataset.researchCountry=code;
    input.checked=selected.has(code);input.setAttribute('aria-label','Select '+countryLabel(code)+' for research');
    input.addEventListener("change",() => { if(input.checked) selected.add(code); else selected.delete(code);persistSelection(); });
    label.append(input,node("span","Select for research")); return label;
  }
  // The complete filtered catalogue, independent of rendered cards/rows.
  function setMatching(countries){matching=countries.map(c=>c.code);toolbar();}
  get('research-select-matching').addEventListener('click',()=>{for(const code of matching)selected.add(code);persistSelection();});
  get('research-clear-selection').addEventListener('click',()=>{selected.clear();persistSelection();});
  function cardControls(code) {
    const box=node("div",undefined,"country-watch-controls");box.append(watchButton(code,"card"),selection(code));return box;
  }
  function detailControls(code) {
    const box=node("section",undefined,"country-watch-detail");
    if(personal(code).watched){
      const overflow=node('details',undefined,'country-overflow');overflow.append(node('summary','Country actions'),watchButton(code,'detail'));box.append(overflow);
    }else box.append(watchButton(code,'detail'));
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
  let reportCountry=null;
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
      draft={countries:context.countries || [...selected],parent_request_id:context.parent_request_id || null,parent_request_revision:context.parent_request_revision ?? null,parent_request_digest:context.parent_request_digest || null,prior_results:context.prior_results || [],submission_key:crypto.randomUUID(),...(context.edit_id?{edit_id:context.edit_id}:{})};
      if(!draft.countries.length) { status("Select countries or territories for the research draft first.");return; }
      get("request-form").reset();get("request-bounds").hidden=data.synthetic!==false;
      get("request-max-institutions").value=context.bounds?.institutions ?? 5;get("request-max-programs").value=context.bounds?.programs ?? 5;get("request-form").dataset.submitting="false";
      get('request-countries').dataset.countryCodes=JSON.stringify(draft.countries);
      get("request-countries").textContent=draft.countries.length+' selected — '+draft.countries.map(countryLabel).join(" · ");
      const unsupported=draft.countries.filter(code=>!(/^[A-Z]{3}$/.test(code)) || code==='XKX');
      const scopeBlocked=draft.countries.length>20 || unsupported.length>0;
      get('request-submit').disabled=scopeBlocked;
      get('request-form').dataset.scopeBlocked=String(scopeBlocked);
      const scopeNotice=scopeBlocked ? ' Full scope preserved. The current handoff supports up to 20 assigned country codes per request; '+(unsupported.length ? 'territory mappings need producer agreement ('+unsupported.map(countryLabel).join(', ')+'). ' : '')+'Narrow your draft selection before saving a bounded request. Nothing has been submitted.' : '';
      get('request-countries').dataset.scopeNotice=scopeNotice;
      get("request-scope").value=context.scope || "country_conditions";
      get("request-scope").querySelector('option[value="refresh"]').disabled=!draft.parent_request_id;
      get("request-lineage").hidden=!draft.parent_request_id;
      get("request-lineage").textContent="Following up on a saved request/result. Earlier snapshots remain unchanged.";
      for(const key of preferenceFields) get("request-"+key).value=context.preferences?.[key] ?? data.preferences?.[key] ?? "";
      get("request-preference-summary").textContent=summary(data.preferences);
      get("request-preferences").open=!data.has_preferences;
      get("request-context").value=context.context || "";get("request-limits").value=context.limits || "";
      get('request-only').checked=!!context.request_only;
      get("request-form-status").textContent=(data.synthetic===false?"Next: review the exact scope and approved profile reference before confirming dispatch. Offline requests stay pending.":"This synthetic request stays local; no real agent will be invoked.")+get("request-countries").dataset.scopeNotice;
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
    event.preventDefault();if(!draft || get("request-form").dataset.submitting==="true" || get("request-form").dataset.scopeBlocked==="true")return;
    const payload={...draft,scope:get("request-scope").value,preferences:Object.fromEntries(preferenceFields.map(key=>[key,get("request-"+key).value || null])),
      ...(data.synthetic===false ? {bounds:{institutions:Number(get("request-max-institutions").value),programs:Number(get("request-max-programs").value)}} : {}),remember_preferences:!get("request-only").checked,limits:get("request-limits").value || null,context:get("request-context").value || null};
    get("request-form").dataset.submitting="true";get("request-submit").disabled=true;get("cancel-request").disabled=true;get("close-request").disabled=true;
    try {
      if(data.synthetic===false && window.GradCompassDispatch){
        const {edit_id,...confirmedPayload}=payload;
        await window.GradCompassDispatch.prepare(confirmedPayload,edit_id);return;
      }
      const saved=await post("/api/research/submit",payload);
      await reload();
      requestDialog.close();
      await openRequests(saved.request.request_id);
    } catch(error) {get("request-form-status").textContent=error.message+" Retry confirms the same submission without duplicates.";}
    finally {get("request-form").dataset.submitting="false";get("request-submit").disabled=false;get("cancel-request").disabled=false;get("close-request").disabled=false;}
  });
  window.addEventListener("grad-compass:dispatch-cancelled",()=>{if(draft)draft.submission_key=crypto.randomUUID();});
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
    if(!box){box=node("section");box.id="research-handoff-box";const secondary=get('report-history');if(secondary){secondary.insertBefore(box,secondary.children[1] || null);secondary.open=true;}else get("research-request-detail").prepend(box);}
    box.replaceChildren(node("h3","Instructions for Dave"),node("p","Your request is already saved. Use these instructions to invoke Dave manually. Copying does not record acknowledgement. Responses will appear automatically."));
    const prompt=node("textarea",undefined,"handoff-text");prompt.id="research-handoff";prompt.readOnly=true;prompt.value=exported.prompt;prompt.rows=5;
    async function copyInstructions(){
      try {
        if(data.synthetic===false)await post('/api/local/copy-instructions',{request_id:requestId,...(feedbackId?{feedback_id:feedbackId}:{})});
        else {prompt.focus();prompt.select();if(!document.execCommand('copy'))throw new Error('Select and copy the displayed instructions');}
        get("research-message").textContent="Copied. Invoke Dave manually with these instructions. No acknowledgement has been assumed.";
      }
      catch {prompt.focus();prompt.select();get("research-message").textContent="Instructions ready. Select and copy the text, then manually invoke Dave.";}
    }
    const copy=action("Copy instructions for Dave",copyInstructions,"copy-research-handoff");
    box.append(prompt,copy);box.scrollIntoView({block:"nearest"});
    await copyInstructions();
  }
  function renderList(identity,items=data.requests,archive=false) {
    const countries=get('report-country-navigation'),chosen=countries.value;
    countries.replaceChildren(new Option('All countries',''),...[...new Set((items || []).flatMap(item=>item.countries))].map(code=>new Option(countryLabel(code),code)));
    countries.value=[...countries.options].some(v=>v.value===chosen)?chosen:'';
    const list=get("research-request-list");list.replaceChildren();
    if(!items?.length){list.append(node("p","No requests saved yet."));return;}
    for(const item of items){
      const row=node("button",undefined,"request-row");row.type="button";row.dataset.request=item.request_id;row.setAttribute("aria-current",String(item.request_id===identity));
      row.append(node("strong",scopeLabels[item.scope]),node("span",item.countries.map(countryLabel).join(", ")),node("span",item.state==='prepared' && item.dispatch_receipt ? dispatchLabel(item.dispatch_receipt) : stateLabel(item.state,item.completion)),node("span",dateLabel(item.created_at)));
      row.addEventListener("click",()=>openRequests(item.request_id,null,null,archive));list.append(row);
    }
  }
  function dispatchLabel(receipt) {
    return {accepted:'Paperclip task received — research acknowledgement is separate',pending:'Pending dispatch — explicit review/retry required',uncertain:'Delivery uncertain — reconcile before another action',dispatching:'Dispatch attempt recorded — awaiting receipt',cancelled:'Cancelled dispatch — history retained',superseded:'Replaced request — history retained',draft:'Draft — not dispatched'}[receipt.status] || receipt.status;
  }
  function stateLabel(state,completion) {
    return {prepared:"Saved — awaiting Dave’s acknowledgement",accepted:"Acknowledged — awaiting findings",rejected:"Acknowledgement rejected",needs_clarification:"Clarification requested",results_received:completion==='partial' ? "Partial results ready — research continues" : "Findings received — report preparation and delivery are separate"}[state] || state;
  }
  async function openRequests(identity=null,revision=null,finding=null,archive=false) {
    const sequence=++openSequence;
    if(!researchDialog.open)researchDialog.showModal();
    get("research-message").className="";get("research-message").textContent="Loading…";
    get("research-request-detail").dataset.request="";
    get("research-request-detail").replaceChildren(node("p","Loading the selected request…"));
    try {
      if(!archive && window.GradCompassWorkspace?.operational)await window.GradCompassLocal.checkInbox();
      await reload();if(sequence!==openSequence)return;
      const archiveItems=archive ? (await (await fetch("/api/local/history")).json()).requests : null;
      const items=archive ? archiveItems : data.requests;
      identity=identity || (!archive && data.preferred_country_reports?.[reportCountry]?.request_id) || items?.find(item=>item.result_count>0)?.request_id || items?.[0]?.request_id;
      if(!archive && !finding && revision==null && !reportCountry)reportCountry=Object.keys(data.preferred_country_reports || {}).find(code=>data.preferred_country_reports[code].request_id===identity) || null;
      renderList(identity,items,archive);
      if(!identity){get("research-request-detail").replaceChildren(node("p",archive ? "No sample requests were saved. The original sample workspace remains preserved." : "Save countries and select them for research in the map panel to prepare your first request."));get("research-message").textContent=archive ? "Sample history · read only." : "";return;}
      const response=await fetch((archive ? "/api/local/history/" : "/api/research/requests/")+encodeURIComponent(identity),{cache:"no-store"});
      if(!response.ok)throw new Error("Could not load this request.");
      const detail=await response.json();if(sequence!==openSequence)return;
      current=detail;currentRevision=revision;currentFinding=finding;
      renderDetail();get("research-message").textContent=archive ? "Sample history · read only. These are invented examples, separate from real research." : data.synthetic===false ? "" : "Manual synthetic pilot. No real research or automatic agent execution.";
    }catch(error){get("research-message").textContent=error.message;get("research-message").className="research-error";}
  }
  function renderDetail() {
    const request=current.request;
    const section=get("research-request-detail");section.dataset.request=request.request_id;section.replaceChildren();
    const item=data.requests.find(item=>item.request_id===request.request_id);
    section.append(node("h3",scopeLabels[request.scope]),node("p",request.countries.map(countryLabel).join(" · ")),
      node("p",current.archive ? "Sample history · read only" : stateLabel(item?.state || "prepared",item?.completion),"request-state"));
    const dispatchReceipt=data.requests?.find(item=>item.request_id===request.request_id)?.dispatch_receipt;
    if(!current.archive && request.synthetic===false)section.append(node('p',dispatchReceipt && !current.acknowledgement && !current.results.length ? ['cancelled','superseded'].includes(dispatchReceipt.status) ? dispatchLabel(dispatchReceipt)+'. This original request is retained for history; it will not be dispatched automatically.' : dispatchReceipt.status==='accepted' ? 'Paperclip task '+dispatchReceipt.task.identifier+' was received. Dave’s request-bound research acknowledgement has not arrived yet; responses will appear automatically. Task receipt is separate from factual acceptance.' : 'This request is saved in Pending requests. Review it there to edit, cancel or explicitly retry. Reconnecting does not start it automatically.' : current.results.length ? 'Returned findings are saved. Review their evidence and caveats, give feedback, or prepare a follow-up. Receipt is separate from factual acceptance.' : current.acknowledgement?.state==='accepted' ? 'Dave’s response is recorded. Further findings will appear here automatically when delivered.' : current.acknowledgement ? 'Dave’s acknowledgement needs attention. Review his reported status before preparing a follow-up.' : 'This request is saved. Copy the instructions below and invoke Dave manually. His acknowledgement and findings will appear here automatically.'));
    if(current.acknowledgement)section.append(node('p','Acknowledgement recorded: '+dateLabel(current.acknowledgement.acknowledged_at)));
    if(current.acknowledgement?.execution_progress)section.append(node('p','Dave reported: '+current.acknowledgement.execution_progress));
    const snapshot=node("details",undefined,"request-technical");snapshot.append(node("summary","Preference snapshot — fixed for this request"));
    for(const key of preferenceFields)snapshot.append(node("p",`${preferenceLabels[key]}: ${request.preferences[key] || "Unknown"}`));
    snapshot.append(node("p",`Request-specific limits: ${request.limits || "Unknown"}`),node("p",`Context: ${request.context || "None supplied"}`));section.append(snapshot);
    const actions=node("div",undefined,"result-actions");
    actions.append(action("Copy instructions for Dave",()=>handoff(request.request_id),"prepare-research-handoff"),
      action("Prepare follow-up",()=>openRequest({countries:request.countries,scope:"refresh",bounds:request.bounds,parent_request_id:request.request_id,parent_request_revision:request.revision,parent_request_digest:request.digest,prior_results:current.results.length ? [{result_id:current.results.at(-1).envelope.result_id,revision:current.results.at(-1).envelope.revision,digest:current.results.at(-1).envelope.digest,finding_id:null,finding_revision:null}]:[]}),"request-follow-up"));
    if(request.parent_request_id)actions.append(action("View parent request",()=>openRequests(request.parent_request_id,null,null,!!current.archive)));
    if(request.legacy) { for(const id of ["prepare-research-handoff","request-follow-up"]) actions.querySelector("#"+id).disabled=true; section.append(node("p","Legacy synthetic history — original digest semantics preserved. Prepare a new request to use the corrected handoff.")); }
    section.append(actions,technical("Identifiers & exact request binding",{request:request.request_id,revision:request.revision,digest:request.digest}));
    // Response and revision review shares this dialog through its synthetic adapter.
    if(window.GradCompassResearchReview)window.GradCompassResearchReview.render({section,current,revision:currentRevision,finding:currentFinding,country:reportCountry,openRequests:(id,rev,find)=>openRequests(id,rev,find,!!current.archive),openRequest,handoff,post,reload,action,node,technical,notify:()=>window.dispatchEvent(new Event("grad-compass:discovery-updated"))});
    const report=section.querySelector('#country-report');
    if(report){
      reportCountry=report.dataset.country;get('report-country-navigation').value=reportCountry;
      const secondary=node('details',undefined,'report-secondary');secondary.id='report-history';secondary.append(node('summary','Request progress, revision history, comparisons and recovery'));
      for(const child of [...section.children])if(child!==report)secondary.append(child);
      section.replaceChildren(report,secondary);
    }
  }
  function resultLink(origin,label="Review source research") {
    const box=node("div",undefined,"result-origin");
    const button=node("button",`${label} · revision ${origin.revision}`);button.type="button";
    button.addEventListener("click",()=>openRequests(origin.request_id,origin.revision,origin.finding_id));box.append(button);return box;
  }
  function openCountryReport(code,fallback=null){
    reportCountry=code;
    const preferred=data.preferred_country_reports?.[code];
    return openRequests(preferred?.request_id || fallback?.request_id,null,null);
  }
  async function refreshReceived(){
    await reload();
    if(!researchDialog.open || !current || current.archive)return;
    await window.GradCompassReportReader?.refresh();
    const identity=current.request.request_id,sequence=openSequence;
    renderList(identity);
    const response=await fetch('/api/research/requests/'+identity,{cache:'no-store'});
    if(!response.ok)throw new Error('Could not load received findings. Reopen Requests to retry.');
    const next=await response.json();
    if(sequence!==openSequence || !researchDialog.open)return;
    if(JSON.stringify([current.acknowledgement,current.results])===JSON.stringify([next.acknowledgement,next.results]))return;
    const section=get('research-request-detail');
    const editing=section.querySelector('.annotation-draft') || [...section.querySelectorAll('textarea:not([readonly])')].some(input=>((input.id==='report-personal-note' || input.closest('.canonical-report')) ? input.value!==input.defaultValue : input.value) || input===document.activeElement)
      || section.querySelector('#research-response-review[open]');
    if(editing){
      get('show-received-results').hidden=false;
      get('inbox-status').textContent='New responses received. Your draft is kept; show latest results when ready.';
      return;
    }
    const scroll=researchDialog.scrollTop;
    current=next;renderDetail();researchDialog.scrollTop=scroll;
    get('show-received-results').hidden=true;
  }
  get('show-received-results').addEventListener('click',()=>{get('show-received-results').hidden=true;openRequests(current?.request.request_id,currentRevision,currentFinding);});
  get("open-research").addEventListener("click",()=>openRequests());
  get('report-country-navigation').addEventListener('change',()=>{const code=get('report-country-navigation').value;reportCountry=code || null;const candidates=(data.requests || []).filter(v=>!code || v.countries.includes(code));const selected=candidates.find(v=>v.country_reports?.[code] || v.result_count>0) || candidates[0];if(selected)openCountryReport(code,selected);});
  researchDialog.addEventListener('close',()=>window.dispatchEvent(new Event('grad-compass:panels-resized')));
  get("close-research").addEventListener("click",()=>{++openSequence;researchDialog.close();});
  window.addEventListener("grad-compass:prepare-request",event=>openRequest(event.detail));
  window.addEventListener("grad-compass:open-result",event=>openRequests(event.detail.request_id,event.detail.revision,event.detail.finding_id));
  // Changing map filters never changes the pending multi-country selection.
  get("research-selected").addEventListener("click",()=>window.dispatchEvent(new CustomEvent("grad-compass:prepare-request",{detail:{countries:[...selected]}})));
  window.GradCompassResearch=Object.freeze({hydrate,personal,setMatching,countryStatus,cardControls,detailControls,watchButton,selection,post,openRequest,openRequests,openCountryReport,refreshReceived,resultLink,openArchive:()=>openRequests(null,null,null,true)});
})();
