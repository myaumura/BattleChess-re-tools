"""Preparation owns a new output only; failures preserve user files."""

from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools/scripts"), str(ROOT / "scripts")]
from extract_disk import split_macbinary
import extract_disk
from fixtures import macbinary


def load_pipeline(test):
    source = ROOT / "scripts/prepare_game_data.py"
    test.assertTrue(source.is_file(), "The autonomous preparation command is missing")
    spec = importlib.util.spec_from_file_location("prepare_game_data", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_pack(path):
    path.mkdir()
    (path / "animation_pixels.bin").write_bytes(b"indexed pixels")
    digest = hashlib.sha256(b"indexed pixels").hexdigest()
    (path / "checksums.json").write_text(json.dumps({"animation_pixels.bin": digest}))


class PipelineTests(unittest.TestCase):
    def test_help_works_without_original_files_or_external_commands(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/prepare_game_data.py"), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in ("--disk", "--system", "--output"):
            self.assertIn(option, result.stdout)

    def test_missing_and_wrong_reference_inputs_fail_before_output_creation(self):
        pipeline = load_pipeline(self)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            disk, system, output = (
                folder / "game.img",
                folder / "System.bin",
                folder / "output",
            )
            system.write_bytes(b"not a System MacBinary")
            for payload in (None, b"wrong game version"):
                if payload is not None:
                    disk.write_bytes(payload)
                with (
                    self.subTest(payload=payload),
                    self.assertRaises((OSError, ValueError)),
                ):
                    pipeline.prepare(disk, system, output)
                self.assertFalse(output.exists())

    def test_existing_output_and_dangling_symlink_are_preserved(self):
        pipeline = load_pipeline(self)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            output = folder / "output"
            output.mkdir()
            marker = output / "keep.txt"
            marker.write_text("user work")
            with self.assertRaises(ValueError):
                pipeline.prepare(folder / "disk", folder / "system", output)
            self.assertEqual(marker.read_text(), "user work")
            link = folder / "link"
            link.symlink_to(folder / "missing")
            with self.assertRaises(ValueError):
                pipeline.prepare(folder / "disk", folder / "system", link)
            self.assertTrue(link.is_symlink())

    def test_destination_inside_a_source_checkout_is_rejected(self):
        pipeline = load_pipeline(self)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".git").mkdir()
            output = root / "build/data"
            with self.assertRaises(ValueError):
                pipeline.prepare(root / "disk", root / "system", output)
            self.assertFalse(output.exists())

    def test_success_publishes_verified_pack_and_cleans_workspace(self):
        pipeline = load_pipeline(self)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            disk, system, output = (
                folder / "disk.img",
                folder / "System.bin",
                folder / "prepared data",
            )
            disk.write_bytes(b"keep disk")
            system.write_bytes(b"keep System")

            def build(workspace, system_file):
                pack = workspace / "pack"
                write_pack(pack)
                return pack

            with (
                patch.object(pipeline, "check_inputs"),
                patch.object(pipeline, "build_pack", side_effect=build),
            ):
                pipeline.prepare(disk, system, output)
            self.assertEqual(
                (output / "animation_pixels.bin").read_bytes(), b"indexed pixels"
            )
            self.assertEqual(
                sorted(p.name for p in folder.iterdir()),
                ["System.bin", "disk.img", "prepared data"],
            )
            self.assertEqual(disk.read_bytes(), b"keep disk")
            self.assertEqual(system.read_bytes(), b"keep System")

    def test_generation_and_checksum_failures_leave_no_partial_output(self):
        pipeline = load_pipeline(self)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            disk, system = folder / "disk", folder / "system"
            disk.write_bytes(b"original disk")
            system.write_bytes(b"original System")

            def fail(workspace, system_file):
                (workspace / "partial").write_bytes(b"partial")
                raise RuntimeError("external stage failed")

            def corrupt(workspace, system_file):
                pack = workspace / "pack"
                write_pack(pack)
                (pack / "animation_pixels.bin").write_bytes(b"corruption")
                return pack

            for index, build in enumerate((fail, corrupt)):
                output = folder / f"output-{index}"
                with (
                    self.subTest(index=index),
                    patch.object(pipeline, "check_inputs"),
                    patch.object(pipeline, "build_pack", side_effect=build),
                ):
                    with self.assertRaises((RuntimeError, ValueError)):
                        pipeline.prepare(disk, system, output)
                self.assertFalse(output.exists())
            self.assertEqual(
                sorted(p.name for p in folder.iterdir()), ["disk", "system"]
            )

    def test_racing_output_creation_preserves_the_other_writer(self):
        pipeline = load_pipeline(self)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            disk, system, output = folder / "disk", folder / "system", folder / "output"
            disk.write_bytes(b"disk")
            system.write_bytes(b"system")

            def build(workspace, system_file):
                pack = workspace / "pack"
                write_pack(pack)
                output.mkdir()
                (output / "keep").write_bytes(b"other writer")
                return pack

            with (
                patch.object(pipeline, "check_inputs"),
                patch.object(pipeline, "build_pack", side_effect=build),
            ):
                with self.assertRaises(ValueError):
                    pipeline.prepare(disk, system, output)
            self.assertEqual((output / "keep").read_bytes(), b"other writer")

    def test_manifest_rejects_missing_changed_extra_and_escaping_files(self):
        pipeline = load_pipeline(self)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            pack = folder / "pack"
            write_pack(pack)
            self.assertEqual(pipeline.verify_pack(pack), 1)
            pixel_file = pack / "animation_pixels.bin"
            pixel_file.write_bytes(b"wrong")
            with self.assertRaises(ValueError):
                pipeline.verify_pack(pack)
            pixel_file.unlink()
            with self.assertRaises(ValueError):
                pipeline.verify_pack(pack)
            (pack / "checksums.json").write_text(json.dumps({"../secret": "0" * 64}))
            with self.assertRaises(ValueError):
                pipeline.verify_pack(pack)
            (pack / "checksums.json").write_text("{}")
            pixel_file.write_bytes(b"extra")
            with self.assertRaises(ValueError):
                pipeline.verify_pack(pack)


class DiskExtractionTests(unittest.TestCase):
    def test_disk_only_extraction_creates_canonical_application_and_keeps_original_image(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "source/macintosh").mkdir(parents=True)
            image = root / "source/macintosh/BattleChess.img"
            image.write_bytes(b"invented disk fixture")
            blobs = {
                name: macbinary(name, b"fork bytes") for name in extract_disk.NAMES
            }

            def command(args, **kwargs):
                if args[0] == "hcopy":
                    for name, blob in blobs.items():
                        (
                            Path(args[-1]) / (name.replace(" ", "_") + ".bin")
                        ).write_bytes(blob)

            with (
                patch.object(extract_disk, "ROOT", root),
                patch.object(extract_disk.shutil, "which", return_value="hfsutils"),
                patch.object(extract_disk.subprocess, "run", side_effect=command),
            ):
                extract_disk.extract()
                self.assertEqual(
                    (root / "source/macintosh/BattleChess.bin").read_bytes(),
                    blobs["Battle Chess"],
                )
                self.assertTrue(
                    (root / "source/macintosh/extracted/Battle_Chess.bin").is_symlink()
                )
                self.assertEqual(image.read_bytes(), b"invented disk fixture")
                (root / "source/macintosh/BattleChess.bin").write_bytes(
                    b"keep existing application"
                )
                with self.assertRaises(ValueError):
                    extract_disk.extract()
                self.assertEqual(
                    (root / "source/macintosh/BattleChess.bin").read_bytes(),
                    b"keep existing application",
                )


class DependencyTests(unittest.TestCase):
    def test_valid_container_reports_missing_tools_before_preparation(self):
        pipeline = load_pipeline(self)
        from fixtures import resource_file

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            disk, system = root / "disk", root / "System.bin"
            disk.write_bytes(b"invented reference")
            system.write_bytes(
                resource_file(
                    [
                        (b"FOND", 0, "Chicago", b""),
                        (b"FOND", 3, "Geneva", b""),
                        (b"ICON", 0, "", bytes(128)),
                    ]
                )
            )
            with (
                patch.object(
                    pipeline,
                    "REFERENCE_DISK",
                    hashlib.sha256(disk.read_bytes()).hexdigest(),
                ),
                patch.object(pipeline.shutil, "which", return_value=None),
            ):
                with self.assertRaisesRegex(
                    ValueError, "m68kdasm.*hmount.*hcopy.*humount"
                ):
                    pipeline.check_inputs(disk, system)
            self.assertEqual(
                sorted(path.name for path in root.iterdir()), ["System.bin", "disk"]
            )

    def test_external_stage_failure_reports_its_name_and_exit_status(self):
        pipeline = load_pipeline(self)
        with self.assertRaisesRegex(RuntimeError, "test stage.*7"):
            pipeline.run_stage(
                "test stage", [sys.executable, "-c", "raise SystemExit(7)"]
            )
