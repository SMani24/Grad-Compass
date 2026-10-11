"""Regenerate only synthetic T1 assets. No private input is read."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def obj(properties, required=None):
    return {'type':'object','properties':properties,'required':list(properties) if required is None else required,'additionalProperties':False}
def arr(items, minimum=0): return {'type':'array','items':items,'minItems':minimum}
def enum(*values): return {'enum':list(values)}
s = {'type':'string','minLength':1}
nullable = {'type':['string','null'],'minLength':1}
evidence = obj({'source_id':s,'locator_kind':enum('page','section','answer','unavailable'),'locator':s})
source = obj({'id':s,'kind':enum('document','clarification'),'label':s,'sha256':{'type':'string','pattern':'^[a-f0-9]{64}$'},'readability':enum('readable','partial','unreadable'),'captured_at':s,'synthetic':{'type':'boolean'}})
claim = obj({'id':s,'subject_id':s,'field':{'type':'string','pattern':'^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'},'kind':enum('documented_fact','user_report','preference','inference','conflict','unknown'),'value':{'type':['string','number','boolean','null'],'minLength':1},'context':nullable,'evidence':arr(evidence),'related_claim_ids':arr(s),'rationale':nullable,'next_action':nullable})
issue = obj({'id':s,'kind':enum('missing','unreadable','ambiguous','conflict'),'claim_ids':arr(s,1),'detail':s,'next_action':s})
approval = obj({'receipt_id':s,'actor_type':enum('human'),'actor_id':s,'approved_at':s,'reliable_for_discovery':enum(True),'scope':enum('profile_only')})
schema = obj({'schema_version':enum('1.0.0'),'profile_id':s,'revision_id':s,'parent_revision_id':nullable,'version_name':s,'status':enum('draft','frozen'),'synthetic':{'type':'boolean'},'sources':arr(source),'claims':arr(claim,1),'issues':arr(issue),'approval':{'anyOf':[{'type':'null'},approval]}})
schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:grad-compass:applicant-profile:1.0.0','title':'Applicant profile 1.0.0'})
(ROOT/'schemas/applicant-profile-1.0.0.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
from hashlib import sha256

def src(i,kind,label,body):
    return dict(id=i,kind=kind,label=label,sha256=sha256(body.encode()).hexdigest(),readability='readable',captured_at='2026-10-01T00:00:00Z',synthetic=True)
def ref(i,kind,loc):return dict(source_id=i,locator_kind=kind,locator=loc)
def c(i,field,kind,value,ev=(),related=(),rationale=None,next_action=None):
    return dict(id=i,subject_id='subject-1',field=field,kind=kind,value=value,context=None,evidence=list(ev),related_claim_ids=list(related),rationale=rationale,next_action=next_action)
sources=[src('src-transcript','document','Invented transcript','Bachelor of History; completed 2024.'),src('src-cv','document','Invented CV','Degree completed 2023.'),src('src-answer','clarification','Synthetic explicit answer','I prefer remote study.')]
claims=[c('degree','education.degree','documented_fact','Bachelor of History',[ref('src-transcript','page','1')]),c('year-a','education.completion_year','documented_fact',2024,[ref('src-transcript','page','1')]),c('year-b','education.completion_year','documented_fact',2023,[ref('src-cv','section','Education')]),c('year-conflict','education.completion_year','conflict',None,related=['year-a','year-b'],rationale='Supplied sources disagree.',next_action='Ask which year is correct and request supporting evidence.'),c('location','preferences.delivery','preference','remote',[ref('src-answer','answer','1')]),c('budget','preferences.budget','unknown',None,rationale='No explicit answer supplied.',next_action='Ask the applicant for an optional budget and currency.'),c('recency','education.recent_completion','inference',True,related=['year-a','year-b'],rationale='Both reported years fall within five years of 2026; the exact year remains disputed.')]
a=dict(schema_version='1.0.0',profile_id='synthetic-a',revision_id='revision-a1',parent_revision_id=None,version_name='synthetic-a-v1',status='draft',synthetic=True,sources=sources,claims=claims,issues=[dict(id='issue-year',kind='conflict',claim_ids=['year-conflict'],detail='Two completion years.',next_action='Clarify with applicant.'),dict(id='issue-budget',kind='missing',claim_ids=['budget'],detail='Budget not supplied.',next_action='Ask explicitly if needed.')],approval=None)
b=dict(schema_version='1.0.0',profile_id='synthetic-b',revision_id='revision-b1',parent_revision_id=None,version_name='synthetic-b-v1',status='draft',synthetic=True,sources=[src('src-answer-b','clarification','Invented vocational background','Diploma in Culinary Arts; kitchen supervisor.')],claims=[c('degree-b','education.degree','user_report','Diploma in Culinary Arts',[ref('src-answer-b','answer','1')]),c('role-b','experience.role','user_report','Kitchen supervisor',[ref('src-answer-b','answer','1')]),c('grade-b','education.grade','unknown',None,rationale='Transcript not supplied.',next_action='Request transcript if grade is required.')],issues=[dict(id='issue-grade',kind='missing',claim_ids=['grade-b'],detail='No documented grade.',next_action='Request evidence.')],approval=None)
import copy
revised=copy.deepcopy(b)
revised.update(revision_id='revision-b2',parent_revision_id='revision-b1',version_name='synthetic-b-v2',status='frozen',approval=dict(receipt_id='synthetic-receipt-b2',actor_type='human',actor_id='synthetic-human',approved_at='2026-10-01T01:00:00Z',reliable_for_discovery=True,scope='profile_only'))
revised['sources'].append(src('src-correction','clarification','Invented correction','My role is pastry supervisor; grade remains unknown and accepted for this synthetic scenario.'))
revised['claims'][1].update(value='Pastry supervisor',evidence=[ref('src-correction','answer','1')])
for name,data in [('applicant-a-draft',a),('applicant-b-draft',b),('applicant-b-frozen',revised)]:
    (ROOT/f'examples/{name}.json').write_text(json.dumps(data,indent=2)+'\n')
raw=(ROOT/'examples/applicant-b-frozen.json').read_bytes()
receipt=dict(receipt_id='synthetic-receipt-b2',synthetic=True,decision='accepted',actor_type='human',actor_id='synthetic-human',profile_id='synthetic-b',revision_id='revision-b2',version_name='synthetic-b-v2',schema_version='1.0.0',sha256=sha256(raw).hexdigest(),reliable_for_discovery=True,scope='profile_only',approved_at='2026-10-01T01:00:00Z')
(ROOT/'examples/approval-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
