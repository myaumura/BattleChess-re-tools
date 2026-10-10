"""Recover embedded graphics from verified original bytes. Run: python3 tools/scripts/extract_assets.py.
Uses only Python stdlib. Four bitmap PICTs are decoded; one vector PICT is preserved.
"""

import hashlib
import json
import struct
import zlib
from pathlib import Path
from analyze_dump import analyze, read_source


def png(path, width, height, pixels):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    rows = b"".join(
        b"\0" + pixels[y * width * 4 : (y + 1) * width * 4] for y in range(height)
    )
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )
    saved = path.read_bytes()
    assert saved[12:16] == b"IHDR" and struct.unpack(">2I", saved[16:24]) == (
        width,
        height,
    )
    assert zlib.decompress(saved[41:-16]) == rows


def extract(root):
    memory, _, _ = read_source(root)
    inventory = analyze(root)["resources"]
    folder = root / "assets"
    for child in ["raw", "pictures", "icons", "cursors"]:
        (folder / child).mkdir(parents=True, exist_ok=True)
    entries = []
    for resource in inventory:
        kind = resource["type"]
        if kind not in ["PICT", "ICN#", "ICON", "CURS"]:
            continue
        payload = bytes(
            memory[i]
            for i in range(resource["offset"], resource["offset"] + resource["size"])
        )
        stem = kind.replace("#", "_mask") + "_" + str(resource["id"])
        raw = folder / "raw" / (stem + ".bin")
        raw.write_bytes(payload)
        assert raw.read_bytes() == payload
        entry = dict(
            resource,
            raw=str(raw.relative_to(folder)),
            sha256=hashlib.sha256(payload).hexdigest(),
        )
        if kind == "PICT":
            source = folder / "pictures" / (stem + ".pict")
            source.write_bytes(bytes(512) + payload)
            assert source.read_bytes()[512:] == payload
            target = source.with_suffix(".png")
            if resource["id"] == 10001:
                entry["pict"] = str(source.relative_to(folder))
                entry["preview_error"] = (
                    "Text/vector PICT; macOS sips and AppKit cannot decode it."
                )
                entries.append(entry)
                continue
            # These four PICT v1 resources contain one PackBitsRect. Validate the
            # exact shared header rather than pretending to implement all QuickDraw.
            assert payload[10:30] == bytes.fromhex(
                "1101a00082a0008e01000a0000000002e8024098"
            )
            rowbytes = struct.unpack(">H", payload[30:32])[0]
            bounds = struct.unpack(">4h", payload[32:40])
            src = struct.unpack(">4h", payload[40:48])
            dst = struct.unpack(">4h", payload[48:56])
            assert bounds == (0, 0, 100, 56) and src == dst == (0, 0, 100, 50)
            assert rowbytes == 8 and payload[56:58] == b"\0\1"
            width, height = 50, 100
            cursor, pixels = 58, bytearray()
            for y in range(height):
                size = payload[cursor]
                cursor += 1
                end = cursor + size
                row = bytearray()
                while cursor < end:
                    control = payload[cursor]
                    cursor += 1
                    if control < 128:
                        row.extend(payload[cursor : cursor + control + 1])
                        cursor += control + 1
                    elif control > 128:
                        row.extend([payload[cursor]] * (257 - control))
                        cursor += 1
                assert cursor == end and len(row) == rowbytes
                for x in range(width):
                    value = 0 if row[x // 8] & (128 >> (x % 8)) else 255
                    pixels.extend([value, value, value, 255])
            assert payload[cursor:] == bytes.fromhex("a0008fa00083ff")
            png(target, width, height, pixels)
        else:
            width = height = 16 if kind == "CURS" else 32
            count = width * height // 8
            assert len(payload) == (
                68 if kind == "CURS" else 256 if kind == "ICN#" else 128
            )
            bitmap = payload[:count]
            mask = (
                payload[count : count * 2] if kind != "ICON" else bytes([255]) * count
            )
            # Classic cursor data=1/mask=0 means invert. PNG cannot invert its backdrop;
            # keep an explicit count and preview these pixels opaque black.
            invert = sum((a & ~b).bit_count() for a, b in zip(bitmap, mask))
            pixels = bytearray()
            for i in range(width * height):
                bit = 128 >> (i % 8)
                value = 0 if bitmap[i // 8] & bit else 255
                alpha = 255 if (mask[i // 8] | bitmap[i // 8]) & bit else 0
                pixels.extend([value, value, value, alpha])
            target = (
                folder / ("cursors" if kind == "CURS" else "icons") / (stem + ".png")
            )
            png(target, width, height, pixels)
            if kind == "CURS":
                entry["hotspot_yx"] = list(struct.unpack(">2h", payload[64:68]))
                entry["invert_pixels"] = invert
        entry.update(png=str(target.relative_to(folder)), width=width, height=height)
        entries.append(entry)
    assert len(entries) == 11
    manifest = folder / "manifest.json"
    manifest.write_text(json.dumps(entries, indent=2) + "\n")
    assert json.loads(manifest.read_text()) == entries
    figures = "".join(
        f'<figure><img src="{e["png"]}" alt="{e["type"]} {e["id"]}"><figcaption>{e["type"]} {e["id"]} · {e["width"]} × {e["height"]}</figcaption></figure>'
        for e in entries
        if "png" in e
    )
    (folder / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Battle Chess extracted graphics</title><style>body{font:16px system-ui;margin:32px;background:#eee}main{display:flex;flex-wrap:wrap;gap:24px}figure{margin:0;padding:20px;background:white}img{image-rendering:pixelated;min-width:96px;max-width:100%}figcaption{margin-top:12px}</style><h1>Battle Chess embedded graphics</h1><p>Original resource artwork; no generated or downloaded images. Cursor details are in manifest.json. <a href="pictures/PICT_10001.pict">PICT 10001 (original text/vector picture)</a> is preserved without a PNG preview; see README.md.</p><main>'
        + figures
        + "</main>"
    )
    print(
        f"Extracted and reopened {len(entries)} raw graphics, 5 PICT files, and {sum('png' in e for e in entries)} PNG previews. {folder}"
    )


if __name__ == "__main__":
    extract(Path(__file__).resolve().parents[2])
