# SPDX-License-Identifier: Apache-2.0
"""Recorded hashes must remain enforced when Python assertions are disabled."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

class VendorVerification(unittest.TestCase):
    def test_optimized_python_rejects_changed_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'scripts').mkdir()
            (root / 'vendor' / 'example').mkdir(parents=True)
            checker = root / 'scripts' / 'check-vendor.py'
            shutil.copyfile(Path(__file__).resolve().parents[1] / 'scripts' / 'check-vendor.py', checker)
            payload = root / 'vendor' / 'example' / 'source.goose'
            payload.write_bytes(b'original snapshot')
            manifest = {'schema': 1, 'libraries': [{'directory': 'example',
                'files': {'source.goose': hashlib.sha256(payload.read_bytes()).hexdigest()}}]}
            (root / 'vendor' / 'manifest.json').write_text(json.dumps(manifest))
            valid = subprocess.run([sys.executable, '-O', str(checker)], capture_output=True, timeout=10)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            payload.write_bytes(b'changed snapshot')
            invalid = subprocess.run([sys.executable, '-O', str(checker)], capture_output=True, timeout=10)
            self.assertNotEqual(invalid.returncode, 0)
            self.assertIn(b'differs from its recorded snapshot', invalid.stderr)

if __name__ == '__main__':
    unittest.main()
