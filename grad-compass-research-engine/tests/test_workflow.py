"""Synthetic-only integration checks; all generated data stays in run scratch."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from workflow import Store, build, candidate, freeze, encode, digest, receipt_from_interaction, normalize_markdown_whitespace, render, structured_fragment
from validate import verify_receipt

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        scratch = os.environ.get('PAPERCLIP_RUN_SCRATCH_DIR') or os.environ.get('PAPERCLIP_SCRATCH_DIR')
        if not scratch: raise RuntimeError('Set PAPERCLIP_RUN_SCRATCH_DIR to an authorized scratch directory')
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = Store(self.root, synthetic=True)
        self.manifest = dict(synthetic=True, sources=[], required=[dict(subject_id='applicant',field='preferences.location'),dict(subject_id='degree-a',field='education.gpa')])

    def source(self, name, text, field='education.degree', subject='degree-a', kind='document', value=None):
        self.store.put('intake/'+name, text.encode())
        item = dict(file=name, kind=kind, observations=[dict(subject_id=subject,field=field,line=1,quote=text.splitlines()[0],value=value or text.splitlines()[0])])
        self.manifest['sources'].append(item)
        return item

    def run_build(self, parent=None):
        name = 'manifest-'+str(len(list((self.root/'intake').glob('manifest-*'))))+'.json'
        self.store.put('intake/'+name, encode(self.manifest))
        return build(self.store, name, parent)

    def acceptance(self, p, request):
        return dict(id='synthetic-interaction', companyId='synthetic-company',issueId='synthetic-issue',kind='request_confirmation',status='accepted',effectiveResolverPolicy='human_only',resolvedByUserId='synthetic-human',resolvedByAgentId=None,payload=request['payload'],result=dict(outcome='accepted'),resolvedAt='2026-10-01T00:00:00Z')

    def test_generality_unknown_provenance_cache(self):
        self.source('arts.txt','BA in History')
        p, stats = self.run_build()
        self.assertEqual(stats, dict(parsed=1,reused=0))
        self.assertTrue(any(c['kind']=='unknown' and c['value'] is None for c in p['claims']))
        fact=p['claims'][0]
        self.assertEqual(fact['evidence'][0]['locator'],'line 1')
        second, stats = self.run_build(p['revision_id'])
        self.assertEqual(stats, dict(parsed=0,reused=1))
        self.assertEqual(fact,second['claims'][0])
        self.assertEqual(second['parent_revision_id'],p['revision_id'])
        self.source('work.txt','Laboratory technician','experience.role','job-a')
        third, stats = self.run_build(second['revision_id'])
        self.assertEqual(stats,dict(parsed=1,reused=1))
        self.assertEqual(third['claims'][0],fact)

    def test_reported_but_unverified_is_distinct_from_absent(self):
        item = self.source('invented-cv.txt', 'June 2022 – August 2022', 'experience.reported_dates', 'role-a')
        item['observations'][0]['context'] = 'Applicant CV reports this range; no appointment record supplied.'
        self.manifest['required'] = [dict(subject_id='role-a', field='experience.official_dates',
            rationale='No official appointment record supplied.', next_action='Request a record only if certification is needed.')]
        p, _ = self.run_build()
        reported = next(c for c in p['claims'] if c['field']=='experience.reported_dates')
        absent = next(c for c in p['claims'] if c['field']=='experience.official_dates')
        self.assertEqual(reported['value'], 'June 2022 – August 2022')
        self.assertEqual(reported['kind'], 'documented_fact')
        self.assertIn('Applicant CV reports', reported['context'])
        self.assertEqual(absent['kind'], 'unknown')
        self.assertIsNone(absent['value'])
        self.assertFalse(any(c['kind']=='conflict' for c in p['claims']))

    def test_repeatable_details_are_not_false_conflicts(self):
        self.source('letter.txt', 'Led tutorials', 'teaching.duties', 'role-a')
        self.source('cv.txt', 'Prepared exercises', 'teaching.duties', 'role-a')
        self.manifest['repeatable_fields'] = [dict(subject_id='role-a', field='teaching.duties')]
        p, _ = self.run_build()
        self.assertEqual(len([c for c in p['claims'] if c['field']=='teaching.duties']), 2)
        self.assertFalse(any(c['kind']=='conflict' for c in p['claims']))

    def test_structured_research_claim_rejects_line_fragment_and_accepts_complete_span(self):
        item = self.source('letter.txt', 'She developed methods for\nmonitoring coastal water quality.',
                           'experience.personal_work', 'research-a', value='She developed methods for')
        with self.assertRaisesRegex(ValueError, 'sentence fragment'):
            self.run_build()
        self.assertTrue(structured_fragment('to the Institute', 'experience.institution'))
        self.assertTrue(structured_fragment('research assistant who joined the group and worked on', 'experience.role'))
        item['observations'][0].update(end_line=2,
            quote='She developed methods for\nmonitoring coastal water quality.',
            value='She developed methods for monitoring coastal water quality.',
            normalization='markdown_whitespace')
        p, _ = self.run_build()
        claim = next(c for c in p['claims'] if c['field']=='experience.personal_work')
        self.assertEqual(claim['value'], 'She developed methods for monitoring coastal water quality.')
        self.assertEqual(claim['evidence'][0]['locator'], 'lines 1-2')

    def test_conflict_correction_and_parent_preserved(self):
        self.source('cv.txt','Kitchen supervisor','experience.role','job-a')
        self.source('letter.md','Pastry supervisor','experience.role','job-a')
        p,_=self.run_build()
        original=self.store.read('profiles/'+p['revision_id']+'.json')
        self.assertEqual(sum(c['kind']=='conflict' for c in p['claims']),1)
        self.source('answer.txt','Pastry supervisor','experience.role','job-a','clarification')
        self.manifest['corrections']=[dict(subject_id='job-a',field='experience.role',value='Pastry supervisor')]
        revised,_=self.run_build(p['revision_id'])
        claims=[c for c in revised['claims'] if c['field']=='experience.role']
        self.assertEqual(len(claims),1)
        self.assertEqual(claims[0]['kind'],'user_report')
        self.assertEqual(self.store.read('profiles/'+p['revision_id']+'.json'),original)

    def test_preference_requires_clarification(self):
        self.source('cv.txt','Canada','preferences.location','applicant')
        with self.assertRaises(ValueError): self.run_build()
        self.manifest['sources'][0]['kind']='clarification'
        p,_=self.run_build()
        self.assertEqual(p['claims'][0]['kind'],'preference')

    def test_source_change_invalidates_only_dependents(self):
        self.source('a.txt','Diploma in Design')
        self.source('b.txt','Library assistant','experience.role','job-b')
        p,_=self.run_build()
        (self.root/'intake/a.txt').write_text('Diploma in Music')
        self.manifest['sources'][0]['observations'][0].update(quote='Diploma in Music',value='Diploma in Music')
        revised,stats=self.run_build(p['revision_id'])
        self.assertEqual(stats,dict(parsed=1,reused=1))
        self.assertNotEqual(p['claims'][0]['id'],revised['claims'][0]['id'])
        self.assertEqual(p['claims'][1],revised['claims'][1])
        self.assertEqual(self.store.read('sources/'+p['sources'][0]['id']+'.bin'),b'Diploma in Design')

    def test_unreadable_and_unmapped_visible(self):
        self.store.put('intake/scan.pdf',b'%PDF synthetic unsupported')
        self.manifest['sources']=[dict(file='scan.pdf',kind='document')]
        p,_=self.run_build()
        self.assertEqual(p['sources'][0]['readability'],'unreadable')
        self.assertTrue(any(i['kind']=='unreadable' for i in p['issues']))
        self.source('plain.txt','Unmapped statement')['observations']=[]
        p,_=self.run_build()
        self.assertTrue(any(i['kind']=='ambiguous' for i in p['issues']))

    def test_quote_locator_and_value_must_match(self):
        item=self.source('a.txt','BA in Literature')
        for mutation in [dict(line=2),dict(quote='Invented'),dict(value='Doctorate')]:
            original=copy.deepcopy(item['observations'][0])
            item['observations'][0].update(mutation)
            with self.assertRaises(ValueError): self.run_build()
            item['observations'][0]=original

    def test_range_normalization_and_context(self):
        raw = 'Award: **BA**\nin __History__ and `Archives`\nUnrelated'
        item = self.source('record.md', raw)
        item['observations'] = [dict(subject_id='degree-a', field='education.degree', line=1, end_line=2,
            quote='**BA**\nin __History__ and `Archives`', value='BA in History and Archives',
            normalization='markdown_whitespace', context='Degree wording; dates remain unverified.')]
        p,_ = self.run_build()
        c = p['claims'][0]
        self.assertEqual(c['value'], 'BA in History and Archives')
        self.assertEqual(c['evidence'][0]['locator'], 'lines 1-2')
        self.assertIn('Degree wording;', c['context'])
        self.assertIn('does not establish semantic entailment', c['context'])
        self.assertEqual(self.store.read('sources/'+p['sources'][0]['id']+'.bin'), raw.encode())
        second,stats = self.run_build(p['revision_id'])
        self.assertEqual(stats, dict(parsed=0,reused=1))
        self.assertEqual(second['claims'][0], c)

    def test_range_and_normalization_falsification_rejected(self):
        item = self.source('record.md', '**BA**\nin __History__')
        valid = dict(subject_id='degree-a', field='education.degree', line=1, end_line=2,
                     quote='**BA**\nin __History__', value='BA in History', normalization='markdown_whitespace')
        for mutation in [dict(end_line=0), dict(end_line=3), dict(end_line=True), dict(line=2),
                         dict(quote='BA in History'), dict(value='MA in History'),
                         dict(normalization='semantic'), dict(normalization=None), dict(context=[])]:
            with self.subTest(mutation=mutation):
                item['observations'] = [dict(valid, **mutation)]
                with self.assertRaises(ValueError): self.run_build()
        self.assertEqual(normalize_markdown_whitespace('A **bold** __word__ `code`\n B'), 'A bold word code B')
        self.assertEqual(normalize_markdown_whitespace('A **unclosed __word `code'), 'A **unclosed __word `code')
        self.assertEqual(normalize_markdown_whitespace('***literal*** ```literal```'), '***literal*** ```literal```')

    def selection_fixture(self):
        self.source('cv.txt','Kitchen supervisor','experience.role','job-a')
        self.source('letter.md','Pastry supervisor','experience.role','job-a')
        parent,_ = self.run_build()
        self.store.put('intake/answer.txt', b'Use the role in the letter.\nKeep other details unchanged.')
        self.manifest['sources'].append(dict(file='answer.txt',kind='clarification',observations=[]))
        self.manifest['corrections'] = [dict(subject_id='job-a',field='experience.role',value='Pastry supervisor',
            source_file='letter.md',authority_file='answer.txt',authority_line=1,authority_quote='Use the role in the letter.')]
        return parent

    def test_document_selection_preserves_fact_and_authority(self):
        parent = self.selection_fixture()
        old = self.store.read('profiles/'+parent['revision_id']+'.json')
        revised,_ = self.run_build(parent['revision_id'])
        facts = [c for c in revised['claims'] if c['field']=='experience.role']
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]['kind'], 'documented_fact')
        self.assertEqual(facts[0]['value'], 'Pastry supervisor')
        self.assertEqual(facts[0]['evidence'], parent['claims'][1]['evidence'])
        choice = next(c for c in revised['claims'] if c['field']=='review.source_selection')
        self.assertEqual(choice['kind'], 'user_report')
        self.assertEqual(choice['value'], 'Use the role in the letter.')
        self.assertEqual(choice['related_claim_ids'], [facts[0]['id']])
        self.assertEqual(choice['evidence'][0]['locator'], 'line 1')
        self.assertNotIn('letter.md', encode(revised).decode())
        self.assertIn(facts[0]['evidence'][0]['source_id'], choice['context'])
        self.assertFalse(any(i['kind'] in ('conflict','ambiguous') for i in revised['issues']))
        self.assertEqual(self.store.read('profiles/'+parent['revision_id']+'.json'), old)

    def test_document_selection_requires_verified_authority(self):
        parent = self.selection_fixture()
        original = copy.deepcopy(self.manifest['corrections'][0])
        for mutation in [dict(authority_file='cv.txt'), dict(authority_file='absent.txt'),
                         dict(authority_line=2), dict(authority_line=True), dict(authority_quote='Choose the CV.'),
                         dict(source_file='cv.txt'), dict(value='Director')]:
            with self.subTest(mutation=mutation):
                self.manifest['corrections'] = [dict(original, **mutation)]
                with self.assertRaises(ValueError): self.run_build(parent['revision_id'])
        self.manifest['corrections'] = [original, original]
        with self.assertRaises(ValueError): self.run_build(parent['revision_id'])

    def test_transcription_retains_unreadable_original_and_gap_context(self):
        self.store.put('intake/scan.pdf', b'%PDF synthetic scan')
        self.manifest['sources'].append(dict(file='scan.pdf', kind='document'))
        item = self.source('transcription.md', 'Workshop participant', 'training.role', 'training-a', 'clarification')
        item['transcription_of'] = 'scan.pdf'
        self.manifest['required'] = [dict(subject_id='training-a', field='training.date',
            rationale='The transcription does not supply a date.', next_action='Verify the original date locally.')]
        p,_ = self.run_build()
        self.assertTrue(any(i['kind']=='unreadable' for i in p['issues']))
        self.assertEqual(next(c for c in p['claims'] if c['field']=='training.role')['kind'], 'user_report')
        gap = next(c for c in p['claims'] if c['field']=='training.date')
        self.assertEqual(gap['rationale'], 'The transcription does not supply a date.')
        review = self.store.read('reviews/'+p['revision_id']+'.html').decode()
        self.assertIn('User-supplied transcription; original not independently verified', review)
        self.assertIn('../intake/scan.pdf', review)
        self.assertIn('Verify the original date locally.', review)
        item['kind'] = 'document'
        with self.assertRaises(ValueError): self.run_build(p['revision_id'])

    def test_grouped_review_escapes_metadata_and_unsafe_links(self):
        item = self.source('record.md', '<script>alert(1)</script>', 'education.degree')
        item['observations'][0]['context'] = '<img src=x onerror=alert(2)>'
        p,_ = self.run_build()
        sid = p['sources'][0]['id']
        review = render(p, mappings={sid:dict(snapshot='https://example.invalid/remote', transcription_of='//example.invalid/file')})
        self.assertIn('<h2>Degree a</h2>', review)
        self.assertIn('<h3>Education / Degree</h3>', review)
        self.assertIn('3 added · 0 removed · 0 updated', review)
        self.assertIn('<summary>Evidence and claim metadata', review)
        self.assertIn('&lt;img', review)
        self.assertNotIn('<script', review)
        self.assertNotIn('<img', review)
        self.assertNotIn('href="http', review)
        self.assertNotIn('href="//', review)
        # Full IDs remain inspectable in collapsed metadata, not headings or summaries.
        import re
        visible = re.sub(r'<details>.*?</details>', '', review, flags=re.S)
        self.assertNotIn(p['revision_id'], visible)
        self.assertNotIn(p['claims'][0]['id'], visible)

    def test_cache_version_invalidates_old_parser_results(self):
        from unittest.mock import patch
        self.source('record.txt', 'Certificate in Accounting')
        with patch('workflow.VERSION', 'workflow-1.0.0'):
            old,_ = self.run_build()
        revised,stats = self.run_build(old['revision_id'])
        self.assertEqual(stats, dict(parsed=1,reused=0))
        self.assertNotEqual(old['claims'][0]['id'], revised['claims'][0]['id'])
        self.assertEqual(revised['schema_version'], '1.0.0')

    def test_review_uses_unambiguous_escaped_subject_titles(self):
        self.source('project.md', 'Archive <script>study</script>', 'project.title', 'project-1')
        p,_ = self.run_build()
        review = render(p)
        self.assertIn('<h2>Archive &lt;script&gt;study&lt;/script&gt;</h2>', review)
        self.assertIn('href="#subject-1">Archive &lt;script&gt;study&lt;/script&gt;</a>', review)
        self.assertIn('<code>project-1</code>', review)
        self.assertNotIn('<script>', review)
        self.source('other.md', 'Competing title', 'project.title', 'project-1')
        revised,_ = self.run_build(p['revision_id'])
        self.assertIn('<h2>Project 1</h2>', render(revised, p))

    def test_path_permissions_links_and_modes(self):
        with self.assertRaises(ValueError): self.store.read('../outside')
        with self.assertRaises(ValueError): self.store.read('/etc/passwd')
        (self.root/'intake/link').symlink_to('/etc/passwd')
        with self.assertRaises(ValueError): self.store.guard()
        (self.root/'intake/link').unlink()
        self.store.put('intake/wide.txt',b'synthetic')
        (self.root/'intake/wide.txt').chmod(0o644)
        with self.assertRaises(ValueError): self.store.guard()
        (self.root/'intake/wide.txt').chmod(0o600)
        with self.assertRaises(ValueError): Store(self.root,synthetic=False)

    def test_escaped_review_and_no_instruction_execution(self):
        text='<script>alert(1)</script> $(touch /never-execute)'
        self.source('a.txt',text)
        p,_=self.run_build()
        review=self.store.read('reviews/'+p['revision_id']+'.html').decode()
        self.assertNotIn('<script>',review)
        self.assertIn('&lt;script&gt;',review)
        self.assertIn('../sources/',review)

    def test_superseded_candidate_and_missing_inventory_rejected(self):
        self.source('a.txt','Certificate in Accounting')
        p,_=self.run_build()
        c,request=candidate(self.store,p['revision_id'],'synthetic-human')
        self.run_build(p['revision_id'])
        with self.assertRaises(ValueError): freeze(self.store,c['revision_id'],'synthetic-issue','synthetic-interaction',self.acceptance(c,request))
        (self.root/'intake/documents').mkdir(mode=0o700)
        self.store.put('intake/documents/unlisted.txt',b'Invented evidence')
        with self.assertRaises(ValueError): self.run_build(p['revision_id'])

    def test_human_digest_and_immutable_freeze(self):
        self.source('a.txt','Certificate in Horticulture')
        p,_=self.run_build()
        c,request=candidate(self.store,p['revision_id'],'synthetic-human')
        raw=self.store.read('candidates/'+c['revision_id']+'.json')
        accepted=self.acceptance(c,request)
        for update in [dict(status='pending'),dict(status='rejected'),dict(resolvedByAgentId='agent'),dict(resolvedByUserId='other'),dict(companyId='other'),dict(effectiveResolverPolicy='anyone')]:
            wrong=copy.deepcopy(accepted);wrong.update(update)
            with self.assertRaises(ValueError): receipt_from_interaction(raw,request,wrong,'synthetic-company','synthetic-issue')
        with self.assertRaises(ValueError): receipt_from_interaction(raw+b' ',request,accepted,'synthetic-company','synthetic-issue')
        receipt=freeze(self.store,c['revision_id'],'synthetic-issue','synthetic-interaction',accepted)
        frozen=self.store.read('frozen/'+c['revision_id']+'/profile.json')
        verify_receipt(frozen,receipt)
        self.assertEqual(frozen,raw)
        self.assertEqual((self.root/'frozen'/c['revision_id']/'profile.json').stat().st_mode & 0o777,0o400)
        with self.assertRaises(FileExistsError): freeze(self.store,c['revision_id'],'synthetic-issue','synthetic-interaction',accepted)
        revised,_=self.run_build(c['revision_id'])
        self.assertEqual(revised['parent_revision_id'],c['revision_id'])
        self.assertEqual(revised['status'],'draft')
        self.assertIsNone(revised['approval'])

    def test_confirmation_server_default_preserves_exact_approval(self):
        self.source('a.txt','Certificate in Horticulture')
        p,_=self.run_build()
        c,request=candidate(self.store,p['revision_id'],'synthetic-human')
        raw=self.store.read('candidates/'+c['revision_id']+'.json')
        # Historical immutable requests omit this UI field; Paperclip persists true.
        historical=copy.deepcopy(request)
        historical['payload'].pop('allowDeclineReason',None)
        accepted=copy.deepcopy(self.acceptance(c,historical))
        accepted['payload']['allowDeclineReason']=True
        receipt=receipt_from_interaction(raw,historical,accepted,'synthetic-company','synthetic-issue')
        verify_receipt(raw,receipt)
        for key,value in [('allowDeclineReason',False),('allowDeclineReason',1),('prompt','Changed approval terms'),('detailsMarkdown','Changed exact version'),('target',dict(type='custom',key='wrong',revisionId=digest(raw))),('extra','unexpected')]:
            wrong=copy.deepcopy(accepted)
            wrong['payload'][key]=value
            with self.assertRaises(ValueError): receipt_from_interaction(raw,historical,wrong,'synthetic-company','synthetic-issue')

if __name__=='__main__': unittest.main()
