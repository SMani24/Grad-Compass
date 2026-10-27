"use strict";
/* Read-only progress refresh is automatic; execution recovery is always explicit. */
(() => {
  const get=id=>document.getElementById(id),dialog=get('requests-dialog');
  const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const country=code=>typeof BY_CODE!=='undefined'?BY_CODE[code]?.name || code:code;
  const date=value=>value?new Date(value).toLocaleString():'Not checked yet';
  const scope=code=>({country_conditions:'Country conditions',universities_programs:'Universities and programs',refresh:'Follow-up / refresh'}[code] || code);
  let data=null,busy=false,timer=null,signature='';
  async function read(){const r=await fetch('/api/requests',{cache:'no-store'});const value=await r.json();if(!r.ok)throw Error(value.error || 'Could not load request history');data=value;render();return value;}
  function action(target,label,fn){const b=node('button',label);b.type='button';b.addEventListener('click',async()=>{b.disabled=true;try{await fn();}catch(e){get('requests-status').textContent=e.message;}finally{b.disabled=false;}});target.append(b);return b;}
  function link(target,label,url){if(!url)return;const a=node('a',label,'request-link');a.href=url;a.target='_blank';a.rel='noopener noreferrer';target.append(a);}
  function matches(row){
    const filter=get('requests-filter').value,query=get('requests-search').value.trim().toLowerCase();
    const pending=['draft','pending','uncertain','dispatching'].includes(row.status),finished=['complete','cancelled','superseded'].includes(row.status);
    return (filter==='all' || filter==='attention' && row.needs_attention || filter==='pending' && pending || filter==='finished' && finished || filter==='active' && !pending && !finished)
      && (!query || [row.countries.map(country).join(' '),row.scope,row.intake,row.task?.identifier,row.id].join(' ').toLowerCase().includes(query));
  }
  async function refresh(identity=null){
    if(busy)return;busy=true;get('refresh-requests').disabled=true;get('requests-status').textContent='Checking Paperclip and retained delivery status… Saved history remains available.';
    try{await window.GradCompassResearch.post('/api/requests/refresh',identity?{request_id:identity}:{});await read();get('requests-status').textContent='Status updated.';}
    catch(e){get('requests-status').textContent=e.message;}
    finally{busy=false;get('refresh-requests').disabled=false;}
  }
  async function open(filter='all',identity=null){
    get('requests-filter').value=filter;get('requests-search').value='';signature='';
    if(!dialog.open)dialog.showModal();
    try{await read();if(identity){const card=[...get('requests-list').children].find(n=>n.dataset.request===identity);card?.scrollIntoView({block:'start'});}refresh();}catch(e){get('requests-status').textContent=e.message;}
  }
  function render(){
    if(!data)return;
    const count=data.attention_count+data.unassociated_delivery_errors.length;
    get('open-requests').hidden=false;get('open-requests').textContent=count?'Requests · '+count+' need attention':'Requests';
    get('requests-notification').hidden=!count;
    const failures=data.requests.filter(r=>r.status==='failed');
    get('requests-notification-text').textContent=failures.length?failures.map(r=>r.countries.map(country).join(', ')+': '+r.label.toLowerCase()).join(' · ')+'. Saved requests and work are preserved.':count+' request or delivery item(s) need attention. Last-known states are retained.';
    if(!dialog.open)return;
    const currentProfile=document.getElementById('active-profile')?.textContent;
    get('requests-profile').textContent=currentProfile || 'Current local profile';
    const next=JSON.stringify([data.requests,get('requests-filter').value,get('requests-search').value,data.unassociated_delivery_errors]);
    if(next===signature || !window.getSelection().isCollapsed)return;signature=next;
    const opened=new Set([...get('requests-list').querySelectorAll('details[open]')].map(d=>d.dataset.details));
    const list=get('requests-list'),fragment=document.createDocumentFragment();
    const rows=data.requests.filter(matches);
    for(const row of rows){
      const card=node('article',undefined,'tracked-request');card.dataset.request=row.request_id || row.id;card.dataset.status=row.status;
      const heading=node('div',undefined,'tracked-request-heading');heading.append(node('h3',row.countries.map(country).join(', ')),node('span',row.label,'tracked-request-state'));card.append(heading);
      card.append(node('p',scope(row.scope)+' · Intake: '+(row.intake || 'Not specified'),'tracked-request-summary'));
      card.append(node('p','Created '+date(row.created_at)+' · Updated '+date(row.updated_at),'tracked-request-dates'));
      const stage=row.stage.startsWith('Grad Compass:')?'Country report coordination':row.stage.replace(/^([A-Z]{3}):/,(_,code)=>country(code)+':');
      card.append(node('p','Current step: '+stage));
      if(row.notice)card.append(node('p',row.notice,'request-persistent-notice'));
      if(row.tracking.connection_error)card.append(node('p',row.tracking.connection_error+' Last successful status check: '+date(row.last_success_at)+'. This is not a new confirmed research failure.','request-connection-notice'));
      card.append(node('p',row.work_saved));
      card.append(node('p','Last status check: '+date(row.last_checked_at)+' · Last reported activity: '+date(row.last_activity_at),'tracked-request-dates'));
      if(row.task)card.append(node('p','Paperclip task '+row.task.identifier+' · same confirmed request retained.','tracked-request-dates'));
      if(row.status==='failed' || row.status==='blocked')card.append(node('p',row.next_action,'request-next-action'));
      if(row.status==='failed'){
        const recovery=node('details');recovery.dataset.details=row.id+':recovery';recovery.open=opened.has(recovery.dataset.details);recovery.append(node('summary','How to recover this request'));
        const steps=node('ol');
        for(const text of ['Open “Resume / recover in Paperclip” below. It opens the existing failed step, not a new request.',row.tracking.latest?.failure?.includes('not trusted')?'A Paperclip board operator must repair the researcher’s working-folder setup using the existing authorized Grad Compass repository. Keep the trust checks enabled.':'Review the recorded problem and any provider limits. Complete any required operator repair or human decision before retrying.','Use Paperclip’s supported recovery card to explicitly resume the original assigned owner, preserving the confirmed scope. Do not submit another research task.','Return here and refresh status. Saved findings, earlier reports and annotations remain available.'])steps.append(node('li',text));
        recovery.append(steps,node('p','Dave coordinates execution recovery; Marry supports runtime and delivery diagnosis. In-app restart is unavailable until a safe conditional retry capability is verified.'));card.append(recovery);
      }
      for(const error of row.delivery_errors)card.append(node('p','Delivery problem: '+error.error,'request-persistent-notice'));
      if(row.reports.length){
        const details=node('details');details.dataset.details=row.id+':reports';details.open=opened.has(details.dataset.details);details.append(node('summary',row.batch_progress?.label || 'Country progress and review'));
        if(row.batch_progress)details.append(node('p',row.batch_progress.qualification));
        for(const report of row.reports){
          const section=node('section',undefined,'request-country-progress');section.dataset.country=report.country;
          section.append(node('h4',country(report.country)),node('p',report.available?report.version+' published · Overview '+(report.overview==='published'?'published':'not published')+' · Photograph '+report.photo.replaceAll('_',' '):'No prepared report published for this request.'));
          if(report.review)section.append(node('p','Report review: '+(report.review.report?.state || 'unknown').replaceAll('_',' ')+' · Overview review: '+(report.review.overview?.state || 'not published').replaceAll('_',' ')+' · Human approval: '+(report.review.human?.state || 'unknown').replaceAll('_',' ')));
          for(const pending of report.outstanding || []){
            section.append(node('p',pending.item+' — '+pending.owner+': '+pending.action,'request-next-action'));
            if(pending.reason){const recorded=node('details');recorded.append(node('summary','Recorded delivery note'),node('p',pending.reason));section.append(recorded);}
          }
          const uncertainties=(report.coverage || []).filter(c=>c.state==='investigated_unresolved');
          if(uncertainties.length){const more=node('details');more.append(node('summary','Research uncertainties (separate from delivery)'));for(const c of uncertainties)more.append(node('p',c.title+': '+c.detail));section.append(more);}
          action(section,report.available?'Read '+country(report.country)+' report':'View '+country(report.country)+' findings',()=>{dialog.close();window.GradCompassResearch.openRequests(row.request_id,null,null,false,report.country);});
          details.append(section);
        }
        if(row.execution_progress)details.append(node('p','Producer’s acknowledgement progress (historical): '+row.execution_progress));
        card.append(details);
      }
      const actions=node('div',undefined,'tracked-request-actions');
      if(row.request_id){
        action(actions,row.results_count?'Open findings & reports':'View saved request',()=>{dialog.close();window.GradCompassResearch.openRequests(row.request_id);});
        action(actions,'Refresh status',()=>refresh(row.request_id));
      }
      link(actions,'Open in Paperclip',row.task_url);
      if(['failed','blocked'].includes(row.status))link(actions,'Resume / recover in Paperclip',row.recovery_url);
      if(['draft','pending','uncertain','dispatching'].includes(row.dispatch_status)){
        action(actions,row.dispatch_status==='draft'?'Review and confirm':'Review dispatch / retry',async()=>{
          const response=await fetch('/api/dispatch',{cache:'no-store'}),dispatch=await response.json(),entry=dispatch.entries.find(e=>e.id===row.dispatch_id);
          if(!entry)throw Error('Saved dispatch was not found in this profile');
          dialog.close();await window.GradCompassDispatch.review(entry);
        });
        if(['draft','pending'].includes(row.dispatch_status)){
          action(actions,'Edit pending request',async()=>{
            const r=await fetch('/api/dispatch',{cache:'no-store'}),v=await r.json(),entry=v.entries.find(e=>e.id===row.dispatch_id);
            if(!entry || entry.attempts)throw Error('Reconcile the existing attempt before editing');
            dialog.close();window.GradCompassResearch.openRequest({...entry.payload,edit_id:entry.id,request_only:!entry.payload.remember_preferences});
          });
          action(actions,'Cancel pending request',async()=>{await window.GradCompassResearch.post('/api/dispatch/cancel',{id:row.dispatch_id});await read();});
        }
      }
      card.append(actions);
      const technical=node('details');technical.dataset.details=row.id+':technical';technical.open=opened.has(technical.dataset.details);technical.append(node('summary','Task, attempts and technical details'),node('pre',JSON.stringify({request_id:row.request_id,dispatch_id:row.dispatch_id,dispatch_status:row.dispatch_status,dispatch_attempts:row.dispatch_history,execution:row.tracking.latest,observations:row.tracking.history,delivery_errors:row.delivery_errors},null,2)));card.append(technical);
      fragment.append(card);
    }
    if(!rows.length)fragment.append(node('p','No requests match this filter. All requests includes dispatched and completed work.'));
    if(data.unassociated_delivery_errors.length){const section=node('details');section.append(node('summary','Unassociated delivery problems'));for(const error of data.unassociated_delivery_errors)section.append(node('p',error.file+': '+error.error));fragment.append(section);}
    list.replaceChildren(fragment);
  }
  get('open-requests').addEventListener('click',()=>open());get('requests-attention').addEventListener('click',()=>open('attention'));
  get('close-requests').addEventListener('click',()=>dialog.close());get('refresh-requests').addEventListener('click',()=>refresh());
  for(const id of ['requests-filter','requests-search'])get(id).addEventListener(id==='requests-search'?'input':'change',()=>{signature='';render();});
  function initialize(){if(!window.GradCompassWorkspace?.operational)return;read().catch(()=>{});if(!timer)timer=setInterval(()=>read().catch(()=>{}),5000);}
  window.addEventListener('grad-compass:workspace-loaded',initialize);window.addEventListener('grad-compass:discovery-updated',initialize);window.addEventListener('load',initialize);
  window.addEventListener('focus',()=>{if(window.GradCompassWorkspace?.operational){read().catch(()=>{});refresh();}});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden && window.GradCompassWorkspace?.operational){read().catch(()=>{});refresh();}});
  window.addEventListener('pagehide',()=>clearInterval(timer));
  window.GradCompassRequests=Object.freeze({open,refresh,read});
})();
