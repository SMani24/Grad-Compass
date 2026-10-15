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
    toolbar();
  }
  async function post(path, payload) {
    const response = await fetch(path,{method:"POST",headers:{"Content-Type":"application/json","X-Grad-Compass-Session":session},body:JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save. Please retry.");
    return result;
  }
  async function saveCountry(payload) {
    hydrate(await post("/api/research/country",payload));
    window.dispatchEvent(new Event("grad-compass:personal-updated"));
  }
  function watchButton(code, context) {
    const button = node("button",personal(code).watched ? "Unwatch" : "Watch country","watch-toggle");
    button.type = "button"; button.id = `watch-${context}-${code}`;
    button.setAttribute("aria-pressed",String(personal(code).watched));
    button.setAttribute("aria-label",`${personal(code).watched ? "Unwatch" : "Watch"} ${code}`);
    button.addEventListener("click",async () => {
      if (busy.has(code)) return;
      const restoreFocus = document.activeElement === button;
      busy.add(code); button.disabled = true;
      try {
        const watch = !personal(code).watched;
        await saveCountry({country_code:code,watched:watch});
        button.textContent = watch ? "Unwatch" : "Watch country";
        button.setAttribute("aria-pressed",String(watch));
        button.setAttribute("aria-label",`${watch ? "Unwatch" : "Watch"} ${code}`);
        status(watch ? "Added to your watchlist. Research and assessment are unchanged." : "Removed from watchlist. Your note and assessment are kept.");
        if (restoreFocus) get(button.id)?.focus({preventScroll:true});
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
    const label=node("label","Private note");label.htmlFor="country-note";
    const note=node("textarea");note.id="country-note";note.value=personal(code).note;note.maxLength=4000;note.rows=3;
    note.placeholder="Your context — kept separately from research evidence";
    const save=node("button","Save note","quiet-action");save.id="save-country-note";save.type="button";
    const message=node("p","Notes stay in this local synthetic workspace.","private-note-status");message.setAttribute("role","status");
    save.addEventListener("click",async()=>{
      save.disabled=true;note.disabled=true;
      try { await saveCountry({country_code:code,note:note.value});message.textContent="Note saved. Research and assessment are unchanged."; }
      catch(error){message.textContent=error.message;}
      finally{save.disabled=false;note.disabled=false;}
    });
    box.append(label,note,save,message);return box;
  }
  // Subsequent request UI uses the selection; changing a map filter never clears it.
  get("research-selected").addEventListener("click",()=>window.dispatchEvent(new CustomEvent("grad-compass:prepare-request",{detail:{countries:[...selected]}})));
  window.GradCompassResearch=Object.freeze({hydrate,personal,cardControls,detailControls,watchButton,selection,post});
})();
