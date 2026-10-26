"""CP146 1.0.0: deterministic synthetic events only. No transport or enable switch."""
import copy
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from dependencies import f05, f16
from conformance import key, validate
UTC_ORIGIN = datetime(2026, 10, 25, 11, 58, 20, tzinfo=timezone.utc)

def simulation_time(now):
    require(type(now) is int and now >= 0)
    try: return (UTC_ORIGIN + timedelta(seconds=now)).isoformat().replace('+00:00', 'Z')
    except OverflowError: raise ValueError('CP146 invalid simulation time') from None

def receipt_id(k, sequence):
    return 'synthetic-' + hashlib.sha256((k + ':' + str(sequence)).encode()).hexdigest()

OPS={'transport.submit','receipt.read','transport.cancel','cp146.mailbox.admin','cp146.mailbox.reply','cp146.dns.change'}
REF=re.compile(r'synthetic-[a-z0-9-]{1,100}\Z')
def require(ok):
    if not ok: raise ValueError('CP146 invalid or untrusted evidence')
def ref(x): return type(x) is str and REF.fullmatch(x) is not None
def config(value):
    require(type(value) is dict and value=={'schema_version':'1.0.0','outbound_state':'HOLD','mode':'synthetic-only'})
    return copy.deepcopy(value)
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def request(r):
    require(type(r) is dict and set(r)=={'tenant','account','destination','identity','action_key','payload_ref','operation'})
    require(all(ref(r[k]) for k in ('tenant','account','destination','payload_ref')))
    require(r['operation'] in OPS and type(r['identity']) is dict)
    require(r['identity'].get('client_id')==r['tenant'] and r['identity'].get('action_scope')==r['operation'])
    require(all(ref(v) or v in OPS for v in r['identity'].values()))
    require(r['action_key']==key(r['identity']))
    if not r['operation'].startswith('cp146.'):
        f05.validate_request(dict(schema_version='1.0',adapter='providers',action=r['operation'],account_ref=r['account'],action_key=r['action_key'],expected_revision=r['identity']['approved_revision'],payload_ref=r['payload_ref'],outbound_state='HOLD'))
    return r
class SyntheticVerifier:
    """Exact original-byte fixture allowlist. No vendor cryptography or production trust."""
    def __init__(self, fixtures): self._fixtures=copy.deepcopy(fixtures)
    def verify(self, raw):
        require(type(raw) is bytes and raw in self._fixtures)
        return copy.deepcopy(self._fixtures[raw])
