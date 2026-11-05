# SPDX-License-Identifier: Apache-2.0
"""Network deadline tests use only loopback traffic and bounded owned children."""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import io
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from test_release import SCRIPT, verifier

HELPER = Path(__file__).parent / 'fixtures/release_network_worker.py'


class NetworkDeadline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audit = Path(self.temp.name) / 'child.json'
        self.directories = []

    def command(self, base, mode):
        def build(directory):
            self.directories.append(Path(directory))
            optimization = ['-OO' if sys.flags.optimize >= 2 else '-O'] if sys.flags.optimize else []
            return [sys.executable, '-I', *optimization, str(HELPER), str(SCRIPT), base,
                    mode, str(self.audit), directory, 'fixture/project', 'v0.1.0']
        return build

    def assert_cleanup(self):
        self.assertTrue(self.directories)
        self.assertTrue(all(not path.exists() for path in self.directories))
        if self.audit.exists() and os.name == 'posix':
            pid = json.loads(self.audit.read_text())['pid']
            with self.assertRaises(ChildProcessError):
                os.waitpid(pid, os.WNOHANG)

    @contextmanager
    def server(self, mode='normal'):
        stop = threading.Event()
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(self.path)
                if mode == 'headers' and self.path == '/metadata':
                    stop.wait(10)
                    return
                if mode == 'cumulative':
                    if stop.wait(2):
                        return
                payload = (json.dumps({'tag_name': 'v0.1.0', 'draft': False, 'prerelease': True}).encode()
                           if self.path == '/metadata' else
                           json.dumps({'ref': 'refs/tags/v0.1.0', 'object':
                                       {'type': 'commit', 'sha': 'a' * 40}}).encode()
                           if self.path == '/tag' else b'archive bytes')
                try:
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    if mode == 'trickle' and self.path == '/metadata':
                        for byte in payload:
                            self.wfile.write(bytes([byte])); self.wfile.flush()
                            if stop.wait(0.1):
                                return
                    elif mode == 'archive' and self.path == '/archive':
                        self.wfile.write(payload[:1]); self.wfile.flush(); stop.wait(10)
                    else:
                        self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': 0.05})
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}', requests
        finally:
            stop.set(); server.shutdown(); server.server_close(); thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

    def test_success_uses_real_download_and_cleans_child(self):
        with self.server() as (base, requests):
            metadata, encoded, archive = verifier._run_download(self.command(base, 'normal'), 5)
        self.assertEqual(requests, ['/metadata', '/tag', '/archive'])
        self.assertEqual(metadata, json.loads(encoded))
        self.assertEqual(archive, b'archive bytes')
        self.assert_cleanup()

    def test_stalled_headers_trickle_and_archive_are_deadlined(self):
        for mode in ('headers', 'trickle', 'archive'):
            with self.subTest(mode=mode), self.server(mode) as (base, requests):
                started = time.monotonic()
                with self.assertRaisesRegex(ValueError, 'network deadline exceeded'):
                    verifier._run_download(self.command(base, mode), 1.5)
                self.assertLess(time.monotonic() - started, 6)
                self.assertIn('/archive' if mode == 'archive' else '/metadata', requests)
                self.assert_cleanup()

    def test_all_requests_share_one_budget(self):
        with self.server('cumulative') as (base, requests):
            with self.assertRaisesRegex(ValueError, 'network deadline exceeded'):
                verifier._run_download(self.command(base, 'normal'), 5.5)
        self.assertEqual(requests, ['/metadata', '/tag', '/archive'])
        self.assert_cleanup()

    def test_blocked_dns_is_preempted(self):
        with self.assertRaisesRegex(ValueError, 'network deadline exceeded'):
            verifier._run_download(self.command('unused', 'dns'), 1.5)
        self.assertEqual(Path(str(self.audit) + '.phase').read_text(), 'dns')
        self.assert_cleanup()

    def test_worker_error_partial_and_oversized_results_fail_closed(self):
        for mode in ('error', 'partial', 'oversized'):
            with self.subTest(mode=mode), patch.object(verifier, 'MAX_ARCHIVE', 4):
                with self.assertRaises((ValueError, OSError)) as error:
                    verifier._run_download(self.command('unused', mode), 5)
                self.assertLess(len(str(error.exception)), 5000)
                self.assert_cleanup()

    def test_startup_budget_and_late_success(self):
        child = Mock(returncode=0)
        child.poll.return_value = 0
        with patch.object(verifier.subprocess, 'Popen', return_value=child), \
                patch.object(verifier.time, 'monotonic', side_effect=[0, 0, 2, 2]):
            with self.assertRaisesRegex(ValueError, 'network deadline exceeded'):
                verifier._run_download(self.command('unused', 'normal'), 1)
        self.assertEqual(child.wait.call_args_list[0].kwargs['timeout'], 0)
        self.assert_cleanup()

    def test_interrupt_reaps_owned_child(self):
        original = subprocess.Popen
        children = []
        def launch(*args, **kwargs):
            child = original(*args, **kwargs); children.append(child)
            wait = child.wait
            def interrupted_wait(*args, **kwargs):
                child.wait = wait
                raise KeyboardInterrupt
            child.wait = interrupted_wait
            return child
        with patch.object(verifier.subprocess, 'Popen', side_effect=launch):
            with self.assertRaises(KeyboardInterrupt):
                verifier._run_download(self.command('unused', 'dns'), 5)
        self.assertIsNotNone(children[0].returncode)
        self.assert_cleanup()

    def test_interrupt_before_process_creation_cleans_temporary_directory(self):
        with patch.object(verifier.subprocess, 'Popen', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                verifier._run_download(self.command('unused', 'normal'), 5)
        self.assert_cleanup()

    def test_ctrl_c_after_spawn_before_handle_return_is_reaped(self):
        original = subprocess.Popen
        children = []
        previous = signal.getsignal(signal.SIGINT)
        def launch(*args, **kwargs):
            child = original(*args, **kwargs); children.append(child)
            signal.raise_signal(signal.SIGINT)
            return child
        try:
            with patch.object(verifier.subprocess, 'Popen', side_effect=launch):
                with self.assertRaises(KeyboardInterrupt):
                    verifier._run_download(self.command('unused', 'dns'), 5)
            self.assertIsNotNone(children[0].returncode)
            self.assertEqual(signal.getsignal(signal.SIGINT), previous)
            self.assert_cleanup()
        finally:
            # Also contain the fixture if this regression ever fails again.
            for child in children:
                if child.poll() is None:
                    child.kill(); child.wait(timeout=2)

    def test_unconfirmed_cleanup_is_not_reported_as_reaped(self):
        child = Mock(returncode=None); child.poll.return_value = None
        child.wait.side_effect = subprocess.TimeoutExpired('fixture', 2)
        with self.assertRaisesRegex(ValueError, 'termination/reaping unconfirmed'):
            verifier._stop_worker(child)
        child.kill.assert_called_once()

    def test_launch_interrupt_cleanup_failure_restores_handler_once(self):
        previous = signal.getsignal(signal.SIGINT)
        child = Mock(returncode=None); child.poll.return_value = None
        child.wait.side_effect = subprocess.TimeoutExpired('fixture', 2)
        def launch(*args, **kwargs):
            signal.raise_signal(signal.SIGINT)
            return child
        with patch.object(verifier.subprocess, 'Popen', side_effect=launch):
            with self.assertRaisesRegex(ValueError, 'termination/reaping unconfirmed'):
                verifier._run_download(self.command('unused', 'normal'), 5)
        self.assertEqual(signal.getsignal(signal.SIGINT), previous)
        self.assertEqual(child.wait.call_count, 1)
        child.kill.assert_called_once()
        self.assert_cleanup()

    def test_launch_sigint_policy_is_restored_and_cleanup_precedes_replay(self):
        previous = signal.getsignal(signal.SIGINT)
        events = []
        def handler(signum, frame):
            events.append('handler')
        try:
            signal.signal(signal.SIGINT, handler)
            with self.assertRaises(KeyboardInterrupt):
                with verifier._defer_launch_interrupt(lambda: events.append('cleanup')):
                    signal.raise_signal(signal.SIGINT)
            self.assertEqual(events, ['cleanup', 'handler'])
            self.assertIs(signal.getsignal(signal.SIGINT), handler)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            with verifier._defer_launch_interrupt(lambda: self.fail('ignored interrupt cleanup')):
                signal.raise_signal(signal.SIGINT)
            self.assertEqual(signal.getsignal(signal.SIGINT), signal.SIG_IGN)
        finally:
            signal.signal(signal.SIGINT, previous)

    def test_interrupt_during_handler_restoration_cleans_before_replay(self):
        original = signal.signal
        previous = signal.getsignal(signal.SIGINT)
        events = []
        def handler(signum, frame):
            events.append('handler')
        def restore_edge(signum, replacement):
            if replacement is handler:
                signal.raise_signal(signal.SIGINT)
            return original(signum, replacement)
        try:
            original(signal.SIGINT, handler)
            with patch.object(verifier.signal, 'signal', side_effect=restore_edge):
                with self.assertRaises(KeyboardInterrupt):
                    with verifier._defer_launch_interrupt(lambda: events.append('cleanup')):
                        pass
            self.assertEqual(events, ['cleanup', 'handler'])
            self.assertIs(signal.getsignal(signal.SIGINT), handler)
        finally:
            original(signal.SIGINT, previous)

    def test_invalid_deadline_values(self):
        for value in ('0', '-1', 'nan', 'inf', '3601', 'word'):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                verifier.network_seconds(value)
        self.assertEqual(verifier.network_seconds('0.25'), 0.25)

    def test_worker_inherits_optimized_python_semantics(self):
        code = '''import json,runpy,sys
m=runpy.run_path(sys.argv[1],run_name='fixture')
def capture(command, seconds):
    print(json.dumps(command('/unused')))
m['download_live'].__globals__['_run_download']=capture
m['download_live']('fixture/project','v0.1.0',1)
'''
        for option in ('-O', '-OO'):
            result = subprocess.check_output([sys.executable, option, '-c', code, str(SCRIPT)], text=True)
            command = json.loads(result)
            self.assertIn(option, command)
            self.assertIn('-I', command)

    def test_cli_timeout_and_interrupt_emit_no_success_json(self):
        arguments = [str(SCRIPT), '--tag', 'v0.1.0', '--expected-commit', 'a' * 40,
                     '--tested-head', 'b' * 40, '--network-deadline', '0.25']
        for error, status in ((ValueError('network deadline exceeded'), 1), (KeyboardInterrupt(), 130)):
            with self.subTest(status=status), patch.object(sys, 'argv', arguments), \
                    patch.object(verifier, 'download_live', side_effect=error), \
                    redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as diagnostic:
                self.assertEqual(verifier.main(), status)
            self.assertEqual(output.getvalue(), '')
            self.assertIn('deadline exceeded' if status == 1 else 'interrupted', diagnostic.getvalue())


if __name__ == '__main__':
    unittest.main()
