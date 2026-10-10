"""Every Python command must be safe to import without data or external tools."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ImportTests(unittest.TestCase):
    def test_imports_do_not_read_game_data_run_commands_or_generate_output(self):
        code = """
import runpy, sys
from pathlib import Path
from unittest.mock import patch
root = Path(sys.argv[1])
sys.path[:0] = [str(root / 'tools/scripts'), str(root / 'tools/recompilation'), str(root / 'scripts')]
with patch('subprocess.run', side_effect=AssertionError('command executed during import')), patch('subprocess.Popen', side_effect=AssertionError('process started during import')):
    runpy.run_path(sys.argv[2], run_name='import_check')
"""
        sources = sorted(
            path
            for directory in ("scripts", "tools")
            for path in (ROOT / directory).rglob("*.py")
        )
        with tempfile.TemporaryDirectory() as folder:
            for source in sources:
                with self.subTest(script=str(source.relative_to(ROOT))):
                    result = subprocess.run(
                        [sys.executable, "-c", code, str(ROOT), str(source)],
                        cwd=folder,
                        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(
                        result.returncode, 0, result.stdout + result.stderr
                    )
                    self.assertEqual(result.stdout, "", "Import executed command work")
                    self.assertEqual(list(Path(folder).iterdir()), [])
