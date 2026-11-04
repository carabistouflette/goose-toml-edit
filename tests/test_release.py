# SPDX-License-Identifier: Apache-2.0
"""Hermetic release verification, including deliberately malformed artifacts."""
import copy
from contextlib import redirect_stdout
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import urllib.request
import urllib.response
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/verify-release.py'
SPEC = importlib.util.spec_from_file_location('release_verifier', SCRIPT)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class ReleaseVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run_git('init', '-q')
        self.run_git('config', 'user.name', 'Fixture')
        self.run_git('config', 'user.email', 'fixture@example.invalid')
        self.run_git('config', 'commit.gpgsign', 'false')
        self.run_git('config', 'core.hooksPath', '/dev/null')
        self.files = {'LICENSE': b'root license', 'GOOSE_REVISION': b'a' * 40 + b'\n',
                      'toml_edit.goose': b'fixture source', 'vendor/lib/LICENSE': b'vendor license',
                      'vendor/lib/lib.goose': b'vendor source'}
        manifest = {'schema': 1, 'libraries': [{'directory': 'lib', 'revision': 'b' * 40,
                    'repository': 'https://github.com/example/lib',
                    'license': 'Apache-2.0', 'files': {name: hashlib.sha256(self.files['vendor/lib/' + name]).hexdigest()
                    for name in ('LICENSE', 'lib.goose')}}]}
        self.files['vendor/manifest.json'] = json.dumps(manifest).encode()
        self.commit = self.commit_files(self.files)
        self.run_git('commit', '-q', '--allow-empty', '-m', 'identical tested tree')
        self.tested = self.run_git('rev-parse', 'HEAD').strip().decode()
        self.metadata = {'release': {'tag_name': 'v0.1.0', 'draft': False, 'prerelease': True},
                         'tag_ref': {'ref': 'refs/tags/v0.1.0',
                                     'object': {'type': 'commit', 'sha': self.commit}},
                         'annotated_tags': {}}

    def run_git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE)

    def commit_files(self, files):
        for name, data in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.run_git('add', '.')
        self.run_git('commit', '-q', '-m', 'fixture')
        return self.run_git('rev-parse', 'HEAD').decode().strip()

    def archive(self, files=None, extras=(), modes=None):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w') as archive:
            for name, data in (self.files if files is None else files).items():
                member = tarfile.TarInfo('fixture/' + name)
                member.size = len(data); member.mode = (modes or {}).get(name, 0o644)
                archive.addfile(member, io.BytesIO(data))
            for member, data in extras:
                archive.addfile(member, io.BytesIO(data))
        return gzip.compress(output.getvalue())

    def verify(self, raw=None, metadata=None, commit=None, tested=None):
        return verifier.verify(self.root, 'v0.1.0', commit or self.commit, tested or self.tested,
                               self.metadata if metadata is None else metadata,
                               self.archive() if raw is None else raw)

    def test_valid_and_annotated_tags(self):
        self.assertEqual(self.verify()['result'], 'pass')
        metadata = copy.deepcopy(self.metadata)
        oid = 'c' * 40
        metadata['annotated_tags'][oid] = {'sha': oid, 'object': metadata['tag_ref']['object']}
        metadata['tag_ref']['object'] = {'type': 'tag', 'sha': oid}
        self.assertEqual(self.verify(metadata=metadata)['files'], len(self.files))
        metadata['annotated_tags'][oid]['object'] = {'type': 'tag', 'sha': oid}
        with self.assertRaisesRegex(ValueError, 'cyclic/deep'):
            self.verify(metadata=metadata)

    def test_release_identity_policy(self):
        for field, value in [('draft', True), ('draft', 0), ('prerelease', False), ('tag_name', 'other')]:
            metadata = copy.deepcopy(self.metadata); metadata['release'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.verify(metadata=metadata)
        # Equal trees do not permit substituting a different expected commit.
        with self.assertRaisesRegex(ValueError, 'tag target'):
            self.verify(commit=self.tested)
        metadata = copy.deepcopy(self.metadata); metadata['tag_ref']['ref'] = 'refs/tags/other'
        with self.assertRaisesRegex(ValueError, 'reference name'):
            self.verify(metadata=metadata)

    def test_changed_tested_tree_and_replacement_refs(self):
        changed = dict(self.files, extra=b'new')
        different = self.commit_files(changed)
        with self.assertRaisesRegex(ValueError, 'tested head'):
            self.verify(tested=different)
        # A local replacement must not make the different tree equal to the anchor.
        self.run_git('replace', different, self.commit)
        with self.assertRaisesRegex(ValueError, 'tested head'):
            self.verify(tested=different)

    def test_modified_missing_extra_and_executable_files(self):
        changed = dict(self.files); changed['toml_edit.goose'] = b'corrupt'
        missing = dict(self.files); del missing['LICENSE']
        for files in (changed, missing, dict(self.files, extra=b'extra')):
            with self.subTest(files=list(files)), self.assertRaises(ValueError):
                self.verify(self.archive(files))
        with self.assertRaisesRegex(ValueError, 'executable mode'):
            self.verify(self.archive(modes={'toml_edit.goose': 0o755}))
        for mode in (0o4644, 0o2644, 0o1644):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'archive mode'):
                self.verify(self.archive(modes={'LICENSE': mode}))
        directory = tarfile.TarInfo('fixture/vendor'); directory.type = tarfile.DIRTYPE
        directory.mode = 0o1777
        with self.assertRaisesRegex(ValueError, 'archive mode'):
            self.verify(self.archive(extras=[(directory, b'')]))

    def test_positive_stable_nested_and_executable_release(self):
        self.run_git('update-index', '--chmod=+x', 'toml_edit.goose')
        self.run_git('commit', '-q', '-m', 'executable fixture')
        commit = self.run_git('rev-parse', 'HEAD').decode().strip()
        metadata = copy.deepcopy(self.metadata); metadata['release']['prerelease'] = False
        metadata['tag_ref']['object']['sha'] = commit
        raw = self.archive(modes={'toml_edit.goose': 0o755})
        report = verifier.verify(self.root, 'v0.1.0', commit, commit, metadata, raw, prerelease=False)
        self.assertFalse(report['prerelease'])
        files = dict(self.files); files['vendor/lib/nested/source.goose'] = b'nested'
        manifest = json.loads(files['vendor/manifest.json'])
        manifest['libraries'][0]['files']['nested/source.goose'] = hashlib.sha256(b'nested').hexdigest()
        files['vendor/manifest.json'] = json.dumps(manifest).encode()
        self.assertIn('vendor/lib/nested/source.goose', verifier.vendor_graph(files)[1])

    def test_paths_duplicates_links_sparse_and_mixed_roots(self):
        for name in ('fixture/../escape', '/absolute', 'fixture/./LICENSE',
                     'fixture//LICENSE', 'fixture/.build/generated', 'other/extra',
                     'fixture/LICENSE'):
            member = tarfile.TarInfo(name); member.size = 1
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.verify(self.archive(extras=[(member, b'x')]))
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.GNUTYPE_SPARSE, tarfile.FIFOTYPE):
            member = tarfile.TarInfo('fixture/evil'); member.type = kind; member.linkname = 'LICENSE'
            with self.subTest(kind=kind), self.assertRaises((ValueError, tarfile.TarError)):
                self.verify(self.archive(extras=[(member, b'')]))
        member = tarfile.TarInfo('fixture/safe'); member.pax_headers = {'path': 'fixture/../escape'}
        with self.assertRaises(ValueError):
            self.verify(self.archive(extras=[(member, b'')]))

    def test_truncated_gzip_and_hidden_payload(self):
        raw = self.archive()
        with self.assertRaises((EOFError, OSError)):
            self.verify(raw[:-4])
        for suffix in (gzip.compress(b'nonzero'), self.archive()):
            with self.subTest(size=len(suffix)), self.assertRaises(ValueError):
                self.verify(raw + suffix)

    def test_size_and_entry_limits_before_parsing(self):
        raw = self.archive()
        for constant, limit in [('MAX_ARCHIVE', len(raw) - 1), ('MAX_UNPACKED', 100),
                                ('MAX_FILE', 2), ('MAX_ENTRIES', 1)]:
            with self.subTest(constant=constant), patch.object(verifier, constant, limit), self.assertRaises(ValueError):
                self.verify(raw)
        member = tarfile.TarInfo('fixture/safe'); member.pax_headers = {'comment': 'x' * 10000}
        with patch.object(verifier, 'MAX_UNPACKED', 1000), self.assertRaises(ValueError):
            self.verify(self.archive(extras=[(member, b'')]))

    def test_malformed_committed_vendor_and_required_records(self):
        variants = []
        for name in ('LICENSE', 'GOOSE_REVISION'):
            variants.append(dict(self.files, **{name: b''}))
        variants.append(dict(self.files, GOOSE_REVISION=b'short'))
        for mutation in ('hash', 'revision', 'license', 'path', 'duplicate', 'unlisted'):
            files = dict(self.files); manifest = json.loads(files['vendor/manifest.json']);lib = manifest['libraries'][0]
            if mutation == 'hash': lib['files']['lib.goose'] = '0' * 64
            elif mutation == 'revision': lib['revision'] = 'main'
            elif mutation == 'license': del lib['files']['LICENSE']
            elif mutation == 'path': lib['files']['../escape'] = '0' * 64
            elif mutation == 'duplicate': manifest['libraries'].append(copy.deepcopy(lib))
            else: files['vendor/lib/unlisted.goose'] = b'extra'
            files['vendor/manifest.json'] = json.dumps(manifest).encode(); variants.append(files)
        for files in variants:
            with self.subTest(files=files), self.assertRaises(ValueError):
                verifier.vendor_graph(files)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            verifier.json_data(b'{"schema":1,"schema":2}')

    def test_cli_optimized_python(self):
        metadata = self.root / 'metadata.json'; archive = self.root / 'archive.tar.gz'
        metadata.write_text(json.dumps(self.metadata)); archive.write_bytes(self.archive())
        command = [sys.executable, '-O', str(SCRIPT), '--git-repo', str(self.root), '--tag', 'v0.1.0',
                   '--expected-commit', self.commit, '--tested-head', self.tested,
                   '--metadata', str(metadata), '--archive', str(archive)]
        good = subprocess.run(command, capture_output=True, timeout=30)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['metadata_mode'], 'offline')
        # A tiny network budget cannot affect offline verification or spawn a worker.
        with patch.object(verifier, 'download_live', side_effect=AssertionError('offline network')), \
                patch.object(verifier.tempfile, 'TemporaryDirectory', side_effect=AssertionError('offline temp')), \
                patch.object(sys, 'argv', command[2:] + ['--network-deadline', '0.001']), \
                redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(verifier.main(), 0)
        offline = json.loads(captured.getvalue())
        self.assertEqual(offline['metadata_mode'], 'offline')
        self.assertNotIn('network_deadline_seconds', offline)
        archive.write_bytes(self.archive(dict(self.files, LICENSE=b'corrupt')))
        bad = subprocess.run(command, capture_output=True, timeout=30)
        self.assertEqual(bad.returncode, 1, bad.stderr)
        self.assertEqual(bad.stdout, b'')
        self.assertIn(b'release verification failed', bad.stderr)
        incomplete = subprocess.run(command[:-2], capture_output=True, timeout=30)
        self.assertEqual(incomplete.returncode, 2)
        self.assertIn(b'must be supplied together', incomplete.stderr)
        metadata.write_bytes(b' ' * (verifier.MAX_METADATA + 1))
        oversized = subprocess.run(command, capture_output=True, timeout=30)
        self.assertEqual(oversized.returncode, 1)
        self.assertIn(b'input file exceeds limit', oversized.stderr)
        invalid = subprocess.run(command + ['--network-deadline', 'nan'], capture_output=True, timeout=30)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn(b'must be finite', invalid.stderr)

    def test_fetch_ignores_credential_proxy_and_bounds_response(self):
        requests = []
        class OfflineHTTPS(urllib.request.HTTPSHandler):
            def https_open(self, request):
                requests.append(request)
                response = urllib.response.addinfourl(io.BytesIO(b'ok'), {}, request.full_url, 200)
                response.msg = 'OK'
                return response
        with patch.dict(os.environ, {'https_proxy': 'http://user:secret@proxy.invalid:8080',
                                     'HTTPS_PROXY': 'http://user:secret@proxy.invalid:8080'}), \
                patch.object(urllib.request, 'HTTPSHandler', OfflineHTTPS):
            self.assertEqual(verifier.fetch('https://fixture.invalid/data', 2), b'ok')
            self.assertFalse(requests[-1].has_proxy())
            self.assertEqual(requests[-1].host, 'fixture.invalid')
            self.assertIsNone(requests[-1].get_header('Proxy-authorization'))
            with self.assertRaisesRegex(ValueError, 'download exceeds limit'):
                verifier.fetch('https://fixture.invalid/data', 1)


if __name__ == '__main__':
    unittest.main()
