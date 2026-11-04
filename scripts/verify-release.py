#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only verification of a public release against explicit local Git anchors."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import urllib.request
import urllib.parse
import zlib

MAX_ARCHIVE = 32 * 1024 * 1024
MAX_UNPACKED = 128 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_ENTRIES = 8192
MAX_METADATA = 1024 * 1024
FORBIDDEN = {'.git', '.build', '.toolchain', '__pycache__'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def full_sha(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value),
            'expected a full lowercase 40-character Git SHA')
    return value


def json_data(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def safe_path(name):
    require(isinstance(name, str) and 0 < len(name) <= 1024 and '\\' not in name and
            not any(ord(c) < 32 or ord(c) == 127 for c in name), 'invalid archive/vendor path')
    parts = name.split('/')
    require(all(part and part not in ('.', '..') for part in parts), 'unsafe path')
    require(not any(part in FORBIDDEN for part in parts) and
            not name.endswith(('.pyc', '.pyo')), 'generated state in release')
    return name


def git(root, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], timeout=30)


def commit_tree(root, commit):
    require(git(root, 'rev-parse', '--verify', commit + '^{commit}').decode().strip() == commit,
            'commit anchor is unavailable or is not a commit')
    return git(root, 'rev-parse', commit + '^{tree}').decode().strip()


def git_files(root, commit):
    result = {}
    for entry in git(root, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not entry:
            continue
        header, raw_name = entry.split(b'\t', 1)
        mode, kind, oid = header.split()
        name = safe_path(raw_name.decode('utf-8'))
        require(kind == b'blob' and mode in (b'100644', b'100755'),
                f'unsupported Git entry: {name}')
        result[name] = (mode == b'100755', oid.decode())
    return result


def read_archive(raw, expected):
    require(len(raw) <= MAX_ARCHIVE, 'compressed archive exceeds limit')
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
        unpacked = compressed.read(MAX_UNPACKED + 1)
    require(len(unpacked) <= MAX_UNPACKED, 'expanded archive exceeds limit')
    files, seen, prefix = {}, set(), None
    with tarfile.open(fileobj=io.BytesIO(unpacked), mode='r:') as archive:
        for count, member in enumerate(archive, 1):
            require(count <= MAX_ENTRIES, 'too many archive entries')
            name = member.name.rstrip('/') if member.isdir() else member.name
            safe_path(name)
            require(name not in seen, 'duplicate archive entry')
            seen.add(name)
            parts = name.split('/', 1)
            if prefix is None:
                prefix = parts[0]
            require(parts[0] == prefix, 'multiple archive roots')
            require(member.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE) and
                    member.sparse is None, 'links/special/sparse archive entries forbidden')
            require(0 <= member.mode <= 0o777, 'privileged/non-POSIX archive mode forbidden')
            if len(parts) == 1:
                require(member.isdir(), 'archive must have a root directory')
                continue
            relative = safe_path(parts[1])
            if member.isdir():
                require(any(path.startswith(relative + '/') for path in expected),
                        'unexpected archive directory')
                continue
            require(relative in expected, f'unexpected archive file: {relative}')
            require(0 <= member.size <= MAX_FILE, 'archive member exceeds limit')
            data = archive.extractfile(member).read()
            executable, oid = expected[relative]
            require(bool(member.mode & 0o111) == executable, 'executable mode differs from Git')
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            require(actual == oid, f'archive bytes differ from Git: {relative}')
            files[relative] = data
        tail = unpacked[archive.offset:]
        require(len(tail) >= 1024 and not any(tail), 'invalid tar end marker or trailing payload')
    require(files.keys() == expected.keys(), 'archive is missing committed files')
    return files


def vendor_graph(files):
    for name in ('toml_edit.goose', 'LICENSE', 'GOOSE_REVISION', 'vendor/manifest.json'):
        require(bool(files.get(name)), f'missing/empty required file: {name}')
    compiler = full_sha(files['GOOSE_REVISION'].decode('ascii').strip())
    manifest = json_data(files['vendor/manifest.json'])
    require(type(manifest['schema']) is int and manifest['schema'] == 1 and isinstance(manifest['libraries'], list) and
            manifest['libraries'], 'invalid vendor schema/libraries')
    directories, graph = set(), {}
    for library in manifest['libraries']:
        directory = safe_path(library['directory'])
        require('/' not in directory and directory not in directories, 'duplicate/nested vendor directory')
        directories.add(directory)
        full_sha(library['revision'])
        require(isinstance(library['license'], str) and library['license'] and
                isinstance(library['repository'], str) and library['repository'] and
                isinstance(library['files'], dict) and 'LICENSE' in library['files'],
                'vendor license record/file required')
        for name, digest in library['files'].items():
            path = 'vendor/' + directory + '/' + safe_path(name)
            require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest),
                    'invalid vendor SHA-256')
            require(path in files and hashlib.sha256(files[path]).hexdigest() == digest,
                    f'vendor snapshot mismatch: {path}')
            graph[path] = digest
        require(bool(files['vendor/' + directory + '/LICENSE']), 'empty vendor license')
    actual = {path for path in files if path.startswith('vendor/') and path != 'vendor/manifest.json'}
    require(actual == graph.keys(), 'unlisted vendored files')
    identities = [{key: library[key] for key in ('directory', 'repository', 'revision', 'license')}
                  for library in manifest['libraries']]
    return compiler, graph, identities


