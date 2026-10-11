"""Offline structural and semantic checks for T1 synthetic exports only."""
import copy
import hashlib
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT/'schemas/applicant-profile-1.0.0.schema.json').read_text())

def check(value, schema, path='$'):
    if 'anyOf' in schema:
        for option in schema['anyOf']:
            try:
                check(value, option, path)
                return
            except ValueError:
                pass
        raise ValueError(f'{path}: no matching alternative')
    types = {'object': lambda v:isinstance(v,dict), 'array':lambda v:isinstance(v,list), 'string':lambda v:isinstance(v,str), 'number':lambda v:type(v) in (int,float), 'boolean':lambda v:type(v) is bool, 'null':lambda v:v is None}
    if 'type' in schema:
        allowed = schema['type'] if isinstance(schema['type'],list) else [schema['type']]
        require(any(types[t](value) for t in allowed), f'{path}: invalid type')
    if 'enum' in schema:
        require(any(type(value) is type(x) and value == x for x in schema['enum']), f'{path}: invalid enum')
    if isinstance(value,dict):
        require(all(k in value for k in schema.get('required',[])), f'{path}: missing key')
        props=schema.get('properties',{})
        if schema.get('additionalProperties') is False:
            require(not set(value)-set(props), f'{path}: unexpected key')
        for key,item in value.items():
            if key in props: check(item,props[key],path+'.'+key)
    if isinstance(value,list):
        require(len(value)>=schema.get('minItems',0),f'{path}: too few items')
        for i,item in enumerate(value): check(item,schema['items'],f'{path}[{i}]')
    if isinstance(value,str):
        require(len(value)>=schema.get('minLength',0),f'{path}: empty string')
        if 'pattern' in schema: require(re.search(schema['pattern'],value) is not None,f'{path}: invalid pattern')

def require(ok,message):
    if not ok: raise ValueError(message)

def validate(profile):
    check(profile,SCHEMA)
    for collection in ('sources','claims','issues'):
        ids=[v['id'] for v in profile[collection]]
        require(len(ids)==len(set(ids)),f'duplicate {collection} IDs')
    sources={s['id']:s for s in profile['sources']}
    claims={c['id']:c for c in profile['claims']}
    require(profile['parent_revision_id']!=profile['revision_id'],'self revision parent')
    require(all(s['synthetic']==profile['synthetic'] for s in sources.values()),'mixed synthetic and private sources')
    for source in sources.values():
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',source['captured_at']) is not None,'timestamp must be UTC')
    for c in claims.values():
        kind=c['kind']
        for ref in c['evidence']:
            require(ref['source_id'] in sources,'dangling evidence')
            if ref['locator_kind']=='page': require(re.fullmatch(r'[1-9][0-9]*',ref['locator']) is not None,'invalid page')
        related=c['related_claim_ids']
        require(len(related)==len(set(related)),'duplicate related claim')
        require(all(i in claims and i!=c['id'] for i in related),'dangling/self claim reference')
        if c['field'].startswith(('preferences.','goals.')):
            require(kind in ('preference','unknown'),'personal choice cannot be inferred')
        if kind in ('documented_fact','user_report','preference'):
            require(c['value'] is not None and c['evidence'],'assertion without value/evidence')
            expected='document' if kind=='documented_fact' else 'clarification'
            require(all(sources[r['source_id']]['kind']==expected for r in c['evidence']),'wrong evidence kind')
            require(all(sources[r['source_id']]['readability']!='unreadable' for r in c['evidence']),'unreadable assertion')
        if kind in ('unknown','conflict'):
            require(c['value'] is None and c['rationale'] and c['next_action'],'uncertainty needs null, reason and next action')
            require(any(c['id'] in i['claim_ids'] for i in profile['issues']),'uncertainty missing issue')
        if kind=='conflict':
            require(len(related)>=2,'conflict needs alternatives')
            require(all(claims[i]['field']==c['field'] and claims[i]['subject_id']==c['subject_id'] for i in related),'conflict alternatives mismatch')
        if kind=='inference': require(related and c['rationale'] and c['value'] is not None,'inference needs inputs and rationale')
    def visit(i,trail):
        require(i not in trail,'cyclic claim derivation')
        for dep in claims[i]['related_claim_ids']: visit(dep,trail|{i})
    for i in claims: visit(i,set())
    for issue in profile['issues']: require(all(i in claims for i in issue['claim_ids']),'dangling issue claim')
    require((profile['status']=='draft') == (profile['approval'] is None),'approval/lifecycle mismatch')

