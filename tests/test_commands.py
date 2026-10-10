"""Command boundaries use explicit paths and keep native sources read-only."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "scripts"),
    str(ROOT / "tools/recompilation"),
    str(ROOT / "tools/recompilation_checks"),
]
from create_workspace import create
from animation_calls import collect
from modem_native_check import frame


class CommandTests(unittest.TestCase):
    def test_animation_call_index_keeps_only_preceding_instructions(self):
        lines = ["not an instruction"] + [
            f"{4096 + i * 2:08X}  4E71 nop" for i in range(16)
        ]
        lines += [
            "00001020  4EAD jsr [A5] /* export_156 */",
            "00001024  4EAD jsr [A5] /* export_159 */",
        ]
        calls = collect(lines)["calls"]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["call_address"], "0x00001020")
        self.assertEqual(calls[0]["callee"], "STARTANI_0x133c4")
        self.assertEqual(calls[0]["preceding_instructions"], lines[3:17])
        self.assertEqual(calls[1]["preceding_instructions"][-1], lines[-2])

    def test_modem_fixture_emits_independently_recorded_wire_bytes(self):
        self.assertEqual(frame(0xA5), bytes.fromhex("a5 04 c5 34"))
        self.assertEqual(
            frame(0xA2, bytes([0x34, 0x14])), bytes.fromhex("a2 06 34 14 f6 4a")
        )

    def test_linux_wrapper_preserves_space_paths_and_readonly_mounts(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            workspace = create(folder / "private workspace")
            native = folder / "native source"
            native.mkdir()
            (workspace / "recompilation").symlink_to(native)
            executable = folder / "bin/docker"
            executable.parent.mkdir()
            executable.write_text(
                '#!/bin/sh\nprintf "%s\\n" "$@" > "$BC_TEST_DOCKER_ARGS"\n'
            )
            executable.chmod(0o755)
            output, arguments = folder / "linux output", folder / "docker-arguments"
            environment = dict(
                os.environ,
                PATH=str(executable.parent) + os.pathsep + os.environ["PATH"],
                BC_TEST_DOCKER_ARGS=str(arguments),
            )
            result = subprocess.run(
                [
                    "sh",
                    str(workspace / "tools/recompilation/validate_linux.sh"),
                    str(output),
                ],
                env=environment,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            args = arguments.read_text().splitlines()
            self.assertEqual(args[:2], ["run", "--rm"])
            mounts = {}
            for argument in args:
                if argument.startswith("type=bind,"):
                    fields = dict(
                        field.split("=", 1)
                        for field in argument.split(",")
                        if "=" in field
                    )
                    mounts[fields["target"]] = (
                        Path(fields["source"]).resolve(),
                        "readonly" in argument.split(","),
                    )
            self.assertEqual(mounts["/source"], (workspace.resolve(), True))
            self.assertEqual(mounts["/native"], (native.resolve(), True))
            self.assertEqual(mounts["/validation"], (output.resolve(), False))
            self.assertEqual(list(native.iterdir()), [])