def verify(root, tag, commit, tested, metadata, raw, prerelease=True):
    full_sha(commit); full_sha(tested)
    release, reference = metadata['release'], metadata['tag_ref']
    require(release['tag_name'] == tag and release['draft'] is False and
            release['prerelease'] is prerelease, 'release tag/draft/prerelease policy mismatch')
    require(reference['ref'] == 'refs/tags/' + tag, 'tag reference name mismatch')
    target, seen = reference['object'], set()
    while target['type'] == 'tag':
        oid = full_sha(target['sha'])
        require(oid not in seen and len(seen) < 8, 'cyclic/deep annotated tag chain')
        seen.add(oid)
        record = metadata['annotated_tags'][oid]
        require(record['sha'] == oid, 'annotated tag identity mismatch')
        target = record['object']
    require(target['type'] == 'commit' and target['sha'] == commit, 'tag target differs from expected commit')
    tree = commit_tree(root, commit)
    require(tree == commit_tree(root, tested), 'release tree differs from tested head')
    files = read_archive(raw, git_files(root, commit))
    compiler, graph, identities = vendor_graph(files)
    return {'tag': tag, 'commit': commit, 'tested_head': tested, 'tree': tree,
            'prerelease': prerelease, 'files': len(files), 'compiler_revision': compiler,
            'archive_sha256': hashlib.sha256(raw).hexdigest(), 'vendor_sha256': graph,
            'vendor_libraries': identities,
            'result': 'pass'}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'goose-toml-edit-release-verifier'})
    with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect).open(request, timeout=30) as response:
        raw = response.read(limit + 1)
    require(len(raw) <= limit, 'download exceeds limit')
    return raw


def live_metadata(repo, tag):
    api = 'https://api.github.com/repos/' + repo
    encoded = urllib.parse.quote(tag, safe='')
    release = json_data(fetch(api + '/releases/tags/' + encoded, MAX_METADATA))
    reference = json_data(fetch(api + '/git/ref/tags/' + encoded, MAX_METADATA))
    records, target = {}, reference['object']
    while target['type'] == 'tag':
        oid = full_sha(target['sha'])
        require(oid not in records and len(records) < 8, 'cyclic/deep annotated tag chain')
        record = json_data(fetch(api + '/git/tags/' + oid, MAX_METADATA))
        records[oid] = record
        target = record['object']
    return {'release': release, 'tag_ref': reference, 'annotated_tags': records}


def bounded_file(path, limit):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    require(len(raw) <= limit, 'input file exceeds limit')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--tested-head', required=True)
    parser.add_argument('--repo', default='carabistouflette/goose-toml-edit')
    parser.add_argument('--git-repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--metadata', type=Path, help='offline API bundle: release, tag_ref, annotated_tags')
    parser.add_argument('--archive', type=Path, help='offline GitHub-style gzip tar archive')
    parser.add_argument('--stable', action='store_true', help='require a stable release instead of prerelease')
    args = parser.parse_args()
    if bool(args.metadata) != bool(args.archive):
        parser.error('--metadata and --archive must be supplied together')
    try:
        full_sha(args.expected_commit); full_sha(args.tested_head)
        require(re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo), 'invalid repository name')
        if args.metadata:
            metadata_raw = bounded_file(args.metadata, MAX_METADATA)
            metadata = json_data(metadata_raw)
            raw = bounded_file(args.archive, MAX_ARCHIVE)
        else:
            metadata = live_metadata(args.repo, args.tag)
            metadata_raw = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()
            raw = fetch('https://codeload.github.com/' + args.repo + '/tar.gz/refs/tags/' +
                        urllib.parse.quote(args.tag, safe=''), MAX_ARCHIVE)
        report = verify(args.git_repo, args.tag, args.expected_commit, args.tested_head,
                        metadata, raw, not args.stable)
        report.update({'metadata_mode': 'offline' if args.metadata else 'live',
                       'metadata_sha256': hashlib.sha256(metadata_raw).hexdigest(), 'repository': args.repo})
        print(json.dumps(report, indent=2))
    except (ValueError, KeyError, TypeError, OSError, EOFError, RecursionError, zlib.error, tarfile.TarError,
            subprocess.SubprocessError) as error:
        print(f'release verification failed: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
