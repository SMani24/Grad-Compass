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
  function render(ctx,result){
    const codes=[...new Set(result.findings.filter(f=>f.kind==='country').map(f=>f.country_code))];
    if(!codes.length)return false;
    const selected=result.findings.find(f=>f.finding_id===ctx.finding)?.country_code;
    const code=selected || (codes.includes(ctx.country)?ctx.country:codes[0]);
    const article=ctx.node('article',undefined,'country-report');article.id='country-report';article.dataset.country=code;
    article.append(ctx.node('p','Opening the saved country report…','reader-status'));ctx.section.append(article);
    window.GradCompassReportReader.upgrade(article,ctx,code);return true;
  }
  window.GradCompassCountryReport=Object.freeze({render,project:projectCountryReport});
})();
