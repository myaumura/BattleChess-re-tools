"""Native font-decoder checks; synthetic glyphs are fixtures, never replacement fonts."""

from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/recompilation"))
from bitmap_fonts import nfnt, sfnt, generate
import tempfile
import hashlib
from system_fonts import extract, control_code


# Native validation (no original entrypoint): exercise packed rows, bearings and corrupt spans.
def check():
    # Character A plus missing glyph; height2, one16-bit row, locations0,3,5.
    header = struct.pack(">HhhhhhhhHhhhh", 0, 65, 65, 4, -1, -1, 3, 2, 10, 1, 1, 0, 1)
    fixture = (
        header
        + bytes((0xB8, 0, 0x50, 0))
        + struct.pack(">3H", 0, 3, 5)
        + bytes((1, 4, 1, 3))
    )
    glyphs = nfnt(fixture)
    assert glyphs[65] == (3, 2, 0, 1, 4, bytes((1, 0, 1, 0, 1, 0)))
    assert glyphs[64] == (2, 2, 0, 1, 3, bytes((1, 1, 1, 0)))
    for bad in (
        fixture[:25],
        fixture[:-1],
        fixture[:30] + struct.pack(">3H", 0, 20, 5) + fixture[36:],
    ):
        try:
            nfnt(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted invalid FONT/NFNT")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "fonts.hpp"
        generate(output)
        assert "geneva_available = false" in output.read_text()
    fonts = Path(__file__).resolve().parents[2] / "source/system7/fonts"
    for name, digest, metrics in [
        (
            "Chicago12.NFNT",
            "36157cec9b4fc731994ca93a7b3749dc9a8e2c24e6460f9b296cf98b45405852",
            (12, 3, 1),
        ),
        (
            "Geneva9.NFNT",
            "b2bbba4a4cd1e78320c6a4256bd5d08e01326349804905a1e5d577521f03c754",
            (10, 2, 0),
        ),
    ]:
        raw = (fonts / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        assert struct.unpack_from(">hhh", raw, 18) == metrics
        assert nfnt(raw)[ord("W")][4] > nfnt(raw)[ord("i")][4]
    icon = (fonts / "Stop.ICON").read_bytes()
    assert len(icon) == 128
    assert (
        hashlib.sha256(icon).hexdigest()
        == "207876ed7e1ca612bd8e457f3f071acc245d684cb89952f540b9c19f5e3ab4c4"
    )
    system = Path("/tmp/battlechess-System.bin")
    if system.exists():
        assert (
            hashlib.sha256(control_code(system.read_bytes())).hexdigest()
            == "b647566a3fe540ae1e2477e6c3ced3d3a33cfffc131fcd8fbfa22c5774cc0dde"
        )
        with tempfile.TemporaryDirectory() as directory:
            extract(system, directory)
            for name in ("Chicago12.NFNT", "Geneva9.NFNT", "Stop.ICON"):
                assert (Path(directory) / name).read_bytes() == (
                    fonts / name
                ).read_bytes()
    font = Path("/System/Library/Fonts/Geneva.ttf")
    if font.exists():
        glyphs = sfnt(font.read_bytes(), 9)
        assert sum(glyphs[c][4] for c in b"Produced by:") == 59
        assert sum(glyphs[c][4] for c in b"Macintosh programming:") == 111
        assert (
            sum(
                glyphs[c][4]
                for c in "presents Battle Chess®: Black & White Edition".encode(
                    "mac_roman"
                )
            )
            == 210
        )
        assert glyphs[ord("i")][4] < glyphs[ord("W")][4]
        try:
            sfnt(font.read_bytes(), 11)
        except ValueError:
            pass
        else:
            raise AssertionError("synthesized absent bitmap size")
    print("bitmap font decoding, original About advances and unavailable fallback: ok")


if __name__ == "__main__":
    check()