def verify_receipt(raw,receipt):
    p=json.loads(raw)
    validate(p)
    require(p['status']=='frozen','receipt requires frozen candidate')
    require(receipt['sha256']==hashlib.sha256(raw).hexdigest(),'frozen bytes changed')
    for key in ('schema_version','profile_id','revision_id','version_name','synthetic'):
        require(receipt[key]==p[key],'receipt target mismatch')
    for key in ('receipt_id','actor_type','actor_id','approved_at','scope','reliable_for_discovery'):
        require(receipt[key]==p['approval'][key],'receipt approval mismatch')
    require(receipt['decision']=='accepted' and receipt['actor_type']=='human' and receipt['reliable_for_discovery'] is True,'explicit reliable human approval required')

def main():
    profiles=[json.loads(p.read_text()) for p in sorted((ROOT/'examples').glob('applicant-*.json'))]
    for p in profiles: validate(p)
    failures=0
    def reject(label,fn):
        nonlocal failures
        try: fn()
        except ValueError: failures+=1
        else: raise AssertionError('accepted invalid case: '+label)
    base=profiles[0]
    mutations=[('dangling source',lambda p:p['claims'][0]['evidence'][0].update(source_id='missing')),('document preference',lambda p:p['claims'][4]['evidence'][0].update(source_id='src-cv')),('invented unknown',lambda p:p['claims'][5].update(value=0)),('empty conflict',lambda p:p['claims'][3].update(related_claim_ids=[])),('missing lineage input',lambda p:p['claims'][6].update(related_claim_ids=['missing'])),('extra field',lambda p:p.update(secret_path='/private')),('approval absent',lambda p:p.update(status='frozen')),('self parent',lambda p:p.update(parent_revision_id=p['revision_id'])),('bad page',lambda p:p['claims'][0]['evidence'][0].update(locator='0')),('duplicate ID',lambda p:p['claims'][1].update(id='degree')),('unreadable assertion',lambda p:p['sources'][0].update(readability='unreadable')),('inferred choice',lambda p:p['claims'][6].update(field='goals.career'))]
    for name,mutate in mutations:
        p=copy.deepcopy(base); mutate(p)
        reject(name,lambda:validate(p))
    raw=(ROOT/'examples/applicant-b-frozen.json').read_bytes()
    receipt=json.loads((ROOT/'examples/approval-receipt.json').read_text())
    verify_receipt(raw,receipt)
    reject('changed bytes',lambda:verify_receipt(raw+b' ',receipt))
    wrong=copy.deepcopy(receipt); wrong['revision_id']='wrong'
    reject('wrong revision',lambda:verify_receipt(raw,wrong))
    wrong2=copy.deepcopy(receipt); wrong2['decision']='rejected'
    reject('rejected approval',lambda:verify_receipt(raw,wrong2))
    old=json.loads((ROOT/'examples/applicant-b-draft.json').read_text()); new=json.loads(raw)
    require(old['claims'][1]['value']=='Kitchen supervisor' and new['claims'][1]['value']=='Pastry supervisor' and new['parent_revision_id']==old['revision_id'],'revision preservation')
    print(f'PASS: {len(profiles)} synthetic exports, receipt binding, revision preservation; {failures} invalid cases rejected.')
    print('Synthetic receipts do not establish real human approval. Private files were not read.')
if __name__=='__main__': main()
