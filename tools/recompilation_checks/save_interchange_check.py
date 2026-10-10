"""Native transfer check: preserve save bytes and Macintosh Finder identity."""

from pathlib import Path
import hashlib
import json
import shutil
import resource
import signal
import subprocess
import sys
import tempfile


def check():
    """Catch missing/wrong Finder fields, changed forks and unsafe overwrite."""
    tool = (
        Path(__file__).resolve().parents[2] / "tools/recompilation/save_interchange.py"
    )
    # Independent initial board, with nonzero opaque bytes to catch lossy transfer.
    data = bytes(range(40)) + bytes.fromhex(
        "00 35 42 14 53 66 66 66 66 "
        "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
        "ee ee ee ee bd ca 9c db f1 03 56 f2 f3"
    )
    assert len(data) == 78
    with tempfile.TemporaryDirectory(prefix="bc-save-transfer-") as directory:
        folder = Path(directory)
        raw, packed, restored = (
            folder / "native.game",
            folder / "transfer.bin",
            folder / "restored.game",
        )
        raw.write_bytes(data)
        result = subprocess.run(
            [
                sys.executable,
                str(tool),
                "export",
                str(raw),
                str(packed),
                "--name",
                "Test Game",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        blob = packed.read_bytes()
        assert len(blob) == 256 and blob[:11] == b"\0\x09Test Game"
        assert blob[65:73] == b"GameIPBC"
        assert blob[83:91] == b"\0\0\0\x4e\0\0\0\0"
        assert blob[122:124] == b"\x81\x81"
        assert blob[128:206] == data and blob[206:] == bytes(50)
        result = subprocess.run(
            [sys.executable, str(tool), "import", str(packed), str(restored)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert restored.read_bytes() == data
        # Existing output must survive both command paths.
        for command, source, target in [
            ("export", raw, packed),
            ("import", packed, restored),
        ]:
            before = target.read_bytes()
            result = subprocess.run(
                [sys.executable, str(tool), command, str(source), str(target)],
                capture_output=True,
            )
            assert result.returncode != 0 and target.read_bytes() == before

        # A real short-write/close failure must remove only the new partial output.
        def limit_output():
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (200, 200))

        partial = folder / "partial.bin"
        result = subprocess.run(
            [sys.executable, str(tool), "export", str(raw), str(partial)],
            capture_output=True,
            preexec_fn=limit_output,
        )
        assert result.returncode != 0 and not partial.exists()
        # CRC corruption, wrong Finder type, truncated fork and extra resource fork.
        for index, invalid in enumerate(
            [
                blob[:115] + b"\x01" + blob[116:],
                blob[:65] + b"TEXT" + blob[69:],
                blob[:205],
                blob[:90] + b"\x01" + blob[91:] + bytes(128),
            ]
        ):
            source, target = folder / f"bad-{index}.bin", folder / f"bad-{index}.game"
            source.write_bytes(invalid)
            result = subprocess.run(
                [sys.executable, str(tool), "import", str(source), str(target)],
                capture_output=True,
            )
            assert result.returncode != 0 and not target.exists()
        raw.write_bytes(data + b"\0")
        result = subprocess.run(
            [sys.executable, str(tool), "export", str(raw), str(folder / "bad.bin")],
            capture_output=True,
        )
        assert result.returncode != 0 and not (folder / "bad.bin").exists()
    print(
        "MacBinary save transfer: exact forks/Finder fields, malformed input and overwrite guards"
    )


def check_hfs(output):
    """Optional real hfsutils transfer; only a disk copy is written, registry restored."""
    for command in ["hmount", "hcopy", "humount", "hls"]:
        if not shutil.which(command):
            raise SystemExit(f"Missing hfsutils command: {command}")
    output.mkdir()
    root = Path(__file__).resolve().parents[2]
    original = root / "source/macintosh/BattleChess.img"
    source_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    image = output / "BattleChess-copy.img"
    shutil.copyfile(original, image)
    data = bytes(range(40)) + bytes.fromhex(
        "00 35 42 14 53 66 66 66 66 "
        "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
        "ee ee ee ee bd ca 9c db f1 03 56 f2 f3"
    )
    raw, packed = output / "native.game", output / "transfer.bin"
    raw.write_bytes(data)
    tool = root / "tools/recompilation/save_interchange.py"
    subprocess.run(
        [
            sys.executable,
            str(tool),
            "export",
            str(raw),
            str(packed),
            "--name",
            "Interchange Test",
        ],
        check=True,
    )
    # hfsutils uses this global registry even for temporary image mounts.
    registry = Path.home() / ".hcwd"
    saved_registry = registry.read_bytes() if registry.exists() else None
    mounted = False
    try:
        subprocess.run(["hmount", str(image)], check=True)
        mounted = True
        subprocess.run(["hcopy", "-m", str(packed), ":"], check=True)
        listing = subprocess.run(
            ["hls", "-l", ":Interchange Test"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        print(listing, end="")
        (output / "hfs-listing.txt").write_text(listing)
        subprocess.run(
            ["hcopy", "-r", ":Interchange Test", str(output / "hfs-data.game")],
            check=True,
        )
        subprocess.run(
            ["hcopy", "-m", ":Interchange Test", str(output / "hfs-return.bin")],
            check=True,
        )
        assert (output / "hfs-data.game").read_bytes() == data
        assert (output / "hfs-return.bin").read_bytes()[65:73] == b"GameIPBC"
        subprocess.run(
            [
                sys.executable,
                str(tool),
                "import",
                str(output / "hfs-return.bin"),
                str(output / "restored.game"),
            ],
            check=True,
        )
        assert (output / "restored.game").read_bytes() == data
    finally:
        try:
            if mounted:
                subprocess.run(["humount", str(image)], check=True)
        finally:
            if saved_registry is None:
                registry.unlink(missing_ok=True)
            else:
                registry.write_bytes(saved_registry)
            assert hashlib.sha256(original.read_bytes()).hexdigest() == source_hash
    report = dict(
        original_sha256=source_hash,
        modified_copy_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
        data_sha256=hashlib.sha256(data).hexdigest(),
        finder_identity="Game/IPBC",
        data_bytes=78,
        scope="Native bytes through real HFS import/export; no original-game execution",
    )
    target = output / "report.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    assert json.loads(target.read_text()) == report
    print("HFS save transfer passed; canonical image and hfsutils registry preserved")


if __name__ == "__main__":
    check()
    if len(sys.argv) == 3 and sys.argv[1] == "--hfs-output":
        check_hfs(Path(sys.argv[2]).resolve())
    elif len(sys.argv) != 1:
        raise SystemExit(
            "Usage: save_interchange_check.py [--hfs-output NEW_DIRECTORY]"
        )
