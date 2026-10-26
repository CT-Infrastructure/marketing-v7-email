"""Synthetic transport tests; no Git/network/provider execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assemble import assemble, cache_path, checked_entries

class Assembly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.addCleanup(self.tmp.cleanup)
        self.component = Path(self.tmp.name)
        self.entries = [dict(repository='example/public', revision='a'*40, source_path='file.py', destination='source/file.py', sha256=hashlib.sha256(b'canonical').hexdigest())]
    def reader(self, repo, rev, path):
        return rev, b'canonical'
    def test_deterministic_idempotent(self):
        first = assemble(self.entries, self.reader, self.component)
        stamp = (first/'source/file.py').stat().st_mtime_ns
        second = assemble(self.entries, lambda *a: self.fail('transport repeated'), self.component)
        self.assertEqual(first, second)
        self.assertEqual(stamp, (second/'source/file.py').stat().st_mtime_ns)
    def test_missing(self):
        def missing(*args): raise FileNotFoundError('synthetic missing')
        with self.assertRaises(FileNotFoundError): assemble(self.entries, missing, self.component)
        self.assertFalse(cache_path(self.entries, self.component).exists())
    def test_hash_and_commit(self):
        for response in [('a'*40,b'corrupt'), ('b'*40,b'canonical')]:
            with self.assertRaises(ValueError): assemble(self.entries, lambda *a: response, self.component)
            self.assertFalse(cache_path(self.entries,self.component).exists())
    def test_paths(self):
        for path in ['../escape','/absolute','C:/drive','a\\b','a//b','a/./b','a/NUL','a/file.']:
            e=copy.deepcopy(self.entries);e[0]['destination']=path
            with self.assertRaises(ValueError): assemble(e,self.reader,self.component)
    def test_duplicate_alias_and_prefix(self):
        for path in ['source/file.py','SOURCE/other.py','source/file.py/child']:
            e=copy.deepcopy(self.entries);e.append(dict(e[0],destination=path))
            with self.assertRaises(ValueError): assemble(e,self.reader,self.component)
    def test_atomic_failure_keeps_previous(self):
        old=assemble(self.entries,self.reader,self.component)
        e=copy.deepcopy(self.entries);e.append(dict(e[0],source_path='missing',destination='second.py'))
        def fail(repo,rev,path):
            if path=='missing': raise OSError('synthetic interruption')
            return self.reader(repo,rev,path)
        with self.assertRaises(OSError): assemble(e,fail,self.component)
        self.assertEqual((old/'source/file.py').read_bytes(), b'canonical')
        self.assertFalse(cache_path(e,self.component).exists())
        self.assertFalse(list((self.component/'.assembled').glob('stage-*')))
    def test_corrupt_cache_fails_closed(self):
        target=assemble(self.entries,self.reader,self.component)
        (target/'source/file.py').write_bytes(b'corrupt')
        with self.assertRaises(ValueError): assemble(self.entries,self.reader,self.component)
    def test_link_rejected(self):
        # Sandbox denies creating links; inject metadata to exercise fail-closed logic.
        from unittest.mock import patch
        target=assemble(self.entries,self.reader,self.component)
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError): assemble(self.entries,self.reader,self.component)
        original = Path.stat
        def linked_stat(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path.name == 'file.py':
                from types import SimpleNamespace
                return SimpleNamespace(st_mode=result.st_mode, st_nlink=2)
            return result
        with patch.object(Path, 'stat', linked_stat):
            with self.assertRaises(ValueError): assemble(self.entries,self.reader,self.component)
