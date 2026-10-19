"""Focused private-inbox delivery checks with invented local records only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'grad-compass'))
sys.path.insert(0, str(ROOT / 'grad-compass-research-engine' / 'scripts'))
from web import research_envelopes as env
from web.inbox import InboxReceiver
from web.local import LocalWorkspace
from publish_local_response import publish


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='grad-compass-publish-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = LocalWorkspace(self.root / 'workspace')
        self.store = self.workspace.research
        payload = {'submission_key': str(uuid4()), 'countries': ['CAN'], 'scope': 'country_conditions',
                   'preferences': {}, 'remember_preferences': False, 'limits': None, 'context': None,
                   'parent_request_id': None, 'prior_results': [], 'bounds': {'institutions': 0, 'programs': 0}}
        self.request = self.store.submit(payload)['request']
        self.handoff = Path(self.store.export(self.request['request_id'])['path'])

    def response_file(self, value, name='response.json'):
        path = self.root / name
        path.write_text(json.dumps(env.packet(value)), encoding='utf-8')
        return path

    def binding(self):
        return {'schema_version': '0.1.0', 'synthetic': False, 'request_id': self.request['request_id'],
                'request_revision': self.request['revision'], 'request_digest': self.request['digest']}

    def test_ack_partial_final_replay_restart_and_unfinished_write(self):
        ack = {**self.binding(), 'envelope_kind': 'acknowledgement', 'ack_id': str(uuid4()),
               'acknowledged_at': '2026-10-19T00:00:00Z', 'state': 'accepted', 'execution_progress': 'Started'}
        first, created = publish(self.handoff, self.response_file(ack))
        self.assertTrue(created)
        self.assertFalse(publish(self.handoff, self.response_file(ack))[1])
        inbox = self.workspace.directory / 'inbox'
        (inbox / '.tmp-unfinished').write_text('{')
        receiver = InboxReceiver(self.workspace, quiet_seconds=0)
        self.assertEqual(receiver.check()['received'], 1)
        self.assertEqual(receiver.check()['received'], 0)
        result = {**self.binding(), 'envelope_kind': 'result', 'result_id': str(uuid4()),
                  'result_revision': 1, 'previous_result_revision': None, 'previous_result_digest': None,
                  'issued_at': '2026-10-19T00:01:00Z', 'completion': 'partial',
                  'findings': [], 'public_associations': []}
        partial, _ = publish(self.handoff, self.response_file(result))
        prior = env.packet(result)['sha256']
        final = {**result, 'result_revision': 2, 'previous_result_revision': 1,
                 'previous_result_digest': prior, 'completion': 'complete'}
        complete, _ = publish(self.handoff, self.response_file(final))
        self.assertEqual(receiver.check()['received'], 2)
        self.assertEqual(receiver.status()['errors'], [])
        reopened = LocalWorkspace(self.workspace.directory)
        self.assertEqual(InboxReceiver(reopened, quiet_seconds=0).check()['received'], 0)
        saved = reopened.research.request(self.request['request_id'])
        self.assertEqual(len(saved['results']), 2)
        self.assertEqual(saved['results'][-1]['envelope']['completion'], 'complete')
        self.assertEqual(reopened.research.scan_inbox()['received'], 0)
        self.assertEqual({first, partial, complete}, set(inbox.glob('*.json')))

    def test_wrong_binding_invalid_transport_and_conflict(self):
        ack = {**self.binding(), 'envelope_kind': 'acknowledgement', 'ack_id': str(uuid4()),
               'acknowledged_at': '2026-10-19T00:00:00Z', 'state': 'accepted', 'execution_progress': None}
        with self.assertRaises(ValueError):
            publish(self.handoff, self.response_file({**ack, 'request_digest': '0' * 64}))
        bad = self.response_file(ack)
        bad.write_text('{bad', encoding='utf-8')
        with self.assertRaises(ValueError): publish(self.handoff, bad)
        publish(self.handoff, self.response_file(ack))
        receiver = InboxReceiver(self.workspace, quiet_seconds=0)
        self.assertEqual(receiver.check()['received'], 1)
        changed = {**ack, 'ack_id': str(uuid4())}
        publish(self.handoff, self.response_file(changed, 'conflict.json'))
        receipt = receiver.check()
        self.assertEqual(len(receipt['errors']), 1)
        self.assertEqual(self.store.request(self.request['request_id'])['acknowledgement']['ack_id'], ack['ack_id'])


if __name__ == '__main__': unittest.main()