class Mock:
    outbound_state='HOLD'
    def __init__(self, settings, *, verifier):
        config(settings); require(type(verifier) is SyntheticVerifier)
        self.verifier=verifier; self.actions={}; self.events=set(); self.denials=set(); self.restored=False
    def eligible(self,r,e,now):
        require(type(e) is dict and type(now) is int)
        approval=e.get('approval')
        binding={k:r[k] for k in ('tenant','account','destination','action_key','operation')}
        require(type(approval) is dict and set(approval)==set(binding)|{'approved','revoked','observed','expires'})
        require(all(approval[k]==v for k,v in binding.items()))
        require(approval['approved'] is True and approval['revoked'] is False)
        require(type(approval['observed']) is int and type(approval['expires']) is int and 0<=now-approval['observed']<=60 and now<approval['expires'])
        require((r['tenant'],r['destination']) not in self.denials)
        if self.restored:
            require(e.get('restore_replay')=={'epoch':'synthetic-restore','completed':True,'evidence_ref':'synthetic-replay'} and type(e['restore_replay']['completed']) is bool)
            if r['operation']=='transport.submit':
                require(type(e.get('lifecycle')) is f16.Lifecycle and e['lifecycle'].restore_epoch=='synthetic-restore' and type(e.get('replay_receipt')) is f16.ReplayReceipt)
        if r['operation']=='transport.submit':
            q=e.get('privacy_request'); require(type(q) is f16.Request and q.channel=='email' and q.client_ref==r['tenant'] and q.account_ref==r['account'] and q.subject_ref==r['destination'])
            q=replace(q, now=simulation_time(now))
            decision=f16.evaluate(q,e.get('permission'),e.get('lifecycle'),e.get('reviews',()),replay_receipt=e.get('replay_receipt'))
            require(decision.status=='ELIGIBLE_OFFLINE')
        else:
            require(e.get('operator_scope')==r['operation'] and e.get('provider_review') is True)
    def simulate(self,r,e,*,now=100,scenario='success'):
        request(r); k=r['action_key']; fingerprint=hashlib.sha256(canonical(r).encode()).hexdigest()
        if k in self.actions:
            require(self.actions[k]['fingerprint']==fingerprint)
            return copy.deepcopy(self.actions[k]['receipt'])
        self.eligible(r,e,now)
        require(scenario=='success' or scenario in f05.ERRORS)
        status='HELD' if scenario=='success' else f05.error_decision(scenario,submitted=scenario in {'TIMEOUT_AFTER_SUBMIT','AMBIGUOUS_RESPONSE'})
        receipt=dict(schema_version='1.0',receipt_id=receipt_id(k, 0),action_identity=copy.deepcopy(r['identity']),action_key=k,event_id=r['identity']['source_event_id'],correlation_id='synthetic-correlation',approval_ref='synthetic-approval',destination=r['destination'],attempt=1,recorded_at=simulation_time(now),status=status,provider_object_ref=None,evidence_ref='synthetic-evidence',reconciliation_ref=None,outbound_state='HOLD',reservation_retained=True,reconciliation_outcome=None)
        validate('action-receipt',receipt)
        self.actions[k]={'request':copy.deepcopy(r),'fingerprint':fingerprint,'receipt':receipt,'history':[copy.deepcopy(receipt)],'disposition':'SIMULATED_ONLY' if scenario=='success' else scenario}
        return copy.deepcopy(receipt)
    def intake(self,raw,*,now=100):
        simulation_time(now)
        p=self.verifier.verify(raw)
        require(type(p) is dict and set(p)=={'account','action_key','object','event','at','kind','outcome','tenant','destination'})
        simulation_time(p['at'])
        require(all(ref(p[x]) for x in ('account','object','event','tenant','destination')) and 0<=now-p['at']<=60)
        require(p['action_key'] in self.actions)
        a=self.actions[p['action_key']]; r=a['request']
        require(all(p[k]==r[k] for k in ('account','tenant','destination')))
        receipt=a['receipt']; require(receipt['provider_object_ref'] in (None,p['object']))
        require(p['kind'] in {'suppression','revocation','delete','reply','status','reconcile'})
        require(p['outcome'] in {'UNKNOWN','OCCURRED','NOT_OCCURRED'})
        event=(p['account'],p['event'])
        if event in self.events: return 'DUPLICATE_NO_EFFECT'
        if p['kind']=='reconcile':
            require(receipt['status']=='UNKNOWN')
            if p['outcome']!='UNKNOWN':
                receipt=copy.deepcopy(receipt)
                receipt.update(receipt_id=receipt_id(r['action_key'],len(a['history'])),recorded_at=simulation_time(now),status='RECONCILED',reconciliation_ref='synthetic-proof',reconciliation_outcome=p['outcome'],provider_object_ref=p['object'] if p['outcome']=='OCCURRED' else None,reservation_retained=p['outcome']=='OCCURRED',outbound_state='CONFIRMED' if p['outcome']=='OCCURRED' else 'HOLD')
                validate('action-receipt',receipt)
                transition(a['receipt'],receipt)
                a['history'].append(copy.deepcopy(receipt)); a['receipt']=receipt
        if p['kind'] in {'suppression','revocation','delete'}: self.denials.add((p['tenant'],p['destination']))
        self.events.add(event)
        return 'RECEIPT_ONLY'
    def dump(self):
        return canonical({'version':'1.0.0','actions':self.actions,'events':[list(x) for x in sorted(self.events)],'denials':[list(x) for x in sorted(self.denials)]})
    @classmethod
    def restore(cls,serialized,settings,*,verifier):
        try:
            data=json.loads(serialized); require(type(data) is dict and set(data)=={'version','actions','events','denials'} and data['version']=='1.0.0')
            require(type(data['actions']) is dict and len(data['actions'])<=1000)
            for k,a in data['actions'].items():
                require(set(a)=={'request','fingerprint','receipt','history','disposition'}); request(a['request'])
                require(k==a['request']['action_key'] and a['fingerprint']==hashlib.sha256(canonical(a['request']).encode()).hexdigest())
                validate('action-receipt',a['receipt']); require(a['receipt']['action_key']==k and a['receipt']['destination']==a['request']['destination'] and a['receipt']['action_identity']==a['request']['identity'])
                require(a['disposition']=='SIMULATED_ONLY' or a['disposition'] in f05.ERRORS)
                history=a['history']
                require(type(history) is list and 1<=len(history)<=2 and history[-1]==a['receipt'])
                expected='HELD' if a['disposition']=='SIMULATED_ONLY' else f05.error_decision(a['disposition'],submitted=a['disposition'] in {'TIMEOUT_AFTER_SUBMIT','AMBIGUOUS_RESPONSE'})
                require(history[0]['status']==expected)
                for i,h in enumerate(history):
                    validate('action-receipt',h)
                    require(h['receipt_id']==receipt_id(k,i) and h['action_key']==k and h['action_identity']==a['request']['identity'] and h['destination']==a['request']['destination'])
                    require(h['evidence_ref']=='synthetic-evidence' and h['approval_ref']=='synthetic-approval' and h['correlation_id']=='synthetic-correlation' and h['attempt']==1)
                    if i==0:
                        require(h['provider_object_ref'] is None and h['reconciliation_ref'] is None and h['reconciliation_outcome'] is None and h['reservation_retained'] is True and h['outbound_state']=='HOLD')
                    else:
                        transition(history[i-1],h)
                        require(h['reconciliation_ref']=='synthetic-proof' and (h['provider_object_ref'] is None or ref(h['provider_object_ref'])))
            for field in ('events','denials'):
                require(type(data[field]) is list and all(type(x) is list and len(x)==2 and all(ref(v) for v in x) for x in data[field]))
            obj=cls(settings,verifier=verifier); obj.actions=data['actions'];obj.events={tuple(x) for x in data['events']}; obj.denials={tuple(x) for x in data['denials']};obj.restored=True
            return obj
        except (ValueError,TypeError,KeyError,AttributeError): raise ValueError('CP146 corrupt restore held') from None

def transition(previous,current):
    validate('action-receipt',previous); validate('action-receipt',current)
    require(all(previous[k]==current[k] for k in ('action_key','action_identity','event_id','correlation_id','destination','approval_ref','attempt')))
    require(previous['status']=='UNKNOWN' and current['status']=='RECONCILED')
    require(previous['receipt_id']!=current['receipt_id'] and f16.instant(current['recorded_at'])>=f16.instant(previous['recorded_at']))
    require(previous['provider_object_ref'] is None or previous['provider_object_ref']==current['provider_object_ref'])
