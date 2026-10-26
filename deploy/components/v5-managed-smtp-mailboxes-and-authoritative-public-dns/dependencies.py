"""Load hash-verified accepted dependencies from the component-local cache."""
import importlib.util
from pathlib import Path
import sys
from assemble import LOCK, cache_path, checked_entries, verify
import json
_entries = checked_entries(json.loads(LOCK.read_text(encoding='utf-8')))
ROOT = verify(_entries, cache_path(_entries))
def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
f05 = load('cp146_f05', 'source-exports/F05/contracts/adapters/contract.py')
f16 = load('cp146_f16', 'source-exports/F16/contracts/privacy/eligibility.py')
