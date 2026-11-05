# SPDX-License-Identifier: Apache-2.0
"""Child fixture: exercise the real downloader without external network access."""
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import time

script, base, mode, audit, directory, repo, tag = sys.argv[1:]
Path(audit).write_text(json.dumps({'pid': os.getpid(), 'directory': directory}))
namespace = runpy.run_path(script, run_name='download_fixture')
worker = namespace['_download_worker']
original_fetch = namespace['fetch']

if mode == 'partial':
    (Path(directory) / 'archive.tar.gz').write_bytes(b'partial')
    sys.exit(0)
if mode == 'oversized':
    (Path(directory) / 'metadata.json').write_text('{}')
    (Path(directory) / 'archive.tar.gz').write_bytes(b'oversized')
    sys.exit(0)
if mode == 'error':
    def fail(*args):
        raise ValueError('failure:' + 'x' * 10000)
    worker.__globals__['live_metadata'] = fail
elif mode == 'dns':
    def blocked_dns(*args, **kwargs):
        Path(audit + '.phase').write_text('dns')
        time.sleep(30)
    socket.getaddrinfo = blocked_dns
else:
    def local_fetch(url, limit):
        phase = 'metadata' if '/releases/tags/' in url else 'tag' if '/git/ref/tags/' in url else 'archive'
        return original_fetch(base + '/' + phase, limit)
    worker.__globals__['fetch'] = local_fetch
sys.exit(worker(directory, repo, tag))
