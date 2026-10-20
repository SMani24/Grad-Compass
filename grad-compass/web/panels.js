"use strict";
(() => {
  const root=document.documentElement,get=id=>document.getElementById(id);
  let preferred={left:300,right:350},ready=false,saveTimer,sequence=0,saveQueue=Promise.resolve();
  const maximum=()=>Math.max(260,Math.min(720,Math.floor((innerWidth-320)/2)));
  function apply(){
    for(const side of ['left','right']){
      const actual=Math.max(260,Math.min(preferred[side],maximum()));
      root.style.setProperty(side==='left' ? '--results-width' : '--inspector-width',actual+'px');
      const handle=get('resize-'+side);
      for(const [key,value] of Object.entries({valuemin:260,valuemax:maximum(),valuenow:actual,valuetext:actual+' pixels'}))handle.setAttribute('aria-'+key,value);
    }
    window.dispatchEvent(new Event('grad-compass:panels-resized'));
  }
  function scheduleSave(){
    clearTimeout(saveTimer);const current=++sequence;get('panel-save-status').textContent='Saving panel widths…';
    saveTimer=setTimeout(async()=>{
      const value={...preferred};saveQueue=saveQueue.catch(()=>{}).then(()=>window.GradCompassResearch.post('/api/panel-widths',value));
      try{await saveQueue;if(current===sequence)get('panel-save-status').textContent='Panel widths saved for this profile.';}
      catch(error){if(current===sequence)get('panel-save-status').textContent=error.message+' Resize again to retry.';}
    },250);
  }
  for(const side of ['left','right']){
    const handle=get('resize-'+side);
    handle.addEventListener('pointerdown',event=>{
      if(!ready || event.button!==0)return;event.preventDefault();handle.setPointerCapture(event.pointerId);
      const start=event.clientX,width=parseInt(handle.getAttribute('aria-valuenow'),10);
      root.classList.add('resizing-panel');handle.classList.add('is-dragging');
      const move=e=>{preferred[side]=Math.round(Math.max(260,Math.min(maximum(),width+(e.clientX-start)*(side==='left'?1:-1))));apply();};
      const finish=()=>{root.classList.remove('resizing-panel');handle.classList.remove('is-dragging');handle.removeEventListener('pointermove',move);handle.removeEventListener('pointerup',finish);handle.removeEventListener('pointercancel',finish);scheduleSave();};
      handle.addEventListener('pointermove',move);handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);
    });
    handle.addEventListener('keydown',event=>{
      if(!ready || event.altKey || event.ctrlKey || event.metaKey || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();event.stopPropagation();
      const current=parseInt(handle.getAttribute('aria-valuenow'),10),delta=(event.shiftKey?40:10)*(event.key==='ArrowRight'?1:-1)*(side==='left'?1:-1);
      preferred[side]=event.key==='Home'?260:event.key==='End'?maximum():Math.max(260,Math.min(maximum(),current+delta));apply();scheduleSave();
    });
    handle.addEventListener('dblclick',()=>{preferred[side]=side==='left'?300:350;apply();scheduleSave();});
  }
  get('reset-panel-widths').addEventListener('click',()=>{preferred={left:300,right:350};apply();scheduleSave();});
  addEventListener('resize',apply);
  async function load(){
    try{const response=await fetch('/api/panel-widths',{cache:'no-store'});if(!response.ok)throw Error('Could not load panel widths');const value=await response.json();preferred={left:value.left,right:value.right};ready=true;apply();}
    catch(error){get('panel-save-status').textContent=error.message;}
  }
  window.addEventListener('grad-compass:workspace-loaded',load);
  // Scripts are deferred: initial workspace loading normally completes after this listener.
  if(window.GradCompassWorkspace)load();
})();
