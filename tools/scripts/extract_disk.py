"""Extract this Macintosh HFS disk through installed hfsutils, preserving forks.

hfsutils writes its virtual-volume registry ~/.hcwd; no OS mount is performed.
The source image is copied and made read-only before hmount.
"""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("ALLCANM1", "ALLCANM2", "Battle Chess", "Battle Chess Manual")


def split_macbinary(blob):
    if len(blob) < 128 or blob[0] != 0 or not 1 <= blob[1] <= 63:
        raise ValueError("Invalid MacBinary header")
    name = blob[2 : 2 + blob[1]].decode("mac_roman")
    data_size, resource_size = struct.unpack_from(">II", blob, 83)
    resource_offset = 128 + (data_size + 127) // 128 * 128
    if resource_offset + resource_size > len(blob):
        raise ValueError("Truncated MacBinary forks")
    return (
        name,
        blob[128 : 128 + data_size],
        blob[resource_offset : resource_offset + resource_size],
    )


def extract():
    for command in ("hmount", "hcopy", "humount"):
        if not shutil.which(command):
            raise SystemExit(f"Install hfsutils: missing {command}")
    source = ROOT / "source/macintosh/BattleChess.img"
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    folder = ROOT / "source/macintosh/extracted"
    folder.mkdir(exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix="battlechess-hfs-") as temp:
        image = Path(temp) / "BattleChess.img"
        shutil.copyfile(source, image)
        image.chmod(0o444)
        subprocess.run(["hmount", str(image)], check=True)
        try:
            subprocess.run(
                ["hcopy", "-m", *[":" + n for n in NAMES], str(temp) + "/"], check=True
            )
        finally:
            subprocess.run(["humount", str(image)], check=True)
        assert hashlib.sha256(image.read_bytes()).hexdigest() == original_hash
        blobs = {
            name: (Path(temp) / (name.replace(" ", "_") + ".bin")).read_bytes()
            for name in NAMES
        }
    canonical = ROOT / "source/macintosh/BattleChess.bin"
    application = blobs["Battle Chess"]
    if split_macbinary(application)[0] != "Battle Chess":
        raise ValueError("Unexpected application name on game disk")
    if canonical.exists() or canonical.is_symlink():
        if canonical.read_bytes() != application:
            raise ValueError(
                "Game disk application differs from the supplied MacBinary"
            )
    else:
        with canonical.open("xb") as output:
            output.write(application)
    for expected in NAMES:
        binary = folder / (expected.replace(" ", "_") + ".bin")
        blob = blobs[expected]
        name, data, resource = split_macbinary(blob)
        assert name == expected
        if name == "Battle Chess":
            if binary.exists() or binary.is_symlink():
                assert binary.read_bytes() == blob
                binary.unlink()
            binary.symlink_to("../BattleChess.bin")
        else:
            binary.write_bytes(blob)
        assert binary.read_bytes() == blob
        for suffix, content in (("data", data), ("rsrc", resource)):
            if content:
                output = folder / f"{name}.{suffix}"
                output.write_bytes(content)
                assert output.read_bytes() == content
        records.append(
            dict(
                name=name,
                macbinary=binary.name,
                data_length=len(data),
                resource_length=len(resource),
                sha256=hashlib.sha256(blob).hexdigest(),
            )
        )
    assert (folder / "Battle_Chess.bin").read_bytes() == (
        ROOT / "source/macintosh/BattleChess.bin"
    ).read_bytes()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    target = folder / "manifest.json"
    target.write_text(json.dumps(records, indent=2) + "\n")
    assert json.loads(target.read_text()) == records
    print(
        "Extracted four files; forks reopened; application matches original; disk unchanged"
    )


if __name__ == "__main__":
    # Small malformed-input check in addition to real-input extraction assertions.
    try:
        split_macbinary(bytes(128))
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid header accepted")
    extract()
