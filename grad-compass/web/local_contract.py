"""Request-bound real handoff validation. This validates structure, never factual truth."""
from urllib.parse import urlsplit
from web import research_envelopes as env


def require(condition,message):
    if not condition:raise ValueError(message)


def https(value):
    require(isinstance(value,str),'Supply a source URL')
    parsed=urlsplit(value)
    require(parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password,'Use an HTTPS source URL')


def validate_response(value,request,batch_reader):
    require(value.get('request_id')==request['request_id'] and type(value.get('request_revision')) is int
            and value['request_revision']==request['revision'] and value.get('request_digest')==request['digest'],
            'The response must bind the exact saved request revision and bytes')
    kind=value.get('envelope_kind')
    if kind=='acknowledgement':
        env.identifier(value.get('ack_id'));env.utc(value.get('acknowledged_at'))
        require(value.get('state') in ('accepted','rejected','needs_clarification'),'Use an explicit producer acknowledgement state')
        require(value.get('execution_progress') is None or isinstance(value['execution_progress'],str),'Execution progress must be explicitly supplied')
        return
    require(kind=='result','Receive an acknowledgement or result envelope')
    env.identifier(value.get('result_id'));env.utc(value.get('issued_at'))
    require(type(value.get('revision')) is int and value['revision']>=1,'Use a positive result revision')
    require(value.get('completion') in ('partial','complete'),'State partial or complete scope')
    if value['revision']==1:
        require(value.get('previous_result_revision') is None and value.get('previous_result_digest') is None,'The first result cannot invent a predecessor')
    else:
        require(type(value.get('previous_result_revision')) is int and value['previous_result_revision']==value['revision']-1,'Bind the preceding result revision')
        env.digest_reference(value.get('previous_result_digest'))
    findings=value.get('findings');associations=value.get('public_associations')
    require(isinstance(findings,list) and len(findings)<=1000 and isinstance(associations,list),'Use bounded typed findings and public associations')
    ids=set();counts={'institution':set(),'program':set()};validated=[]
    for association in associations:
        require(isinstance(association,dict),'Use a typed public association')
        env.identifier(association.get('batch_id'))
        env.digest_reference(association.get('manifest_sha256'))
        batch=batch_reader(association['batch_id'],association['manifest_sha256'])
        require(association.get('manifest_sha256')==batch['digest'],'Public association manifest digest mismatch')
        institution=next((r for r in batch['institutions'] if r['id']==association.get('institution_id')),None)
        require(institution is not None and institution['record_revision']==association.get('institution_record_revision'),'Public institution revision mismatch')
        require(institution['country_code'] in request['countries'],'A public institution is outside the requested countries')
        program=None
        if 'program_id' in association:
            program=next((r for r in batch['programs'] if r['id']==association['program_id']),None)
            require(program is not None and program['record_revision']==association.get('program_record_revision') and program['institution_id']==institution['id'],'Public program revision or parent mismatch')
        else:require('program_record_revision' not in association,'A program revision requires its program ID')
        validated.append((association,institution,program))
    for finding in findings:
        require(isinstance(finding,dict) and isinstance(finding.get('finding_id'),str) and finding['finding_id'] not in ids,'Use unique typed finding identities')
        ids.add(finding['finding_id']);env.identifier(finding.get('finding_revision'))
        require(finding.get('country_code') in request['countries'],'A finding is outside the requested countries')
        require(finding.get('kind') in ('country','institution','program'),'This request does not authorize faculty, outreach or other findings')
        if finding['kind']=='country':
            require(finding.get('country_schema_version')==env.COUNTRY_VERSION,'Unsupported country evidence version')
            for key in ('country_record_id','record_revision'):env.identifier(finding.get(key))
            env.utc(finding.get('observed_at'))
            require(isinstance(finding.get('summary'),str) and isinstance(finding.get('uncertainties'),list),'Preserve a summary, caveats and explicit unknowns')
            require(finding.get('evidence_status') in ('unknown','supplied') and finding.get('coverage') is not None,'Separate evidence coverage from review and suitability')
            expected={key:finding.get(key) for key in ('country_record_id','record_revision','finding_id','finding_revision','evidence_status','review_status')}
            require(finding.get('finding_ref')==expected,'Country finding reference does not bind exact revisions/status')
            review=finding.get('review',{})
            require(isinstance(review,dict) and review.get('kind')=='agent_factual_review' and review.get('decision') in ('pending','accepted','rejected','changes_required','unknown'),'Preserve the actual agent factual-review state')
            require(review.get('decision')==finding.get('review_status'),'Conflicting factual review states')
            for key in ('country_record_id','record_revision','finding_id','finding_revision'):
                require(review.get(key)==finding.get(key),'Review must bind the exact country/finding revision')
            if review.get('reviewed_at') is not None:env.utc(review['reviewed_at'])
            if review['decision'] in ('accepted','rejected','changes_required'):
                require(bool(review.get('reviewer_id')) and review.get('reviewed_at') is not None,'A review disposition requires its reviewer and UTC time')
            approval=finding.get('human_approval')
            require(isinstance(approval,dict) and approval.get('state') in ('not_requested','unknown','pending','accepted','rejected'),'Preserve human approval separately from agent review')
            if approval.get('state') in ('accepted','rejected'):
                require(bool(approval.get('approver_id')) and approval.get('approved_at') is not None,'Human approval cannot be inferred from an agent review')
                env.utc(approval['approved_at'])
            sources=finding.get('sources')
            require(isinstance(sources,list) and (sources or finding['evidence_status']=='unknown'),'Supplied evidence needs provenance')
            for source in sources:
                require(isinstance(source,dict) and bool(source.get('source_id')) and bool(source.get('source_revision')) and bool(source.get('locator')),'Keep source identities, revisions and page locators')
                https(source.get('source_url'));env.utc(source.get('observed_at'))
        else:
            require(request['scope']!='country_conditions','Country-conditions requests cannot add institution/program research')
            identity=finding.get('external_id');env.identifier(identity)
            match=next(((a,i,p) for a,i,p in validated if (i['id'] if finding['kind']=='institution' else p['id'] if p else None)==identity),None)
            require(match is not None,'Public findings must bind actual validated batch records')
            require(match[1]['country_code']==finding['country_code'],'Finding/public country mismatch')
            if finding['kind']=='program':require(finding.get('institution_id')==match[1]['id'],'Program finding parent mismatch')
            counts[finding['kind']].add(identity)
    bounds=request.get('bounds',{})
    # Associations also project records into discovery; none may bypass typed findings or limits.
    for association,institution,program in validated:
        require(institution['id'] in counts['institution'] or (program is not None and program['id'] in counts['program']),
                'Every public association needs a matching typed finding')
        counts['institution'].add(institution['id'])
        if program is not None:
            require(program['id'] in counts['program'],'A program association needs its typed finding')
    for kind,field in (('institution','institutions'),('program','programs')):
        require(len(counts[kind])<=bounds.get(field,0),'The result exceeds the saved request limits')
    candidate=value.get('candidate')
    if candidate is not None:
        require(isinstance(candidate,dict),'Use the original structured producer candidate')
        require(candidate.get('schema_version')=='producer-candidate-0.1.0','Unsupported producer candidate version')
        require(not (set(candidate)-{'schema_version','countries','institutions','programs','public_record_bindings',
                                    'mapping_sha256','source_sha256','publication_state','transformed_factual_review'}),
                'This handoff does not authorize additional private artifact categories')
        countries=candidate.get('countries',[])
        require(isinstance(countries,list) and all(isinstance(r,dict) and r.get('key') in request['countries'] for r in countries),
                'The candidate includes unrequested country findings')
        for row in countries:
            require(any(f['kind']=='country' and f['country_code']==row['key'] and f['country_record_id']==row.get('country_record_id')
                        and f['record_revision']==row.get('country_record_revision') for f in findings),
                    'Candidate country evidence must bind the returned country revision')
        bindings=candidate.get('public_record_bindings',[])
        require(isinstance(bindings,list) and all(isinstance(b,dict) for b in bindings),'Use typed producer public bindings')
        for kind,group in (('institution','institutions'),('program','programs')):
            rows=candidate.get(group,[])
            require(isinstance(rows,list) and len(rows)<=bounds.get(group,0),'Candidate records exceed the saved request limits')
            for row in rows:
                require(isinstance(row,dict) and any(b.get('kind')==kind and b.get('key')==row.get('key') and b.get('id') in counts[kind]
                    and any((i if kind=='institution' else p) is not None and (i if kind=='institution' else p)['id']==b['id']
                            and (i if kind=='institution' else p)['record_revision']==b.get('record_revision') for _,i,p in validated)
                    for b in bindings),'Private candidate records must bind the exact returned public revisions')
