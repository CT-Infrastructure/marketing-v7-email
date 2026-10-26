
import copy
import ast
import json
import unittest
from dataclasses import replace
from test_mock import req, evidence, proof, CONFIG
from mock import Mock, SyntheticVerifier, simulation_time
from conformance import validate
from dependencies import ROOT

class Corrections(unittest.TestCase):
    def make(self, fixtures=None):
        return Mock(CONFIG, verifier=SyntheticVerifier(fixtures or {}))

    def test_common_clock_expiry_and_frozen_request(self):
        r=req(); e=evidence(r)
        self.assertEqual(simulation_time(100),e['privacy_request'].now)
        e['approval'].update(observed=9990,expires=10050)
        with self.assertRaises(ValueError): self.make().simulate(r,e,now=10000)
        # Refresh observation snapshots but retain expired permission.
        e['permission']=replace(e['permission'],observed_at=simulation_time(10000))
        e['lifecycle']=replace(e['lifecycle'],observed_at=simulation_time(10000))
        e['reviews']=tuple(replace(x,observed_at=simulation_time(10000),expires_at=simulation_time(11000)) for x in e['reviews'])
        with self.assertRaises(ValueError): self.make().simulate(r,e,now=10000)

    def test_caller_clock_cannot_create_future_or_stale_decision(self):
        r=req(); e=evidence(r)
        e['privacy_request']=replace(e['privacy_request'],now='1900-01-01T00:00:00Z')
        self.assertEqual(self.make().simulate(r,e)['status'],'HELD')
        for now in (True,-1,'100'):
            with self.assertRaises(ValueError): self.make().simulate(r,e,now=now)

    def test_receipts_append_and_reference_transition(self):
        r=req(); m=self.make({b'p':proof(r)})
        before=m.simulate(r,evidence(r),scenario='TIMEOUT_AFTER_SUBMIT')
        m.intake(b'p',now=110)
        after=m.simulate(r,{})
        history=json.loads(m.dump())['actions'][r['action_key']]['history']
        self.assertEqual(history,[before,after])
        self.assertNotEqual(before['receipt_id'],after['receipt_id'])
        # Execute the exact accepted pure transition function with local schema
        # validation: the full accepted validator requires unavailable jsonschema.
        tree=ast.parse((ROOT/'source-exports/F04/contracts/core/validate.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_transition')
        from dependencies import f16
        namespace={'validate':validate,'instant':f16.instant}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'accepted-check-transition','exec'),namespace)
        self.assertTrue(namespace['check_transition'](before,after))
        with self.assertRaises(ValueError): namespace['check_transition'](before,before)
        self.assertEqual(Mock.restore(m.dump(),CONFIG,verifier=m.verifier).simulate(r,{}),after)
        other=req(event='synthetic-other')
        self.assertNotEqual(before['receipt_id'],self.make().simulate(other,evidence(other))['receipt_id'])
        before['status']='HELD'
        self.assertEqual(json.loads(m.dump())['actions'][r['action_key']]['history'][0]['status'],'UNKNOWN')

    def test_restore_rejects_semantic_corruption(self):
        r=req(); m=self.make(); m.simulate(r,evidence(r),scenario='TIMEOUT_AFTER_SUBMIT')
        for mutation in ('latest','both','disposition','outcome'):
            d=json.loads(m.dump()); a=d['actions'][r['action_key']]
            if mutation=='latest': a['receipt']['status']='HELD'
            if mutation=='both':
                a['receipt']['status']='HELD'; a['history'][0]['status']='HELD'
            if mutation=='disposition': a['disposition']='SIMULATED_ONLY'
            if mutation=='outcome': a['history'][0]['reconciliation_outcome']='OCCURRED'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                Mock.restore(json.dumps(d),CONFIG,verifier=m.verifier)

    def test_restore_rejects_invalid_history_transition(self):
        r=req(); m=self.make({b'p':proof(r)}); m.simulate(r,evidence(r),scenario='AMBIGUOUS_RESPONSE'); m.intake(b'p')
        for field,value in [('recorded_at','2026-10-25T11:59:59.9Z'),('receipt_id','synthetic-reused'),('attempt',2),('status','UNKNOWN')]:
            d=json.loads(m.dump()); a=d['actions'][r['action_key']]
            a['history'][-1][field]=value; a['receipt']=copy.deepcopy(a['history'][-1])
            with self.subTest(field=field), self.assertRaises(ValueError):
                Mock.restore(json.dumps(d),CONFIG,verifier=m.verifier)

    def test_callback_before_initial_receipt_is_atomic_denial(self):
        r=req(); m=self.make({b'p':proof(r)}); m.simulate(r,evidence(r),scenario='AMBIGUOUS_RESPONSE')
        before=m.dump()
        with self.assertRaises(ValueError): m.intake(b'p',now=99)
        self.assertEqual(before,m.dump())

    def test_mixed_fractional_chronology_both_directions(self):
        f=json.loads((ROOT/'source-exports/F04/contracts/core/fixtures/event-envelope.json').read_text())
        f.update(occurred_at='2026-10-25T12:00:00.1Z',received_at='2026-10-25T12:00:00Z')
        with self.assertRaises(ValueError): validate('event-envelope',f)
        f.update(occurred_at='2026-10-25T12:00:00Z',received_at='2026-10-25T12:00:00.1Z')
        validate('event-envelope',f)
        f.update(occurred_at='2026-10-25T12:00:00.10Z',received_at='2026-10-25T12:00:00.1Z')
        validate('event-envelope',f)

    def test_reviewed_freshness_policy_not_local_legal_limit(self):
        r=req(); e=evidence(r)
        e['privacy_request']=replace(e['privacy_request'],max_age_seconds=999999999)
        e['permission']=replace(e['permission'],observed_at='2026-10-24T12:00:00Z')
        self.assertEqual(self.make().simulate(r,e)['status'],'HELD')


    def capacity_session(self):
        # Exercise the actual restore bound, retaining distinct historical state.
        requests=[]; m=self.make()
        for i in range(1000):
            r=req('cp146.dns.change',event='synthetic-capacity-'+str(i))
            r['destination']='synthetic-subject-'+str(i)
            scenario='TIMEOUT_AFTER_SUBMIT' if i in (0,1) else 'success'
            m.simulate(r,evidence(r),scenario=scenario); requests.append(r)
        m.verifier=SyntheticVerifier({
            b'reconcile':proof(requests[1],event='synthetic-reconciled'),
            b'suppress':proof(requests[2],kind='suppression',event='synthetic-suppressed',outcome='UNKNOWN'),
            b'delete':proof(requests[3],kind='delete',event='synthetic-deleted',outcome='UNKNOWN')})
        for raw in (b'reconcile',b'suppress',b'delete'): m.intake(raw)
        return m,requests

    def test_capacity_roundtrip_replay_conflict_and_atomic_admission(self):
        m,requests=self.capacity_session(); before=m.dump()
        restored=Mock.restore(before,CONFIG,verifier=m.verifier)
        self.assertEqual(restored.dump(),before)
        self.assertEqual(len(restored.actions),1000)
        self.assertEqual(restored.actions[requests[0]['action_key']]['receipt']['status'],'UNKNOWN')
        self.assertTrue(restored.actions[requests[0]['action_key']]['receipt']['reservation_retained'])
        self.assertEqual(len(restored.actions[requests[1]['action_key']]['history']),2)
        self.assertEqual(restored.denials,{(requests[i]['tenant'],requests[i]['destination']) for i in (2,3)})
        for session in (m,restored):
            for r in requests[:4]:
                self.assertEqual(session.simulate(r,{},scenario='invalid'),m.actions[r['action_key']]['receipt'])
                changed=copy.deepcopy(r); changed['payload_ref']='synthetic-changed'
                with self.assertRaises(ValueError): session.simulate(changed,{})
                self.assertEqual(session.dump(),before)
            for raw in (b'reconcile',b'suppress',b'delete'):
                self.assertEqual(session.intake(raw),'DUPLICATE_NO_EFFECT')
                self.assertEqual(session.dump(),before)
            for scenario in ('success','TIMEOUT_AFTER_SUBMIT','AMBIGUOUS_RESPONSE','invalid'):
                for denied in (False,True):
                    r=req('cp146.dns.change',event='synthetic-excess')
                    if denied: r['destination']=requests[2]['destination']
                    e=evidence(r)
                    e['restore_replay']={'epoch':'synthetic-restore','completed':True,'evidence_ref':'synthetic-replay'}
                    with self.subTest(restored=session.restored,scenario=scenario,denied=denied):
                        with self.assertRaises(ValueError): session.simulate(r,e,scenario=scenario)
                        self.assertEqual(session.dump(),before)
            malformed=req(); malformed['payload_ref']='../../invalid'
            with self.assertRaises(ValueError): session.simulate(malformed,{})
            self.assertEqual(session.dump(),before)

    def test_every_emitted_capacity_state_is_restorable(self):
        m=self.make()
        for i in range(1001):
            r=req('cp146.dns.change',event='synthetic-boundary-'+str(i))
            if i<1000:
                m.simulate(r,evidence(r))
            else:
                before=m.dump()
                # Old code emits 1001 actions here; restore below rejects its own dump.
                try: m.simulate(r,evidence(r))
                except ValueError: self.assertEqual(m.dump(),before)
        serialized=m.dump()
        self.assertEqual(Mock.restore(serialized,CONFIG,verifier=m.verifier).dump(),serialized)
        self.assertEqual(len(m.actions),1000)
