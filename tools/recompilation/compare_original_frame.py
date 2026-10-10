#!/usr/bin/env python3
"""Compare a native initial frame with the recorded System 7 executable capture.

Native validation only: WIND400 exposes 511x320 pixels at screen (64,90).
The original mouse cursor covers local x20..29/y18..32; exclude only that area.
"""

import argparse
from pathlib import Path
import struct
import zlib


def read_png(path):
    """Decode noninterlaced RGB/RGBA PNGs emitted by SDL and browser canvas."""
    source = Path(path).read_bytes()
    assert source[:8] == b"\x89PNG\r\n\x1a\n"
    offset, compressed = 8, bytearray()
    while offset < len(source):
        length = struct.unpack_from(">I", source, offset)[0]
        kind = source[offset + 4 : offset + 8]
        data = source[offset + 8 : offset + 8 + length]
        assert (
            zlib.crc32(kind + data)
            == struct.unpack_from(">I", source, offset + 8 + length)[0]
        )
        offset += length + 12
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", data)
            )
            assert (
                depth == 8
                and color in (2, 6)
                and (compression, filtering, interlace) == (0, 0, 0)
            )
        elif kind == b"IDAT":
            compressed.extend(data)
        elif kind == b"IEND":
            break
    channels = 4 if color == 6 else 3
    stride = width * channels
    raw = zlib.decompress(compressed)
    assert len(raw) == height * (stride + 1)
    prior, rows = bytes(stride), []
    for y in range(height):
        mode = raw[y * (stride + 1)]
        assert mode <= 4
        row = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            above = prior[x]
            diagonal = prior[x - channels] if x >= channels else 0
            estimate = left + above - diagonal
            distances = [abs(estimate - value) for value in (left, above, diagonal)]
            predictor = (
                0,
                left,
                above,
                (left + above) // 2,
                (left, above, diagonal)[distances.index(min(distances))],
            )[mode]
            row[x] = (row[x] + predictor) & 255
        rows.append([bytes(row[x : x + 3]) for x in range(0, stride, channels)])
        prior = row
    return rows


def main():
    """Require every unoccluded original content pixel to match at integer scale."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path)
    parser.add_argument(
        "--original",
        type=Path,
        default=Path(__file__).resolve().parents[2]
        / "docs/recompilation/evidence/original-initial.png",
    )
    parser.add_argument(
        "--exact-viewport",
        action="store_true",
        help="Require WIND400 content plus the native 20-pixel menu bar",
    )
    args = parser.parse_args()
    original, native = read_png(args.original), read_png(args.native)
    assert (len(original[0]), len(original)) == (640, 480)
    # Retain old 512-wide captures as references; strict mode rejects that adaptation.
    logical_width = 511 if args.exact_viewport or len(native[0]) % 511 == 0 else 512
    scale = len(native[0]) // logical_width
    assert (
        scale >= 1
        and len(native[0]) == logical_width * scale
        and len(native) >= 340 * scale
    )
    if args.exact_viewport:
        assert (
            len(native) == 340 * scale
        ), "Viewport must contain exactly 320 board rows"
    checked = 0
    for y in range(320):
        for x in range(511):
            if 20 <= x < 30 and 18 <= y < 33:
                continue
            expected = original[90 + y][64 + x]
            for dy in range(scale):
                for dx in range(scale):
                    assert native[(20 + y) * scale + dy][x * scale + dx] == expected, (
                        x,
                        y,
                        dx,
                        dy,
                    )
            checked += 1
    print(
        f"{checked} original visible content pixels match at {scale}x; cursor rectangle excluded"
    )


if __name__ == "__main__":
    main()
