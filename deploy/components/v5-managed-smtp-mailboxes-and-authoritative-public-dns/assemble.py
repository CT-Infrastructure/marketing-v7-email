"""Pinned public blob assembly. Importing this module performs no transport."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

COMPONENT = Path(__file__).resolve().parent
LOCK = COMPONENT / 'dependencies.lock.json'

def safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError('unsafe path')
    parts = value.split('/')
    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+', p) or p in ('.', '..') or p.endswith('.') or p.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))} for p in parts):
        raise ValueError('unsafe path')
    return parts

def checked_entries(entries):
    seen = set()
    prefixes = {}
    for e in entries:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', e['repository']):
            raise ValueError('repository')
        if not re.fullmatch('[a-f0-9]{40}', e['revision']) or not re.fullmatch('[a-f0-9]{64}', e['sha256']):
            raise ValueError('pin')
        safe_path(e['source_path'])
        parts = safe_path(e['destination'])
        folded = e['destination'].casefold()
        if folded in seen:
            raise ValueError('duplicate destination')
        seen.add(folded)
        for i in range(1, len(parts)+1):
            prefix = '/'.join(parts[:i])
            old = prefixes.setdefault(prefix.casefold(), prefix)
            if old != prefix:
                raise ValueError('case alias')
    if any(a != b and b.startswith(a + '/') for a in seen for b in seen):
        raise ValueError('file directory conflict')
    return entries

def cache_path(entries, component=COMPONENT):
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return component / '.assembled' / digest

def no_links(path):
    for p in (path, *path.parents):
        if p.is_symlink() or p.is_junction():
            raise ValueError('linked destination')

def verify(entries, target):
    no_links(target)
    expected = {e['destination'] for e in entries}
    if not target.is_dir():
        raise ValueError('missing assembled dependencies; run assemble.py')
    actual = set()
    for p in target.rglob('*'):
        no_links(p)
        if p.is_file():
            if p.stat().st_nlink != 1:
                raise ValueError('hard link')
            actual.add(p.relative_to(target).as_posix())
    if actual != expected:
        raise ValueError('cache inventory mismatch')
    for e in entries:
        if hashlib.sha256((target / e['destination']).read_bytes()).hexdigest() != e['sha256']:
            raise ValueError('cache hash mismatch')
    return target

def assemble(entries, reader, component=COMPONENT):
    """reader(repository, revision, source_path) -> (actual_revision, bytes).

    Caller authenticates transport; returned commit and every byte hash are checked.
    Only a fully validated new generation is published. No old cache is replaced.
    Concurrent identical publication validates the winning generation.
    """
    checked_entries(entries)
    component = Path(component)
    target = cache_path(entries, component)
    no_links(target)
    if target.exists():
        return verify(entries, target)
    target.parent.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='stage-', dir=target.parent))
    try:
        for e in entries:
            revision, data = reader(e['repository'], e['revision'], e['source_path'])
            if revision != e['revision'] or type(data) is not bytes or hashlib.sha256(data).hexdigest() != e['sha256']:
                raise ValueError('input commit or hash mismatch')
            dest = stage / e['destination']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        verify(entries, stage)
        try:
            os.rename(stage, target)
        except OSError:
            if not target.exists():
                raise
            verify(entries, target)
        return target
    finally:
        if stage.exists():
            shutil.rmtree(stage)

def git_reader(checkout):
    """Root-executed adapter for a public Git checkout; never invoked at import."""
    import subprocess
    checkout = Path(checkout).resolve()
    def read(repository, revision, source_path):
        if repository != 'CT-Infrastructure/marketing-v7-control':
            raise ValueError('unapproved repository')
        def git(*args):
            return subprocess.run(['git', '-C', str(checkout), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        remote = git('remote', 'get-url', 'origin').decode().strip()
        if remote not in ('https://github.com/' + repository + '.git', 'https://github.com/' + repository):
            raise ValueError('wrong repository origin')
        actual = git('rev-parse', '--verify', revision + '^{commit}').decode().strip()
        mode = git('ls-tree', revision, '--', source_path).decode().split(' ', 1)[0]
        if mode not in ('100644', '100755'):
            raise ValueError('not a regular Git blob')
        return actual, git('cat-file', 'blob', revision + ':' + source_path)
    return read

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', required=True, help='public marketing-v7-control Git checkout')
    args = parser.parse_args()
    print(assemble(json.loads(LOCK.read_text(encoding='utf-8')), git_reader(args.checkout)))
