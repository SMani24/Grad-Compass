"use strict";
/* Persistent local mode adapts existing panels; it never invokes a producer or agent. */
(() => {
  const get=id=>document.getElementById(id);
  const element=(tag,text)=>{const value=document.createElement(tag);if(text!==undefined)value.textContent=text;return value;};
  const readable=value=>value==null ? "Unknown" : typeof value==="object" ? JSON.stringify(value) : String(value);
  let messageTimer,operational=false,profileState=null,pendingReset=null;
  let inboxVersion=null,inboxTimer=null,inboxBusy=false,inboxStatus=null;
  async function read(path){const response=await fetch(path,{cache:'no-store'});const data=await response.json();if(!response.ok)throw new Error(data.error || 'Could not load this profile');return data;}
  const post=(path,payload)=>window.GradCompassResearch.post(path,payload);
  async function updateInbox(value,notify=true){
    if(value.session && value.session!==window.GradCompassWorkspace?.session)throw new Error('This profile changed. Close this window and reopen Grad Compass.');
    const changed=inboxVersion===null || inboxVersion!==value.version;
    inboxVersion=value.version;inboxStatus=value;
    get('inbox-indicator').hidden=false;get('inbox-receipt').hidden=false;
    get('results-ready').hidden=!value.ready_count;
    get('results-ready').textContent=`Results ready (${value.ready_count})`;
    get('inbox-errors-action').hidden=!value.errors.length;
    const text=value.errors.length ? `${value.errors.length} incoming response(s) need attention. Open Requests for details.` : !get('show-received-results').hidden ? 'New responses received. Your draft is kept; show latest results when ready.' : value.pending ? 'Waiting for incoming files to finish…' : 'Responses arrive automatically. Dave is invoked manually.';
    for(const id of ['inbox-workspace-status','inbox-status']){
      if(get(id).textContent!==text)get(id).textContent=text;
      get(id).title=value.checked_at ? 'Last inbox check: '+new Date(value.checked_at).toLocaleString() : 'Checking inbox';
    }
    const errors=get('inbox-errors');errors.hidden=!value.errors.length;
    const list=get('inbox-error-list');const signature=JSON.stringify(value.errors);
    if(list.dataset.errors!==signature){list.replaceChildren(...value.errors.map(item=>element('p',item.file+': '+item.error)));list.dataset.errors=signature;}
    if(changed){
      window.dispatchEvent(new CustomEvent('grad-compass:discovery-updated',{detail:{automatic:true}}));
      if(notify)await window.GradCompassResearch.refreshReceived();
    }
    return value;
  }
  async function checkInbox(){return updateInbox(await post('/api/local/refresh',{}),false);}
  async function pollInbox(){
    if(!operational || inboxBusy)return;inboxBusy=true;
    try{await updateInbox(await read('/api/local/inbox'));}
    catch(error){get('inbox-workspace-status').textContent=error.message;get('inbox-status').textContent=error.message;}
    finally{inboxBusy=false;}
  }
  get('results-ready').addEventListener('click',()=>window.GradCompassResearch.openRequests(inboxStatus?.latest_request_id));
  get('inbox-errors-action').addEventListener('click',()=>{window.GradCompassResearch.openRequests();get('inbox-errors').open=true;});
  function renderProfiles(value){
    if(!value)return;profileState=value;
    get('local-profiles').hidden=false;get('local-reset-settings').hidden=false;
    const select=get('local-profile');select.replaceChildren();
    for(const profile of value.profiles){const option=element('option',profile.name);option.value=profile.id;select.append(option);}
    select.value=value.active_id;
    const active=value.profiles.find(profile=>profile.id===value.active_id);
    document.querySelector('.preview-label').textContent='Local profile · '+active.name;
    document.querySelector('.preview-label').title='Local profile: '+active.name;
    get('active-profile').hidden=false;get('active-profile').textContent='Profile: '+active.name;get('active-profile').title='Local profile: '+active.name;
    get('switch-profile').disabled=true;
    get('profile-backup-directory').textContent='Current profile backups: '+value.backup_directory;
    get('reset-recovery-list').replaceChildren(...value.recovery_backups.map(backup=>element('p',`${backup.name} · reset ${new Date(backup.reset_at).toLocaleString()} · recovery backup: ${backup.path}`)));
  }
  async function loadRemoved(){
    if(!operational)return;
    try{
      const data=await read('/api/local/removed');get('removed-count').textContent=`(${data.universities.length})`;
      get('removed-universities').replaceChildren();
      if(!data.universities.length)get('removed-universities').append(element('p','No removed universities.'));
      for(const university of data.universities){
        const row=element('div');row.className='removed-university';row.append(element('span',university.name));
        const restore=element('button','Restore');restore.type='button';restore.className='quiet-action';restore.dataset.restoreUniversity=university.id;
        restore.setAttribute('aria-label','Restore '+university.name);
        restore.addEventListener('click',async()=>{restore.disabled=true;try{await post('/api/local/restore-university',{id:university.id});await loadRemoved();window.dispatchEvent(new Event('grad-compass:discovery-updated'));get('removed-status').textContent=university.name+' restored.';}catch(error){get('removed-status').textContent=error.message;restore.disabled=false;}});
        row.append(restore);get('removed-universities').append(row);
      }
    }catch(error){get('removed-status').textContent=error.message;}
  }
  function confirmRemoval(university){
    const dialog=get('local-confirm');dialog.returnValue='cancel';
    get('local-confirm-title').textContent='Remove '+university.name+'?';
    get('local-confirm-description').textContent='Remove this university and its programs from your map and list. Original research stays in Requests. A backup is saved first; you can restore the university in Settings.';
    return new Promise(resolve=>{dialog.addEventListener('close',()=>resolve(dialog.returnValue==='confirm'),{once:true});dialog.showModal();});
  }
  function universityActions(container,university){
    const button=element('button','Remove university');button.type='button';button.className='danger-action';button.id='remove-university';
    button.addEventListener('click',async()=>{
      button.disabled=true;
      try{
        if(!await confirmRemoval(university))return;
        await post('/api/local/remove-university',{id:university.research.external_id});
        window.dispatchEvent(new CustomEvent('grad-compass:discovery-updated',{detail:{removedUniversity:university.id}}));
        message(university.name+' removed. Restore it in Settings → Removed universities.');
      }catch(error){message(error.message,true);}finally{button.disabled=false;}
    });container.append(button);
  }
  function message(text,error=false){
    clearTimeout(messageTimer);get("local-message").textContent=text;get("local-message").hidden=false;
    if(!error)messageTimer=setTimeout(()=>{get("local-message").hidden=true;},10000);
  }
  function initialize(workspace){
    if(!workspace.operational)return;
    operational=true;
    document.body.dataset.workspace="local";
    get("refresh-local").hidden=false;get("open-exchange").hidden=true;get("local-settings").hidden=false;
    document.querySelector(".preview-label").textContent="Private local workspace";
    renderProfiles(workspace.profiles);
    document.querySelector("#request-title").parentElement.querySelector(".eyebrow").textContent="MANUAL RESEARCH HANDOFF";
    document.querySelector("#research-dialog .request-hint").textContent="Saved requests and returned findings. Invoke Dave manually; responses arrive automatically with their actual review status.";
    pollInbox();if(!inboxTimer)inboxTimer=setInterval(pollInbox,3000);
  }
  get("refresh-local").addEventListener("click",async()=>{
    const button=get("refresh-local");button.disabled=true;
    try{
      const receipt=await updateInbox(await post("/api/local/refresh",{}));
      message(receipt.errors.length ? receipt.errors.map(item=>item.file+": "+item.error).join(" · ") : `${receipt.received} new response(s) received. Automatic receipt is also running.`,!!receipt.errors.length);
    }catch(error){message(error.message,true);}finally{button.disabled=false;}
  });
  get("backup-local").addEventListener("click",async()=>{
    const button=get("backup-local");button.disabled=true;
    try{const saved=await window.GradCompassResearch.post("/api/local/backup",{});get("backup-status").textContent=`Backup saved: ${saved.name}. Current data is unchanged.`;}
    catch(error){get("backup-status").textContent=error.message;}finally{button.disabled=false;}
  });
  get("sample-history").addEventListener("click",()=>{get("settings-dialog").close();window.GradCompassResearch.openArchive();});
  get('open-settings').addEventListener('click',loadRemoved);
  get('local-profile').addEventListener('change',()=>{get('switch-profile').disabled=get('local-profile').value===profileState?.active_id;});
  get('create-profile-form').addEventListener('submit',async event=>{
    event.preventDefault();const button=event.submitter || get('create-profile-form').querySelector('button');button.disabled=true;
    try{
      const result=await post('/api/local/profiles/create',{name:get('new-profile-name').value});renderProfiles(result);
      get('local-profile').value=result.profile.id;get('switch-profile').disabled=false;get('new-profile-name').value='';
      get('profile-status').textContent=`${result.profile.name} created empty. Choose Switch profile to open it. Your current profile is unchanged.`;
    }catch(error){get('profile-status').textContent=error.message;}finally{button.disabled=false;}
  });
  get('switch-profile').addEventListener('click',async()=>{
    const button=get('switch-profile');button.disabled=true;
    try{await post('/api/local/profiles/switch',{profile_id:get('local-profile').value});window.location.replace('/');}
    catch(error){get('profile-status').textContent=error.message;button.disabled=false;}
  });
  get('open-reset').addEventListener('click',async()=>{
    const button=get('open-reset');button.disabled=true;
    try{
      pendingReset=await read('/api/local/reset-preview');get('reset-title').textContent='Reset “'+pendingReset.name+'”?';
      const c=pendingReset.counts;
      get('reset-summary').textContent=`${c.saved_countries} saved countries, ${c.universities} universities, ${c.programs} programs, ${c.requests} requests, ${c.results} result revisions and ${c.feedback} feedback entries will leave this profile.`;
      get('reset-confirmation').value='';get('confirm-reset').disabled=true;get('reset-status').textContent='';
      get('settings-dialog').close();get('reset-dialog').showModal();get('reset-confirmation').focus();
    }catch(error){get('backup-status').textContent=error.message;}finally{button.disabled=false;}
  });
  get('reset-confirmation').addEventListener('input',()=>{get('confirm-reset').disabled=get('reset-confirmation').value!=='RESET';});
  get('cancel-reset').addEventListener('click',()=>{if(get('reset-dialog').dataset.busy!=='true')get('reset-dialog').close();});
  get('reset-dialog').addEventListener('close',()=>{
    if(get('reset-dialog').dataset.busy!=='true'){
      get('settings-dialog').showModal();get('open-reset').focus({preventScroll:true});
    }
  });
  get('reset-form').addEventListener('submit',async event=>{
    event.preventDefault();if(!pendingReset || get('reset-dialog').dataset.busy==='true')return;
    get('reset-dialog').dataset.busy='true';get('confirm-reset').disabled=true;get('cancel-reset').disabled=true;get('reset-confirmation').disabled=true;
    try{
      await post('/api/local/reset',{profile_id:pendingReset.profile_id,token:pendingReset.token,confirmation:get('reset-confirmation').value});
      window.location.replace('/');
    }catch(error){get('reset-status').textContent=error.message;get('reset-dialog').dataset.busy='false';get('confirm-reset').disabled=get('reset-confirmation').value!=='RESET';get('cancel-reset').disabled=false;get('reset-confirmation').disabled=false;}
  });
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
  window.GradCompassLocal=Object.freeze({initialize,evidence,location,countryFindings,universityActions,checkInbox});
  window.addEventListener('focus',pollInbox);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)pollInbox();});
  window.addEventListener('pagehide',()=>clearInterval(inboxTimer));
  window.addEventListener("grad-compass:workspace-loaded",event=>initialize(event.detail));
  if(window.GradCompassWorkspace)initialize(window.GradCompassWorkspace);
})();
