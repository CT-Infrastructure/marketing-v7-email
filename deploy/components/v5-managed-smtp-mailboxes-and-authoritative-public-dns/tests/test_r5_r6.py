"""Caller ownership and atomic intake clock-domain regressions."""
import copy
import json
import unittest
from datetime import datetime, timezone
from test_mock import req, evidence, proof, CONFIG
from mock import Mock, SyntheticVerifier, UTC_ORIGIN, simulation_time
from conformance import key, validate

class CorrectionsR5R6(unittest.TestCase):
    def test_caller_mutation_preserves_recovery_and_identity(self):
        for outcome in ('OCCURRED', 'NOT_OCCURRED'):
            with self.subTest(outcome=outcome):
                caller = req()
                saved = copy.deepcopy(caller)
                verifier = SyntheticVerifier({b'proof': proof(saved, outcome=outcome)})
                m = Mock(CONFIG, verifier=verifier)
                original = m.simulate(caller, evidence(caller), scenario='TIMEOUT_AFTER_SUBMIT')
                before = m.dump()
                caller['identity']['approved_revision'] = 'synthetic-mutated'
                caller['identity']['source_event_id'] = 'synthetic-mutated-event'
                caller['payload_ref'] = 'synthetic-mutated-payload'
                self.assertEqual(before, m.dump())
                self.assertEqual(original, m.simulate(saved, {}))
                state = json.loads(m.dump())['actions'][saved['action_key']]
                self.assertEqual(state['request'], saved)
                self.assertEqual(state['history'], [original])
                for receipt in (state['receipt'], *state['history']):
                    validate('action-receipt', receipt)
                    self.assertEqual(receipt['action_identity'], saved['identity'])
                    self.assertEqual(receipt['action_key'], key(receipt['action_identity']))
                restored = Mock.restore(m.dump(), CONFIG, verifier=verifier)
                self.assertEqual(restored.simulate(saved, {}), original)
                self.assertEqual(restored.intake(b'proof', now=101), 'RECEIPT_ONLY')
                latest = restored.simulate(saved, {})
                self.assertEqual(latest['reconciliation_outcome'], outcome)
                self.assertEqual(latest['status'], 'RECONCILED')
                self.assertNotEqual(latest['receipt_id'], original['receipt_id'])
                self.assertEqual(restored.actions[saved['action_key']]['history'][0], original)
                self.assertEqual(latest['action_identity'], saved['identity'])
                self.assertEqual(latest['action_key'], key(latest['action_identity']))
                again = Mock.restore(restored.dump(), CONFIG, verifier=verifier)
                self.assertEqual(again.simulate(saved, {}), latest)
                self.assertEqual(again.intake(b'proof', now=101), 'DUPLICATE_NO_EFFECT')
                self.assertEqual(len(again.actions), 1)
                self.assertEqual(again.outbound_state, 'HOLD')

    def test_invalid_intake_clocks_are_atomic_for_every_kind_and_duplicate(self):
        invalid = (-1, True, False, 100.5, '100', None, 10**30, {}, [])
        for kind in ('suppression','revocation','delete','reply','status','reconcile'):
            for duplicate in (False, True):
                for field in ('now','at'):
                    for value in invalid:
                        with self.subTest(kind=kind, duplicate=duplicate, field=field, value=value):
                            r = req()
                            good = proof(r, kind=kind, outcome='UNKNOWN', at=100)
                            bad = copy.deepcopy(good)
                            if field == 'at': bad['at'] = value
                            verifier = SyntheticVerifier({b'good':good,b'bad':bad})
                            m = Mock(CONFIG, verifier=verifier)
                            m.simulate(r, evidence(r), scenario='TIMEOUT_AFTER_SUBMIT')
                            if duplicate: self.assertEqual(m.intake(b'good'), 'RECEIPT_ONLY')
                            before = m.dump()
                            owned = copy.deepcopy((m.actions, m.events, m.denials, m.restored))
                            with self.assertRaises(ValueError):
                                m.intake(b'bad', now=value if field=='now' else 100)
                            self.assertEqual(m.dump(), before)
                            self.assertEqual((m.actions,m.events,m.denials,m.restored), owned)

    def test_valid_domain_edges_and_conservative_intake_without_consent(self):
        maximum = int((datetime.max.replace(tzinfo=timezone.utc, microsecond=0)-UTC_ORIGIN).total_seconds())
        for now in (0, maximum):
            simulation_time(now)
            with self.assertRaises(ValueError): simulation_time(maximum+1)
            for kind in ('suppression','revocation','delete','reply','status','reconcile'):
                with self.subTest(now=now,kind=kind):
                    r=req()
                    m=Mock(CONFIG,verifier=SyntheticVerifier({b'p':proof(r,kind=kind,outcome='UNKNOWN',at=now)}))
                    m.simulate(r,evidence(r),scenario='TIMEOUT_AFTER_SUBMIT')
                    self.assertEqual(m.intake(b'p',now=now),'RECEIPT_ONLY')
                    self.assertEqual(m.intake(b'p',now=now),'DUPLICATE_NO_EFFECT')
                    self.assertEqual(bool(m.denials),kind in ('suppression','revocation','delete'))
                    self.assertEqual(m.actions[r['action_key']]['receipt']['status'],'UNKNOWN')
                    self.assertEqual(m.outbound_state,'HOLD')
                    if m.denials:
                        new=req(event='synthetic-new')
                        with self.assertRaises(ValueError): m.simulate(new,evidence(new))

if __name__ == '__main__': unittest.main()
