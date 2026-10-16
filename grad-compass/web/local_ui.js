"use strict";
/* Persistent local mode adapts existing panels; it never invokes a producer or agent. */
(() => {
  const get=id=>document.getElementById(id);
  const element=(tag,text)=>{const value=document.createElement(tag);if(text!==undefined)value.textContent=text;return value;};
  const readable=value=>value==null ? "Unknown" : typeof value==="object" ? JSON.stringify(value) : String(value);
  let messageTimer;
  function message(text,error=false){
    clearTimeout(messageTimer);get("local-message").textContent=text;get("local-message").hidden=false;
    if(!error)messageTimer=setTimeout(()=>{get("local-message").hidden=true;},10000);
  }
  function initialize(workspace){
    if(!workspace.operational)return;
    document.body.dataset.workspace="local";
    get("refresh-local").hidden=false;get("open-exchange").hidden=true;get("local-settings").hidden=false;
    document.querySelector(".preview-label").textContent="Private local workspace";
    document.querySelector("#request-title").parentElement.querySelector(".eyebrow").textContent="MANUAL RESEARCH HANDOFF";
    document.querySelector("#research-dialog .request-hint").textContent="Private, persistent research. Prepare a request, manually invoke Dave, then refresh to receive returned results. Receipt is separate from factual acceptance.";
    if(workspace.receipt?.errors)message(`${workspace.receipt.errors} incoming file(s) need attention. Use Refresh results to inspect the receipt outcome.`,true);
  }
  get("refresh-local").addEventListener("click",async()=>{
    const button=get("refresh-local");button.disabled=true;
    try{
      const receipt=await window.GradCompassResearch.post("/api/local/refresh",{});
      window.dispatchEvent(new Event("grad-compass:discovery-updated"));
      const errors=receipt.outcomes.filter(item=>item.error);
      message(errors.length ? errors.map(item=>item.file+": "+item.error).join(" · ") : `${receipt.received} new response(s) received. Saved data remains available; no agent was invoked.`,!!errors.length);
    }catch(error){message(error.message,true);}finally{button.disabled=false;}
  });
  get("backup-local").addEventListener("click",async()=>{
    const button=get("backup-local");button.disabled=true;
    try{const saved=await window.GradCompassResearch.post("/api/local/backup",{});get("backup-status").textContent=`Backup saved: ${saved.name}. Current data is unchanged.`;}
    catch(error){get("backup-status").textContent=error.message;}finally{button.disabled=false;}
  });
  get("sample-history").addEventListener("click",()=>{get("settings-dialog").close();window.GradCompassResearch.openArchive();});
  function evidence(container,record,title){
    if(!record)return;
    const details=element("details");details.className="source-details";details.append(element("summary",title));
    details.append(element("p",`Source agent review: ${readable(record.agent_factual_review)} · source human approval: ${readable(record.human_approval)}. These do not replace review of the transformed result.`));
    for(const [label,items] of [["Caveats",record.caveats],["Unknowns",record.unknowns]]){
      if(!items?.length)continue;details.append(element("h4",label));
      for(const item of items)details.append(element("p",typeof item==="string" ? item : `${item.field || "Evidence"}: ${item.detail || item.reason || readable(item)}`));
    }
    for(const claim of record.claims || []){
      const box=element("section");box.append(element("strong",claim.field),element("p",readable(claim.value)));
      const url=safeExternalUrl(claim.source_url);
      if(url){const link=element("a","Source: "+claim.source_id);link.href=url;link.target="_blank";link.rel="noopener noreferrer";box.append(link);}
      box.append(element("p",`${claim.locator || "Locator not supplied"} · observed ${claim.observed_at || "unknown"}`));details.append(box);
    }
    container.append(details);
  }
  function location(container,value){
    const details=element("details");details.className="source-details";details.append(element("summary",value?.status==="verified" ? "Verified campus location" : "Location unresolved · card remains available"));
    details.append(element("p",value?.campus || "No verified campus supplied"),element("p",value?.uncertainty || "No location evidence supplied."));
    if(value?.status==="verified")details.append(element("p",`${value.latitude}, ${value.longitude} · observed ${value.observed_at}`));
    const url=safeExternalUrl(value?.source_url);if(url){const link=element("a","Location source");link.href=url;link.target="_blank";link.rel="noopener noreferrer";details.append(link,element("p",value.locator));}
    container.append(details);
  }
  function countryFindings(container,findings){
    for(const finding of findings){
      const card=element("article");card.className="detail-card country-finding";card.dataset.finding=finding.finding_id;
      card.append(element("h3",(finding.field || "Research finding").replaceAll("_"," ")),element("p",finding.summary),
                  element("p",`Agent factual review: ${finding.review_status} · human approval: ${finding.human_approval.state}`));
      for(const caveat of finding.uncertainties || [])card.append(element("p","• "+readable(caveat)));
      card.append(window.GradCompassResearch.resultLink(finding.origin,"Review this finding"));container.append(card);
    }
  }
  window.GradCompassLocal=Object.freeze({initialize,evidence,location,countryFindings});
  window.addEventListener("grad-compass:workspace-loaded",event=>initialize(event.detail));
  if(window.GradCompassWorkspace)initialize(window.GradCompassWorkspace);
})();
