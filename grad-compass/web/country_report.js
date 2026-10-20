"use strict";
/* A read-only presentation projection. Received producer bytes are never rewritten. */
const REPORT_SECTIONS=[['overview','At a glance'],['study','Study routes and language'],['funding','Funding and what it covers'],['costs','Tuition, living and upfront costs'],['work','Work and residence conditions'],['timing','Application timing'],['questions','Questions and next steps']];
function projectCountryReport(result,request,code){
  const findings=result.findings.filter(f=>f.kind==='country' && f.country_code===code);
  const sections=REPORT_SECTIONS.map(([id,title])=>({id,title,blocks:[]}));
  const add=(section,f,field,text)=>{
    if(typeof text!=='string' || !text.trim())return;
    sections.find(s=>s.id===section).blocks.push({id:f.finding_id+'/'+field,revision:f.finding_revision,finding_id:f.finding_id,field,text,
      observed_at:f.observed_at,academic_year:null,citation_scope:'finding',sources:f.sources || []});
  };
  for(const f of findings){
    const topic={funding:'funding',funding_routes:'funding',costs:'costs',work_rules:'work',language:'study',study_routes:'study',application_timing:'timing'}[f.field] || 'overview';
    add(topic,f,'summary',f.summary);
    for(const [field,section] of [['funding_routes','funding'],['costs','costs'],['work_rules','work'],['study_routes','study'],['language','study'],['application_timing','timing']])add(section,f,field,f[field]);
    (f.uncertainties || []).forEach((text,i)=>add('questions',f,'uncertainties/'+i,text));
  }
  const sources=[...new Map(findings.flatMap(f=>f.sources || []).map(s=>[s.source_id || s.source_url,s])).values()];
  return {schema_version:'app-report-view-0.1',country_code:code,request_id:request.request_id,result_id:result.result_id,result_revision:result.revision,
    result_digest:result.digest,report_date:result.issued_at || result.created_at,observations:[...new Set(findings.map(f=>f.observed_at).filter(Boolean))],
    applicable_academic_year:null,sections,sources,findings};
}
if(typeof module!=='undefined')module.exports={projectCountryReport,REPORT_SECTIONS};
if(typeof document!=='undefined')(() => {
  let assetsPromise;
  const name=code=>typeof BY_CODE!=='undefined'?BY_CODE[code]?.name || code:code;
  const flag=code=>typeof BY_CODE!=='undefined'?BY_CODE[code]?.flag || '🌐':'🌐';
  const date=value=>value ? new Date(value).toISOString().slice(0,10) : 'Unknown';
  const anchor=value=>'claim-'+encodeURIComponent(value);
  function render(ctx,result){
    const {section,current,node,action,openRequests}=ctx;
    const codes=[...new Set(result.findings.filter(f=>f.kind==='country').map(f=>f.country_code))];
    if(!codes.length)return false;
    const selected=result.findings.find(f=>f.finding_id===ctx.finding)?.country_code;
    const code=selected || (codes.includes(ctx.country)?ctx.country:codes[0]),report=projectCountryReport(result,current.request,code);
    const article=node('article',undefined,'country-report');article.id='country-report';article.dataset.country=code;
    const hero=node('header',undefined,'report-hero');
    const photo=node('figure',undefined,'report-photo');const photoFallback=node('span',flag(code),'photo-fallback');photo.append(photoFallback);
    assetsPromise ||= fetch('/report-assets.json').then(r=>r.ok?r.json():{}).catch(()=>({}));
    assetsPromise.then(assets=>{
      const asset=assets[code];if(!asset)return;
      const img=node('img');img.src=asset.path;img.alt=asset.alt;img.addEventListener('error',()=>img.remove());
      const caption=node('figcaption');const link=node('a',asset.credit+' · '+asset.license);link.href=asset.source_url;link.target='_blank';link.rel='noopener noreferrer';caption.append(link);photo.prepend(img);photo.append(caption);
    });
    const heading=node('div',undefined,'report-heading');heading.append(node('p','COUNTRY REPORT','eyebrow'),node('h1',flag(code)+' '+name(code)));
    const progress=window.GradCompassResearch.countryStatus(code,(window.GradCompassWorkspace?.universities || []).filter(u=>u.country_code===code).length);
    const badges=node('div',undefined,'report-badges');
    for(const text of ['Report available · revision '+result.revision+' · '+result.completion,'Factual review: '+[...new Set(report.findings.map(f=>f.review_status))].join(', '),'Human approval: '+[...new Set(report.findings.map(f=>f.human_approval?.state || 'unknown'))].join(', ')])badges.append(node('span',text));
    heading.append(badges,node('p',progress.discovery+'. This report covers a bounded request; it is not exhaustive country coverage.'));
    hero.append(photo,heading);article.append(hero);
    const facts=node('dl',undefined,'report-facts');
    for(const [label,value] of [['Observed',report.observations.map(date).join(', ') || 'Unknown'],['Report issued',date(report.report_date)],['Requested intake',current.request.preferences.intake || 'Not specified'],['Applicable academic year','Not separately supplied; see dated terms']]){const box=node('div');box.append(node('dt',label),node('dd',value));facts.append(box);}article.append(facts);
    if(codes.length>1){const label=node('label','Country in this report');const select=node('select');select.setAttribute('aria-label','Country in this report');for(const c of codes){const option=node('option',name(c));option.value=c;select.append(option);}select.value=code;select.addEventListener('change',()=>openRequests(current.request.request_id,result.revision,result.findings.find(f=>f.kind==='country' && f.country_code===select.value).finding_id));label.append(select);article.append(label);}
    const toolbar=node('div',undefined,'report-tools');const notes=action('Personal notes',()=>{rail.hidden=!rail.hidden;if(!rail.hidden)note.focus();},'toggle-report-notes');notes.className='quiet-action';toolbar.append(notes);article.append(toolbar);
    const layout=node('div',undefined,'report-reading-layout'),body=node('div',undefined,'report-reading-column'),rail=node('aside',undefined,'report-annotation-panel');rail.hidden=true;rail.setAttribute('aria-label','Personal country note');
    const note=node('textarea');note.rows=7;note.maxLength=4000;note.value=window.GradCompassResearch.personal(code).note;note.defaultValue=note.value;note.id='report-personal-note';
    const noteLabel=node('label','Your country note');noteLabel.htmlFor=note.id;const saved=node('p','Saved separately from research. This is the same country note used on the map.');saved.setAttribute('role','status');
    const saveNote=action('Save note',async()=>{const value=await ctx.post('/api/research/country',{country_code:code,note:note.value});note.defaultValue=note.value;window.GradCompassResearch.hydrate(value);saved.textContent='Country note saved.';window.dispatchEvent(new Event('grad-compass:personal-updated'));});saveNote.className='quiet-action';
    rail.append(node('h3','Personal notes'),noteLabel,note,saveNote,saved);
    const outline=node('nav',undefined,'report-outline');outline.setAttribute('aria-label','Report sections');for(const s of report.sections){const a=node('a',s.title);a.href='#report-'+s.id;a.addEventListener('click',e=>{e.preventDefault();document.getElementById('report-'+s.id).scrollIntoView({block:'start',behavior:'auto'});});outline.append(a);}body.append(outline);
    for(const s of report.sections){
      const group=node('section',undefined,'report-section');group.id='report-'+s.id;group.append(node('h2',s.title));
      if(s.id==='overview'){
        const glance=node('div',undefined,'report-glance');
        for(const [title,text] of [['Opportunities',report.sections.some(v=>v.id==='funding' && v.blocks.length)?'Study and funding evidence supplied; eligibility is not established.':'Review the received evidence for supported routes.'],['Obstacles','Read the conditions and unresolved caveats before making a decision.'],['Open questions',report.sections.find(v=>v.id==='questions').blocks.length+' caveats supplied. Missing sections remain unknown.']]){const card=node('div');card.append(node('h3',title),node('p',text));glance.append(card);}group.append(glance);
      }
      if(!s.blocks.length){group.append(node('p','Unknown — no separate '+s.title.toLowerCase()+' evidence was supplied.','report-unknown'));if(['study','timing'].includes(s.id)){const a=node('a','See the original overview for any supplied study or intake context.');a.href='#report-overview';a.addEventListener('click',e=>{e.preventDefault();document.getElementById('report-overview').scrollIntoView();});group.append(a);}}
      for(const block of s.blocks){
        const box=node('div',undefined,'report-claim');box.id=anchor(block.id);box.dataset.claim=block.id;
        box.append(node('p',block.text));
        const tools=node('div',undefined,'claim-tools');
        if(block.sources.length){const sources=node('details',undefined,'claim-sources');sources.append(node('summary','Sources supplied with this finding ('+block.sources.length+')'));sources.append(node('p','These are finding-level sources. Exact claim-to-source links were not supplied.'));
          for(const source of block.sources){const a=node('a',source.locator || source.source_url);if(/^https?:\/\//i.test(source.source_url)){a.href=source.source_url;a.target='_blank';a.rel='noopener noreferrer';}sources.append(a);}tools.append(sources);}
        tools.append(action('Give feedback',()=>{
          const card=[...section.querySelectorAll('.finding-card')].find(v=>v.dataset.finding===block.finding_id);if(!card)return;
          card.closest('details').open=true;card.querySelector('.feedback-form').hidden=false;const input=card.querySelector('.finding-comment');if(!input.value)input.value='Regarding '+s.title+' ['+block.id+']:\n';input.focus();card.scrollIntoView({block:'start'});
        }));box.append(tools);group.append(box);
      }
      body.append(group);
    }
    const sources=node('section',undefined,'report-section');sources.id='report-sources';sources.append(node('h2','Sources'),node('p','Sources below were supplied with the finding. Observation dates do not establish applicability to a later academic year.'));
    for(const source of report.sources){const row=node('div',undefined,'report-source');const link=node('a',source.locator || source.source_url);if(/^https?:\/\//i.test(source.source_url)){link.href=source.source_url;link.rel='noopener noreferrer';link.target='_blank';}row.append(link,node('p',source.source_url),node('p','Observed '+date(source.observed_at)));sources.append(row);}body.append(sources);
    layout.append(body,rail);article.append(layout);section.append(article);return true;
  }
  window.GradCompassCountryReport=Object.freeze({render,project:projectCountryReport});
})();
