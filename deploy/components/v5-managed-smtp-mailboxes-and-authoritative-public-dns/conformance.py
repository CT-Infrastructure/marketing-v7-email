"""Bounded interpreter for keywords present in supplied F04 schemas, not general JSON Schema."""
import json
import re
import hashlib
from datetime import datetime
from dependencies import ROOT
SCHEMAS = {s['$id']:s for p in (ROOT/'source-exports/F04/schemas/runtime').glob('*.json') for s in [json.loads(p.read_text())]}
def check(s, value):
    if '$ref' in s:
        uri, _, fragment = s['$ref'].partition('#')
        target = SCHEMAS[uri]
        for part in fragment.strip('/').split('/') if fragment else []:
            target = target[part]
        check(target, value)
    if 'type' in s:
        types={'object':dict,'array':list,'string':str,'integer':int,'boolean':bool,'null':type(None)}
        if type(value) is not types[s['type']]: raise ValueError('F04 type')
    if 'const' in s and (type(value) is not type(s['const']) or value != s['const']): raise ValueError('F04 constant')
    if 'enum' in s and not any(type(value) is type(x) and value == x for x in s['enum']): raise ValueError('F04 enum')
    if 'anyOf' in s:
        for branch in s['anyOf']:
            try: check(branch,value); break
            except ValueError: pass
        else: raise ValueError('F04 alternatives')
    if 'not' in s:
        try: check(s['not'],value)
        except ValueError: pass
        else: raise ValueError('F04 prohibited')
    if type(value) is dict:
        if not set(s.get('required',[])) <= value.keys(): raise ValueError('F04 required')
        if s.get('additionalProperties') is False and not value.keys() <= s.get('properties',{}).keys(): raise ValueError('F04 unknown')
        for k, schema in s.get('properties',{}).items():
            if k in value: check(schema,value[k])
    if type(value) is str:
        if len(value)<s.get('minLength',0) or len(value)>s.get('maxLength',10**9): raise ValueError('F04 length')
        if 'pattern' in s and re.search(s['pattern'],value) is None: raise ValueError('F04 pattern')
        if s.get('format')=='date-time':
            try: datetime.fromisoformat(value.replace('Z','+00:00'))
            except ValueError: raise ValueError('F04 time') from None
    if type(value) is int and value<s.get('minimum',value): raise ValueError('F04 minimum')
    for branch in s.get('allOf',[]): check(branch,value)
    if 'if' in s:
        try: check(s['if'],value)
        except ValueError: check(s.get('else',{}),value)
        else: check(s.get('then',{}),value)
def key(identity):
    check(SCHEMAS['urn:marketing-v7:runtime:common:1.0']['$defs']['action_identity'],identity)
    return 'sha256:'+hashlib.sha256(json.dumps([identity[k] for k in ('client_id','source_system','source_event_id','action_scope','approved_revision')],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def validate(kind,value):
    check(SCHEMAS['urn:marketing-v7:runtime:'+kind+':1.0'],value)
    if kind=='action-receipt' and (value['event_id']!=value['action_identity']['source_event_id'] or value['action_key']!=key(value['action_identity'])): raise ValueError('F04 identity')
    if kind=='event-envelope' and datetime.fromisoformat(value['received_at'].replace('Z','+00:00'))<datetime.fromisoformat(value['occurred_at'].replace('Z','+00:00')): raise ValueError('F04 chronology')
    return value
