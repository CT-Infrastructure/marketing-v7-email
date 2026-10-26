import unittest
import sys
import json
import copy
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mock import Mock,SyntheticVerifier,config
from dependencies import f05,f16,ROOT
from conformance import key,validate
CONFIG={'schema_version':'1.0.0','outbound_state':'HOLD','mode':'synthetic-only'}
def req(op='transport.submit',event='synthetic-event'):
    identity=dict(client_id='synthetic-client',source_system='synthetic-mautic',source_event_id=event,action_scope=op,approved_revision='synthetic-revision')
    return dict(tenant='synthetic-client',account='synthetic-account',destination='synthetic-subject',identity=identity,action_key=key(identity),payload_ref='synthetic-payload',operation=op)
def evidence(r):
    f=json.loads((ROOT/'source-exports/F16/contracts/privacy/synthetic-fixture.json').read_text())
    bindings={k:f[k] for k in f16.BINDINGS if k!='channel'}; bindings['channel']='email'
    q=f16.Request(**bindings,subject_ref=f['subject_ref'],now=f['now'],max_age_seconds=60)
    p=f16.Permission(**bindings,subject_ref=f['subject_ref'],source_authority='Mautic',granted=True,revoked=False,authority_available=True,valid_from=f['valid_from'],expires_at=f['expires_at'],observed_at=f['observed_at'],evidence_ref='synthetic-permission')
    life=f16.Lifecycle(client_ref=f['client_ref'],subject_ref=f['subject_ref'],deleted=False,suppressed=False,authority_available=True,observed_at=f['observed_at'],retention_until=f['retention_until'],authority_generation=1,applied_generation=1,restore_epoch=None,replay_complete=False,replay_evidence_ref=None,evidence_ref='synthetic-life')
    reviews=tuple(f16.Review(**bindings,kind=k,status='APPROVED',revoked=False,reviewer_role=v,observed_at=f['observed_at'],expires_at=f['expires_at'],evidence_ref='synthetic-review') for k,v in f16.REVIEW_ROLES.items())
    approval={k:r[k] for k in ('tenant','account','destination','action_key','operation')};approval.update(approved=True,revoked=False,observed=90,expires=150)
    return dict(approval=approval,privacy_request=q,permission=p,lifecycle=life,reviews=reviews,operator_scope=r['operation'],provider_review=True)
def proof(r,**kw):
    p=dict(account=r['account'],action_key=r['action_key'],object='synthetic-object',event='synthetic-callback',at=90,kind='reconcile',outcome='OCCURRED',tenant=r['tenant'],destination=r['destination']);p.update(kw);return p
