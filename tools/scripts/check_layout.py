"""Check recovery paths from an unrelated cwd, regenerating only in a temporary copy."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
import extract_disk

ROOT = Path(__file__).resolve().parents[2]


def check():
    with tempfile.TemporaryDirectory(prefix="battlechess-layout-") as temporary:
        root = Path(temporary) / "project"
        scripts = root / "tools/scripts"
        shutil.copytree(
            ROOT / "tools/scripts",
            scripts,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        for relative in (
            "source/macintosh/BattleChess.bin",
            "source/macintosh/BattleChess.txt",
            "tools/3rd-party/dump.log",
            "source/macintosh/extracted/ALLCANM1.data",
            "source/macintosh/extracted/ALLCANM2.data",
        ):
            if (
                relative == "source/macintosh/BattleChess.txt"
                and not (ROOT / relative).exists()
            ):
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        # Exercise extraction output handling without hfsutils touching ~/.hcwd.
        shutil.copyfile(
            ROOT / "source/macintosh/BattleChess.img",
            root / "source/macintosh/BattleChess.img",
        )

        def hfs_command(command, **kwargs):
            if command[0] == "hcopy":
                for name in extract_disk.NAMES:
                    filename = name.replace(" ", "_") + ".bin"
                    shutil.copyfile(
                        ROOT / "source/macintosh/extracted" / filename,
                        Path(command[-1]) / filename,
                    )
            else:
                assert command[0] in ("hmount", "humount")

        with (
            patch.object(extract_disk, "ROOT", root),
            patch.object(extract_disk.shutil, "which", return_value="hfsutils"),
            patch.object(extract_disk.subprocess, "run", side_effect=hfs_command),
        ):
            extract_disk.extract()
            binary = root / "source/macintosh/extracted/Battle_Chess.bin"
            assert (
                binary.is_symlink()
                and binary.resolve()
                == (root / "source/macintosh/BattleChess.bin").resolve()
            )
            extract_disk.extract()  # Rerunning must keep one canonical executable.
            assert binary.is_symlink()
        for original in (ROOT / "source/macintosh/extracted").iterdir():
            if original.is_file() and original.name != ".DS_Store":
                assert (
                    root / "source/macintosh/extracted" / original.name
                ).read_bytes() == original.read_bytes()
        for name in (
            "analyze_dump",
            "prepare_recovery",
            "extract_assets",
            "decode_archive",
            "extract_audio",
            "extract_external_graphics",
            "prepare_swift_assets",
        ):
            subprocess.run(
                [sys.executable, str(scripts / (name + ".py"))],
                cwd=temporary,
                check=True,
            )
        count = 0
        for relative in (
            "dump_analysis.json",
            "recovered/recovery_model.json",
            "assets",
            "swift-native/App/Resources",
        ):
            generated = root / relative
            files = [generated] if generated.is_file() else generated.rglob("*")
            for path in files:
                if path.is_file():
                    original = ROOT / path.relative_to(root)
                    assert path.read_bytes() == original.read_bytes(), str(
                        path.relative_to(root)
                    )
                    count += 1
        assert count > 0
        print(f"Layout check passed: {count} regenerated files match saved outputs.")


if __name__ == "__main__":
    check()
