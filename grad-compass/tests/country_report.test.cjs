const {test}=require('node:test');
const assert=require('node:assert/strict');
const {projectCountryReport,selectCountryReport}=require('../web/country_report.js');
const finding={kind:'country',country_code:'CAN',finding_id:'country:CAN:conditions',finding_revision:'revision-one',summary:'Original supplied words. No qualification omitted.',observed_at:'2026-10-19T11:00:00Z',funding_routes:'Conditional 2026–27 funding; 2027–28 unknown.',costs:'Unverified later-year costs.',work_rules:'Work is not secured funding.',uncertainties:['Unknown route.'],sources:[{source_id:'source-one',source_url:'https://example.invalid/source'}]};
const result={result_id:'result-one',revision:2,digest:'exact-digest',issued_at:'2026-10-20T12:00:00Z',findings:[finding]};
test('projection preserves exact received wording and source revision without mutating input',()=>{
 const original=JSON.stringify(result);const view=projectCountryReport(result,{request_id:'request-one'},'CAN');
 assert.equal(view.sections.find(s=>s.id==='funding').blocks[0].text,finding.funding_routes);
 assert.equal(view.sections[0].blocks[0].text,finding.summary);
 assert.equal(view.result_digest,'exact-digest');assert.equal(JSON.stringify(result),original);
 assert.equal(view.sections.find(s=>s.id==='funding').blocks[0].citation_scope,'finding');
});
test('missing sections and academic year remain unknown; observation and report dates stay distinct',()=>{
 const view=projectCountryReport(result,{request_id:'request-one'},'CAN');
 assert.equal(view.sections.find(s=>s.id==='timing').blocks.length,0);
 assert.equal(view.applicable_academic_year,null);assert.notEqual(view.observations[0],view.report_date);
});
test('stable field anchors are revision-bound and country scoped',()=>{
 const first=projectCountryReport(result,{request_id:'request-one'},'CAN');
 const next=projectCountryReport({...result,findings:[{...finding,finding_revision:'revision-two',funding_routes:'Changed words'}]},{request_id:'request-one'},'CAN');
 const block=v=>v.sections.find(s=>s.id==='funding').blocks[0];
 assert.equal(block(first).id,block(next).id);assert.notEqual(block(first).revision,block(next).revision);
 assert.equal(projectCountryReport(result,{request_id:'request-one'},'BEL').findings.length,0);
});
test('ordinary reading prefers prepared content; explicit historical results stay scoped',()=>{
 const item=(kind,result,version)=>({model:{kind},delivery:{result_revision:result},metadata:{report_date:'2026-10-22',canonical_document:{revision_number:version}}});
 const old=item('received_findings',1,1),prepared=item('prepared_report',2,3),newer=item('received_findings',3,3),reports=[newer,old,prepared];
 assert.equal(selectCountryReport(reports),prepared);
 assert.equal(selectCountryReport(reports,1),old);
 assert.equal(selectCountryReport(reports,3),newer);
 assert.equal(selectCountryReport(reports,99),null);
 assert.deepEqual(reports,[newer,old,prepared]);
});