class Tests(unittest.TestCase):
    def mock(self,fixtures=None): return Mock(CONFIG,verifier=SyntheticVerifier(fixtures or {}))
    def test_success_and_dedupe(self):
        r=req();m=self.mock();first=m.simulate(r,evidence(r));self.assertEqual(first['outbound_state'],'HOLD');self.assertEqual(first,m.simulate(r,{}));self.assertEqual(len(m.actions),1)
        changed=copy.deepcopy(r);changed['payload_ref']='synthetic-other'
        with self.assertRaises(ValueError):m.simulate(changed,evidence(changed))
    def test_permission_negatives(self):
        r=req();base=evidence(r)
        changes=[None,replace(base['permission'],granted=False),replace(base['permission'],granted='true'),replace(base['permission'],revoked=True),replace(base['permission'],channel='sms'),replace(base['permission'],expires_at='2026-10-25T12:00:00Z'),replace(base['permission'],observed_at='2026-10-24T12:00:00Z'),replace(base['permission'],account_ref='synthetic-other'),replace(base['permission'],authority_available=False)]
        for p in changes:
            with self.subTest(p=p):
                e=evidence(r);e['permission']=p;m=self.mock()
                with self.assertRaises(ValueError):m.simulate(r,e)
                self.assertEqual(m.actions,{})
    def test_lifecycle_and_reviews(self):
        r=req()
        for change in ({'deleted':True},{'suppressed':True},{'applied_generation':0},{'replay_complete':'true'},{'restore_epoch':'synthetic-restore'}):
            e=evidence(r);e['lifecycle']=replace(e['lifecycle'],**change)
            with self.assertRaises(ValueError): self.mock().simulate(r,e)
        for reviews in ((),None,('invalid',)):
            e=evidence(r);e['reviews']=reviews
            with self.assertRaises(ValueError):self.mock().simulate(r,e)
    def test_approval_negatives(self):
        r=req()
        for field,value in [('approved',False),('approved','true'),('revoked',True),('observed',0),('observed',101),('expires',100),('account','synthetic-other'),('action_key','synthetic-other'),('destination','synthetic-other'),('tenant','synthetic-other'),('operation','cp146.dns.change')]:
            e=evidence(r);e['approval'][field]=value
            with self.assertRaises(ValueError):self.mock().simulate(r,e)
        e=evidence(r);e.pop('approval')
        with self.assertRaises(ValueError):self.mock().simulate(r,e)
    def test_identity_and_payload_denials_redacted(self):
        r=req()
        for field,value in [('account',''),('tenant','synthetic-other'),('destination','https://secret.invalid'),('payload_ref','../../secret'),('payload_ref','SYNTHETIC_SECRET_VALUE'),('action_key','sha256:'+'0'*64),('operation','unknown')]:
            bad=copy.deepcopy(r);bad[field]=value
            with self.assertRaises(ValueError) as caught:self.mock().simulate(bad,evidence(r))
            self.assertNotIn('SYNTHETIC_SECRET_VALUE',str(caught.exception))
        for field in r:
            bad=copy.deepcopy(r);del bad[field]
            with self.assertRaises(ValueError):self.mock().simulate(bad,evidence(r))
    def test_errors_and_unknown_reservation(self):
        r=req()
        for code in f05.ERRORS:
            m=self.mock();out=m.simulate(r,evidence(r),scenario=code)
            expected=f05.error_decision(code,submitted=code in {'TIMEOUT_AFTER_SUBMIT','AMBIGUOUS_RESPONSE'})
            self.assertEqual(out['status'],expected);self.assertTrue(out['reservation_retained']);self.assertEqual(out,m.simulate(r,evidence(r)))
        self.assertEqual(f05.error_decision('NOT_FOUND',submitted=True),'UNKNOWN')
    def test_reconciliation(self):
        r=req()
        for outcome in ('OCCURRED','NOT_OCCURRED','UNKNOWN'):
            m=self.mock({b'proof':proof(r,outcome=outcome)});m.simulate(r,evidence(r),scenario='TIMEOUT_AFTER_SUBMIT');m.intake(b'proof')
            out=m.simulate(r,{})
            self.assertEqual(out['status'],'UNKNOWN' if outcome=='UNKNOWN' else 'RECONCILED')
            self.assertEqual(out['reservation_retained'],outcome!='NOT_OCCURRED');self.assertEqual(len(m.actions),1)
    def test_bad_callbacks(self):
        r=req()
        for changes in ({'account':'synthetic-other'},{'at':0},{'at':101},{'at':True},{'action_key':'synthetic-wrong'},{'destination':'synthetic-other'},{'tenant':'synthetic-other'},{'kind':'unknown'},{'verified':True}):
            m=self.mock({b'bad':proof(r,**changes)});m.simulate(r,evidence(r),scenario='AMBIGUOUS_RESPONSE');before=m.dump()
            with self.assertRaises(ValueError):m.intake(b'bad')
            self.assertEqual(before,m.dump())
        m=self.mock({b'original':proof(r)});m.simulate(r,evidence(r),scenario='AMBIGUOUS_RESPONSE')
        for raw in (b'tampered',b'{"verified":true}',b'', 'original'):
            with self.assertRaises(ValueError):m.intake(raw)
    def test_intake_suppression_without_consent_and_replay(self):
        r=req();m=self.mock({b'suppress':proof(r,kind='suppression',outcome='UNKNOWN')});m.simulate(r,evidence(r),scenario='TIMEOUT_AFTER_SUBMIT')
        self.assertEqual(m.intake(b'suppress'),'RECEIPT_ONLY');self.assertEqual(m.intake(b'suppress'),'DUPLICATE_NO_EFFECT')
        new=req(event='synthetic-new')
        with self.assertRaises(ValueError):m.simulate(new,evidence(new))
        restored=Mock.restore(m.dump(),CONFIG,verifier=m.verifier)
        self.assertEqual(restored.simulate(r,{})['status'],'UNKNOWN')
        e=evidence(new);e['restore_replay']={'epoch':'synthetic-restore','completed':True,'evidence_ref':'synthetic-replay'}
        with self.assertRaises(ValueError):restored.simulate(new,e)
    def test_operations_have_distinct_authority(self):
        for op in ('cp146.dns.change','cp146.mailbox.admin','cp146.mailbox.reply','receipt.read','transport.cancel'):
            r=req(op);e=evidence(r);e['permission']=None
            self.assertEqual(self.mock().simulate(r,e)['outbound_state'],'HOLD')
            for field,value in [('operator_scope','transport.submit'),('provider_review',False),('provider_review','true')]:
                bad=copy.deepcopy(e);bad[field]=value
                with self.assertRaises(ValueError):self.mock().simulate(r,bad)
    def test_restore_holds_and_corruption(self):
        r=req();m=self.mock();m.simulate(r,evidence(r));restored=Mock.restore(m.dump(),CONFIG,verifier=m.verifier);new=req(event='synthetic-new');e=evidence(new)
        with self.assertRaises(ValueError):restored.simulate(new,e)
        e['restore_replay']={'epoch':'synthetic-restore','completed':True,'evidence_ref':'synthetic-replay'}
        e['lifecycle']=replace(e['lifecycle'],restore_epoch='synthetic-restore',replay_complete=True,replay_evidence_ref='synthetic-replay')
        e['replay_receipt']=f16.ReplayReceipt(client_ref='synthetic-client',subject_ref='synthetic-subject',restore_epoch='synthetic-restore',generation=1,completed=True,authority_available=True,observed_at='2026-10-25T11:59:30Z',evidence_ref='synthetic-replay')
        self.assertEqual(restored.simulate(new,e)['outbound_state'],'HOLD')
        for value in ('{','[]',m.dump().replace('1.0.0','9.9.9'),m.dump().replace('synthetic-payload','../../secret'),m.dump().replace('"reservation_retained":true','"reservation_retained":"true"')):
            with self.assertRaises(ValueError):Mock.restore(value,CONFIG,verifier=m.verifier)
    def test_revocation_delete_reapply_and_object_binding(self):
        for kind in ('revocation','delete'):
            r=req();m=self.mock({b'notice':proof(r,kind=kind,outcome='UNKNOWN')});m.simulate(r,evidence(r),scenario='AMBIGUOUS_RESPONSE');m.intake(b'notice')
            restored=Mock.restore(m.dump(),CONFIG,verifier=m.verifier)
            self.assertIn(('synthetic-client','synthetic-subject'),restored.denials)
            self.assertEqual(restored.intake(b'notice'),'DUPLICATE_NO_EFFECT')
            new=req(event='synthetic-new')
            with self.assertRaises(ValueError):restored.simulate(new,evidence(new))
        r=req();m=self.mock({b'one':proof(r),b'two':proof(r,event='synthetic-other',object='synthetic-other')});m.simulate(r,evidence(r),scenario='TIMEOUT_AFTER_SUBMIT');m.intake(b'one')
        self.assertEqual(m.intake(b'one'),'DUPLICATE_NO_EFFECT')
        with self.assertRaises(ValueError):m.intake(b'two')
    def test_config_denials(self):
        for field in ('endpoint','command','url','credentials','secret','enable','path'):
            bad=dict(CONFIG);bad[field]='SYNTHETIC_SECRET_VALUE'
            with self.assertRaises(ValueError) as c:config(bad)
            self.assertNotIn('SYNTHETIC_SECRET_VALUE',str(c.exception))
        for value in ('LIVE','CONFIRMED',True):
            bad=dict(CONFIG);bad['outbound_state']=value
            with self.assertRaises(ValueError):config(bad)
    def test_f04_supplied_fixtures_and_mutations(self):
        for kind in ('event-envelope','action-receipt'):
            fixture=json.loads((ROOT/('source-exports/F04/contracts/core/fixtures/'+kind+'.json')).read_text());validate(kind,fixture)
            for field in fixture:
                bad=copy.deepcopy(fixture);del bad[field]
                with self.assertRaises(ValueError):validate(kind,bad)
            bad=dict(fixture);bad['unexpected']=True
            with self.assertRaises(ValueError):validate(kind,bad)
        r=req();m=self.mock();out=m.simulate(r,evidence(r),scenario='TIMEOUT_AFTER_SUBMIT');out['reservation_retained']=False
        with self.assertRaises(ValueError):validate('action-receipt',out)
    def test_no_network_or_process_imports(self):
        import ast
        banned={'socket','smtplib','urllib','http','requests','subprocess','os'}
        for name in ('mock.py','conformance.py','dependencies.py'):
            tree=ast.parse((Path(__file__).resolve().parents[1]/name).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):self.assertFalse({a.name.split('.')[0] for a in node.names}&banned)
                if isinstance(node,ast.ImportFrom):self.assertNotIn((node.module or '').split('.')[0],banned)
if __name__=='__main__':unittest.main()
