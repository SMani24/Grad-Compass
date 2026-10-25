"use strict";
/* No reconnect/startup invocation: only explicit confirmed actions call dispatch. */
(() => {
  const get=id=>document.getElementById(id),node=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
  const post=(path,body)=>window.GradCompassResearch.post(path,body);
  let current=null,busy=false;
  const countryName=code=>typeof BY_CODE!=='undefined'?BY_CODE[code]?.name || code:code;
  function summary(entry,target){
    const p=entry.payload,profile=entry.profile_reference;
    target.replaceChildren(node('h3',p.countries.map(countryName).join(', ')),node('p','Research stage: '+({country_conditions:'Country conditions',universities_programs:'Universities and programs',refresh:'Follow-up / refresh'}[p.scope] || p.scope)),node('p','Intake: '+(p.preferences?.intake || 'Not specified')),node('p','Limits: up to '+p.bounds.institutions+' universities and '+p.bounds.programs+' programs; '+(p.limits || 'No additional request-only limits')+' · '+(p.preferences?.research_limits || 'No shared limits')),node('p',profile?'Approved Applicant Profile: '+profile.id+' · revision '+profile.revision+' · human approval '+profile.approval+' · approved '+profile.approved_at:'Approved Applicant Profile reference is unavailable. This request can be saved pending; it will not be dispatched until a verified reference is reviewed.'));
    const details=document.createElement('details');details.append(node('summary','Preferences and exact data for Dave'),node('p',Object.entries(p.preferences || {}).map(([k,v])=>k+': '+(v || 'Unknown')).join(' · ')),node('p','Request-only context: '+(p.context || 'None')),node('p','Profile reference and request digest only; no profile/CV contents or connection credentials are sent.'));
    if(entry.destination)details.append(node('p','Paperclip destination: company '+entry.destination.company_id+' · Dave '+entry.destination.dave_id));
    if(profile)details.append(node('p','Approved reference SHA-256: '+profile.sha256+' · receipt '+profile.receipt_id));
    target.append(details);
  }
  async function review(entry){current=entry;summary(entry,get('dispatch-confirm-summary'));get('dispatch-confirm-status').textContent=entry.error || '';get('dispatch-confirm').textContent=entry.profile_reference?'Confirm and dispatch':'Save pending request';get('dispatch-confirm-dialog').showModal();}
  async function prepare(payload,edit_id){return review(await post('/api/dispatch/prepare',{payload,...(edit_id?{edit_id}:{})}));}
  async function refresh(){
    if(!window.GradCompassWorkspace?.operational)return;
    const r=await fetch('/api/dispatch',{cache:'no-store'});if(!r.ok)throw Error('Could not load pending requests');const data=await r.json();
    const pending=data.entries.filter(e=>['draft','pending','uncertain','dispatching'].includes(e.status));get('open-pending-requests').hidden=false;get('open-pending-requests').textContent='Pending requests ('+pending.length+')';
    const list=get('pending-requests-list');list.replaceChildren();
    for(const entry of [...data.entries].reverse()){
      const section=node('section','');section.className='pending-request';section.append(node('h3',entry.payload.countries.map(countryName).join(', ')+' · draft revision '+entry.revision),node('p',entry.status==='accepted'?'Paperclip task received: '+entry.task.identifier+' · '+entry.task.status+' (task receipt; research acknowledgement is separate)':entry.status),node('p',entry.error || ''));
      const details=document.createElement('details');details.append(node('summary','Review saved scope'));const body=node('div','');summary(entry,body);details.append(body);section.append(details);
      const actions=node('div','');actions.className='request-actions';
      function action(label,fn){const b=node('button',label);b.type='button';b.addEventListener('click',async()=>{b.disabled=true;try{await fn();}catch(e){get('pending-requests-status').textContent=e.message;}finally{b.disabled=false;}});actions.append(b);}
      if(['draft','pending'].includes(entry.status) && !entry.attempts){
        action('Edit as new draft revision',()=>{get('pending-requests-dialog').close();window.GradCompassResearch.openRequest({...entry.payload,preferences:entry.payload.preferences,edit_id:entry.id,request_only:!entry.payload.remember_preferences});});
        action('Cancel request',async()=>{await post('/api/dispatch/cancel',{id:entry.id});await refresh();});
      }
      if(['draft','pending','uncertain','dispatching'].includes(entry.status))action(entry.status==='draft'?'Review and confirm':'Review and retry',()=>review(entry));
      if(entry.request)action('View saved request',()=>{get('pending-requests-dialog').close();window.GradCompassResearch.openRequests(entry.request.id);});
      section.append(actions);list.append(section);
    }
    if(!data.entries.length)list.append(node('p','No pending requests. Start with a map selection.'));
  }
  get('dispatch-confirm').addEventListener('click',async()=>{
    if(busy || !current)return;busy=true;get('dispatch-confirm').disabled=true;get('dispatch-confirm-cancel').disabled=true;
    try{const result=await post('/api/dispatch/confirm',{id:current.id,confirmation_digest:current.confirmation_digest});get('dispatch-confirm-dialog').close();get('request-dialog').close();get('pending-requests-dialog').close();await refresh();await window.GradCompassResearch.openRequests(result.request.id);document.getElementById('research-message').textContent=result.status==='accepted'?'Dave task '+result.task.identifier+' received. Research acknowledgement and findings will arrive separately.':result.error+' Open Pending requests to review, edit or explicitly retry.';}
    catch(error){get('dispatch-confirm-status').textContent=error.message;}
    finally{busy=false;get('dispatch-confirm').disabled=false;get('dispatch-confirm-cancel').disabled=false;}
  });
  function cancel(){if(busy)return;const entry=current;get('dispatch-confirm-dialog').close();if(entry?.status==='draft')post('/api/dispatch/cancel',{id:entry.id}).then(refresh).catch(e=>get('request-form-status').textContent=e.message);window.dispatchEvent(new Event('grad-compass:dispatch-cancelled'));}
  get('dispatch-confirm-cancel').addEventListener('click',cancel);get('dispatch-confirm-dialog').addEventListener('cancel',e=>{e.preventDefault();cancel();});
  get('open-pending-requests').addEventListener('click',async()=>{try{await refresh();get('pending-requests-dialog').showModal();}catch(error){get('research-toolbar-status').textContent=error.message;}});
  get('close-pending-requests').addEventListener('click',()=>get('pending-requests-dialog').close());
  window.addEventListener('grad-compass:discovery-updated',()=>refresh().catch(()=>{}));
  window.addEventListener('load',()=>refresh().catch(()=>{}));
  window.GradCompassDispatch=Object.freeze({prepare,refresh});
})();
