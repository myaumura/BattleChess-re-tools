"""Prepare a native game-data folder from a Battle Chess disk and System MacBinary."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from create_workspace import create

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/recompilation"))
from system_fonts import resources

REFERENCE_DISK = "ba1b3758368c032f6f8475e8bebd07db60c8736c12049ee64785f84356d50af5"
REFERENCE_APPLICATION = (
    "091d8088d305fe16ae45b60fd3f83ca36e6650e5a8c0a63b6e876cfe4fc32922"
)


def check_inputs(disk, system):
    """Reject unsupported inputs and missing executables before creating output."""
    if hashlib.sha256(disk.read_bytes()).hexdigest() != REFERENCE_DISK:
        raise ValueError(
            "Unsupported game disk: expected the reference Macintosh Battle Chess 1.0.2 HFS image"
        )
    try:
        table = resources(system.read_bytes())
        if (
            table[b"FOND", 0][0] != "Chicago"
            or table[b"FOND", 3][0] != "Geneva"
            or len(table[b"ICON", 0][1]) != 128
        ):
            raise ValueError("Missing reference bitmap families or stop icon")
    except (KeyError, ValueError) as error:
        raise ValueError(
            "Supply a System 7 System file exported as MacBinary with its resource fork intact"
        ) from error
    missing = [
        name
        for name in ("m68kdasm", "hmount", "hcopy", "humount")
        if not shutil.which(name)
    ]
    if missing:
        raise ValueError(
            "Install these external tools and put them on PATH: " + ", ".join(missing)
        )


def run_stage(label, command):
    print(f"Preparing: {label}", flush=True)
    try:
        subprocess.run([str(part) for part in command], check=True)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"{label} failed (exit {error.returncode}); no prepared output was published"
        ) from error


def build_pack(workspace, system):
    """Run the existing tools in their isolated, private filesystem layout."""
    python = sys.executable
    scripts = workspace / "tools/scripts"
    generators = workspace / "tools/recompilation"
    checks = workspace / "tools/recompilation_checks"
    run_stage("extract HFS disk", [python, scripts / "extract_disk.py"])
    application = workspace / "source/macintosh/BattleChess.bin"
    if hashlib.sha256(application.read_bytes()).hexdigest() != REFERENCE_APPLICATION:
        raise ValueError(
            "The disk did not yield the supported Battle Chess application"
        )
    run_stage(
        "disassemble application",
        [
            shutil.which("m68kdasm"),
            "--68k",
            application,
            workspace / "tools/3rd-party/dump.log",
        ],
    )
    for filename, label in (
        ("analyze_dump.py", "analyze resources"),
        ("prepare_recovery.py", "reconstruct analysis model"),
        ("extract_assets.py", "decode embedded graphics"),
        ("extract_audio.py", "decode sound effects"),
        ("extract_external_graphics.py", "decode animation frames"),
    ):
        run_stage(label, [python, scripts / filename])
    run_stage(
        "extract System fonts and stop icon",
        [
            python,
            generators / "system_fonts.py",
            system,
            workspace / "source/system7/fonts",
        ],
    )
    pack = workspace / "build/native-data"
    run_stage(
        "generate native data pack", [python, generators / "prepare_data.py", pack]
    )
    run_stage(
        "check animation pixels", [python, checks / "animation_assets_check.py", pack]
    )
    run_stage("check reference fonts", [python, checks / "bitmap_fonts_check.py"])
    return pack


def verify_pack(pack):
    """Reopen every saved file; reject missing, extra or changed pack content."""
    files = json.loads((pack / "checksums.json").read_text())
    if not isinstance(files, dict) or not files:
        raise ValueError("Prepared pack has an empty or invalid checksum manifest")
    actual = set()
    for path in pack.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlink in prepared pack: {path.name}")
        if path.is_file() and path != pack / "checksums.json":
            actual.add(path.relative_to(pack).as_posix())
    if actual != set(files):
        raise ValueError("Prepared pack files differ from the checksum manifest")
    for name, digest in files.items():
        path = pack / name
        if not path.resolve().is_relative_to(pack.resolve()):
            raise ValueError(f"Checksum path escapes prepared pack: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Prepared file checksum differs: {name}")
    return len(files)


def prepare(disk, system, output):
    """Publish a complete verified pack, preserving inputs and existing outputs."""
    if not __debug__:
        raise ValueError(
            "Run without -O or PYTHONOPTIMIZE: recovery assertions must remain enabled"
        )
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(
            "Output already exists; reuse that pack or choose a new directory"
        )
    output = output.resolve()
    if (
        output == ROOT
        or ROOT in output.parents
        or any((parent / ".git").exists() for parent in (output, *output.parents))
    ):
        raise ValueError("Keep prepared game data outside source checkouts")
    disk, system = Path(disk).resolve(), Path(system).resolve()
    check_inputs(disk, system)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Sibling staging permits an atomic directory rename on the same filesystem.
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}-prep-", dir=output.parent
    ) as temporary:
        workspace = create(Path(temporary) / "workspace")
        shutil.copyfile(disk, workspace / "source/macintosh/BattleChess.img")
        system_copy = workspace / "source/system7/System.bin"
        shutil.copyfile(system, system_copy)
        pack = build_pack(workspace, system_copy)
        count = verify_pack(pack)
        try:
            output.mkdir()
        except FileExistsError as error:
            raise ValueError(
                "Output was created by another process; its contents were preserved"
            ) from error
        try:
            pack.replace(output)
        except OSError:
            # Remove only our empty reservation; preserve any concurrent writer's files.
            try:
                output.rmdir()
            except OSError:
                pass
            raise
    print(f"Prepared and verified {count} files: {output}")
    print(f"Build the native application with BC_DATA_DIR set to this folder: {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--disk",
        required=True,
        type=Path,
        help="Reference Macintosh Battle Chess HFS disk image",
    )
    parser.add_argument(
        "--system",
        required=True,
        type=Path,
        help="System 7 System file in MacBinary format",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New prepared-data folder outside source checkouts",
    )
    args = parser.parse_args()
    try:
        prepare(args.disk, args.system, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
