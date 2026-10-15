"use strict";
/* Provisional synthetic response adapter. Real producer integration awaits compatibility review. */
(() => {
  const get=id=>document.getElementById(id);
  const countryName=code=>typeof BY_CODE!=="undefined" ? BY_CODE[code]?.name || code.replaceAll("_"," ") : code;
  const fieldNames={summary:"Summary",funding_routes:"Funding routes",costs:"Costs",work_rules:"Work rules",uncertainties:"Caveats and unknowns",sources:"Sources",observed_at:"Observed date",finding:"Finding"};
  const readable=value=>value==null ? "Unknown / not supplied" : Array.isArray(value) ? value.map(item=>typeof item==="object" ? `${item.source_url} · ${item.observed_at}` : item).join("; ") : String(value);
  function render(ctx) {
    const {section,current,openRequests,openRequest,handoff,post,action,node,technical,notify}=ctx;
    const request=current.request;
    const responseBox=node("details",undefined,"response-review");responseBox.id="research-response-review";responseBox.open=!current.results.length;
    responseBox.append(node("summary","Receive a manual response"),node("p","Synthetic adapter only. Load an app-generated response or select its saved JSON file, inspect it, then explicitly receive it. Loading a preview changes no request state."));
    const chooser=node("select");chooser.id="research-response-kind";chooser.setAttribute("aria-label","Synthetic response type");
    for(const [value,label] of [["accepted","Accepted acknowledgement (demo)"],["needs_clarification","Clarification requested (demo)"],["rejected","Rejected acknowledgement (demo)"],["result-1","First result (demo)"],["result-2","Revised result (demo)"]]){
      const option=node("option",label);option.value=value;chooser.append(option);
    }
    const preview=node("div");preview.id="research-response-preview";
    const responseStatus=node("p");responseStatus.id="research-response-status";responseStatus.setAttribute("role","status");
    let pending=null;
    const receive=action("Receive this response",async()=>{
      if(!pending)throw new Error("Load a synthetic response first.");
      const saved=await post("/api/research/receive",{envelope:pending});
      await openRequests(request.request_id,pending.envelope_kind==="result" ? pending.revision : null);
      get("research-message").textContent=saved.changed ? "Synthetic response received. Its exact request binding was checked." : "Already received — no duplicate changes.";
      notify();
    },"research-receive-response");receive.disabled=true;
    function showEnvelope(value) {
      if(!value || value.request_id!==request.request_id)throw new Error("This response belongs to a different request. Select that request first.");
      pending=value;receive.disabled=false;
      preview.replaceChildren(node("p",value.envelope_kind==="acknowledgement" ? `Preview only: ${value.state.replaceAll("_"," ")} acknowledgement.` : `Preview only: ${value.findings?.length || 0} findings, result revision ${value.revision}.`),
        technical("Response identity and exact request binding",{kind:value.envelope_kind,request:value.request_id,request_revision:value.request_revision,request_digest:value.request_digest,response_digest:value.digest}));
      responseStatus.textContent="Not received yet. No acknowledgement or progress has been assumed.";
    }
    const load=action("Load demo response",async()=>showEnvelope(await post("/api/research/demo-response",{request_id:request.request_id,choice:chooser.value})),"research-load-response");
    const fileLabel=node("label","Or choose a saved app-generated demo JSON file");fileLabel.htmlFor="research-response-file";
    const file=node("input");file.id="research-response-file";file.type="file";file.accept="application/json,.json";
    file.addEventListener("change",async()=>{
      try {
        const chosen=file.files?.[0];if(!chosen)return;
        if(chosen.size>180000)throw new Error("Choose a small app-generated demo response file.");
        showEnvelope(JSON.parse(await chosen.text()));
      }catch(error){pending=null;receive.disabled=true;preview.replaceChildren();responseStatus.textContent=error.message;}
    });
    const buttons=node("div",undefined,"result-actions");buttons.append(load,receive);
    const saveDemo=action("Save demo response JSON",async()=>{
      if(!pending)throw new Error("Load a demo response first.");
      const link=node("a");const url=URL.createObjectURL(new Blob([JSON.stringify(pending,null,2)],{type:"application/json"}));
      link.href=url;link.download="grad-compass-synthetic-response.json";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    },"research-save-response");
    responseBox.append(chooser,buttons,preview,responseStatus,fileLabel,file,saveDemo);section.append(responseBox);

    if(!current.results.length){section.append(node("p","No findings received yet. Request state changes only when an explicit response is recorded."));return;}
    const versions=node("select");versions.id="research-result-revision";versions.setAttribute("aria-label","Result revision to review");
    for(const item of current.results){const option=node("option",`Result revision ${item.envelope.revision} · ${item.envelope.completion}`);option.value=String(item.envelope.revision);versions.append(option);}
    let selected=current.results.find(item=>item.envelope.revision===ctx.revision) || current.results.at(-1);
    versions.value=String(selected.envelope.revision);
    versions.addEventListener("change",()=>openRequests(request.request_id,Number(versions.value)));
    const heading=node("h3","Review returned findings");heading.id="research-findings-title";
    section.append(heading,versions,node("p","Earlier result revisions remain available. Factual review, your assessment, and import approval are separate."));
    const result=selected.envelope;
    const changes=node("details",undefined,"result-changes");changes.id="research-material-changes";changes.open=result.revision>1 || request.prior_results.length>0;
    changes.append(node("summary",`${result.revision>1 || request.prior_results.length ? "Material changes since referenced research" : "New findings"} (${selected.changes.length})`));
    for(const change of selected.changes){
      const box=node("div",undefined,"material-change");box.dataset.field=change.field;
      const target=result.findings.find(item=>item.finding_id===change.finding_id);
      box.append(node("strong",`${target?.name || countryName(target?.country_code || "")} · ${fieldNames[change.field] || change.field}`),node("p","Before: "+readable(change.before)),node("p","After: "+readable(change.after)));changes.append(box);
    }
    if(!selected.changes.length)changes.append(node("p","No material finding changes."));section.append(changes);
    if(result.public_batch){
      const review=action("Review institution/program import",()=>{get("research-dialog").close();get("open-exchange").click();},"research-review-import");
      const box=node("div",undefined,"result-actions");box.append(review);section.append(box,node("p","Public institution/program facts use the existing v1 importer. They enter discovery only after its separate validation, mapping, dry run and operational approval."));
    }
    for(const finding of result.findings){
      const card=node("article",undefined,"finding-card"+(ctx.finding===finding.finding_id ? " highlighted" : ""));card.dataset.finding=finding.finding_id;
      card.append(node("h4",finding.name || countryName(finding.country_code)),node("p",finding.kind==="country" ? "Invented country evidence · unreviewed demo" : "Synthetic institution/program finding · separate import review required"),node("p",finding.summary));
      if(finding.kind==="country"){
        for(const key of ["funding_routes","costs","work_rules"]){card.append(node("strong",fieldNames[key]),node("p",readable(finding[key])));}
        card.append(node("p","Observed: "+finding.observed_at));
        for(const caveat of finding.uncertainties)card.append(node("p","• "+caveat));
        const sources=node("details");sources.append(node("summary","Sources and caveats"));
        for(const source of finding.sources)sources.append(node("p",`${source.source_url} · ${source.locator} · ${source.observed_at}`));card.append(sources);
      }
      const controls=node("div",undefined,"finding-actions");
      const feedbackForm=node("form",undefined,"feedback-form");feedbackForm.hidden=true;
      const label=node("label","Feedback on this specific finding");
      const comment=node("textarea");comment.className="finding-comment";comment.rows=3;comment.maxLength=4000;comment.required=true;
      const commentId="feedback-"+crypto.randomUUID();label.htmlFor=commentId;comment.id=commentId;
      const save=node("button","Save feedback & prepare handoff");save.type="submit";save.className="save-finding-feedback";
      const message=node("p");message.setAttribute("role","status");
      feedbackForm.append(label,comment,save,message);
      const submissionKey=crypto.randomUUID();
      feedbackForm.addEventListener("submit",async event=>{
        event.preventDefault();save.disabled=true;
        try {
          const feedback=await post("/api/research/feedback",{request_id:request.request_id,result_id:result.result_id,revision:result.revision,finding_id:finding.finding_id,comment:comment.value,submission_key:submissionKey});
          await openRequests(request.request_id,result.revision,finding.finding_id);
          await handoff(request.request_id,feedback.feedback_id);
          get("research-message").textContent="Feedback saved locally with its exact finding/revision. Copy its handoff to Dave; delivery is not assumed.";
        }catch(error){message.textContent=error.message;}finally{save.disabled=false;}
      });
      const feedbackButton=action("Give feedback",()=>{feedbackForm.hidden=!feedbackForm.hidden;if(!feedbackForm.hidden)comment.focus();});feedbackButton.className="feedback-open";
      const follow=action("Request an update",()=>{
        const last=[...current.feedback].reverse().find(item=>item.result_id===result.result_id && item.result_revision===result.revision && item.finding_id===finding.finding_id);
        return openRequest({countries:[finding.country_code],scope:"refresh",parent_request_id:request.request_id,
          prior_results:[{result_id:result.result_id,revision:result.revision,digest:result.digest,finding_id:finding.finding_id}],context:last?.comment || ""});
      });follow.className="follow-up-finding";controls.append(feedbackButton,follow);
      const discovery=action(finding.kind==="country" ? "View country on map" : "Open discovery record",async()=>{
        if(finding.kind==="country"){
          get("research-dialog").close();window.dispatchEvent(new CustomEvent("grad-compass:show-country",{detail:{code:finding.country_code}}));return;
        }
        const response=await fetch("/api/workspace");if(!response.ok)throw new Error("Could not load discovery.");
        const workspace=await response.json();const external=finding.kind==="institution" ? finding.external_id : finding.institution_id;
        const university=workspace.universities.find(item=>item.research?.external_id===external);
        if(!university)throw new Error("This record is not promoted yet. Use Review institution/program import first.");
        get("research-dialog").close();window.dispatchEvent(new CustomEvent("grad-compass:show-university",{detail:{id:university.id,program:finding.kind==="program" ? finding.external_id : null}}));
      });discovery.className="open-finding-discovery";controls.append(discovery);card.append(controls,feedbackForm);
      const feedback=current.feedback.filter(item=>item.result_id===result.result_id && item.result_revision===result.revision && item.finding_id===finding.finding_id);
      for(const item of feedback)card.append(node("p","Your saved feedback: "+item.comment,"saved-finding-feedback"));
      section.append(card);
    }
    section.append(technical("Result identity, source revision and delivery binding",{result:result.result_id,revision:result.revision,digest:result.digest,request_digest:result.request_digest,private_version:result.private_schema_version,country_version:"0.1.0",public_batch:result.public_batch?.batch_id || "None"}));
    if(ctx.finding)requestAnimationFrame(()=>[...section.querySelectorAll(".finding-card")].find(card=>card.dataset.finding===ctx.finding)?.scrollIntoView({block:"nearest"}));
  }
  window.GradCompassResearchReview=Object.freeze({render});
})();
