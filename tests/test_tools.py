"""Synthetic checks: no original game files or images are required."""

from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/scripts"))
from analyze_dump import read_source
import extract_assets


def run(script, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / script), *map(str, args)],
        capture_output=True,
        text=True,
        cwd="/tmp",
    )


class WorkspaceTests(unittest.TestCase):
    def test_tools_run_in_an_external_workspace_with_spaces(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "private workspace"
            result = run("scripts/create_workspace.py", workspace)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run(
                [sys.executable, str(workspace / "tools/scripts/decode_archive.py")],
                capture_output=True,
                text=True,
                cwd=temp,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((workspace / "RecoverBattleChess.java").exists())
            self.assertFalse((workspace / "tools/scripts/rebuild_recovery.py").exists())
            self.assertTrue((workspace / "tools/scripts/prepare_recovery.py").is_file())
            self.assertFalse((workspace / "source/macintosh/BattleChess.bin").exists())

    def test_existing_workspace_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "keep.txt"
            marker.write_text("user work")
            result = run("scripts/create_workspace.py", temp)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), "user work")
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), ["keep.txt"])

    def test_workspace_inside_public_repository_is_rejected(self):
        target = ROOT / "private-test-workspace"
        result = run("scripts/create_workspace.py", target)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(target.exists())


class AnalysisTests(unittest.TestCase):
    def test_resource_payload_gaps_are_filled_from_verified_binary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "source/macintosh").mkdir(parents=True)
            (root / "tools/3rd-party").mkdir(parents=True)
            (root / "source/macintosh/BattleChess.bin").write_bytes(bytes(128))
            (root / "tools/3rd-party/dump.log").write_text(
                "00000000  0000 synthetic word\n"
            )
            # Isolate payload extraction from the independent container analyzer.
            report = {
                "resources": [
                    {"type": "ICON", "id": i, "offset": 0, "size": 128}
                    for i in range(3, 14)
                ]
            }
            with patch.object(extract_assets, "analyze", return_value=report):
                extract_assets.extract(root)
            self.assertEqual((root / "assets/raw/ICON_3.bin").read_bytes(), bytes(128))

    def test_binary_and_dump_work_without_supplemental_ghidra_listing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "source/macintosh").mkdir(parents=True)
            (root / "tools/3rd-party").mkdir(parents=True)
            (root / "source/macintosh/BattleChess.bin").write_bytes(
                bytes((0x12, 0x34, 0x56))
            )
            dump = root / "tools/3rd-party/dump.log"
            dump.write_text("00000000  1234 synthetic word\n")
            memory, _, known = read_source(root)
            self.assertEqual(memory, {0: 0x12, 1: 0x34, 2: 0x56})
            self.assertEqual(known, 2)
            dump.write_text("00000000  FFFF conflicting word\n")
            with self.assertRaises(ValueError):
                read_source(root)


class PublicationTests(unittest.TestCase):
    def test_media_binary_and_symlink_are_rejected(self):
        spec = importlib.util.spec_from_file_location(
            "publication", ROOT / "scripts/check_publication.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.violations(ROOT), [])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text("Public instructions\n")
            (root / ".DS_Store").write_bytes(b"Finder metadata\0")
            self.assertEqual(module.violations(root), [])
            image = root / "capture.png"
            image.write_bytes(b"synthetic test marker")
            self.assertTrue(module.violations(root))
            image.unlink()
            text = root / "dump.md"
            text.write_bytes(b"binary\0payload")
            self.assertTrue(module.violations(root))
            text.unlink()
            link = root / "source.py"
            link.symlink_to(root / "README.md")
            self.assertTrue(module.violations(root))


if __name__ == "__main__":
    unittest.main()
