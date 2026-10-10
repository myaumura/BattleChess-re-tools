"""Build-local bitmap strikes; never synthesize or redistribute a system font."""

import argparse
import hashlib
import json
from pathlib import Path
import struct


# Native input validation (no original entrypoint): require a complete byte range.
def span(data, offset, size):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError("Truncated bitmap font")
    return data[offset : offset + size]


# Native input validation (no original entrypoint): unpack a checked big-endian record.
def unpack(fmt, data, offset=0):
    return struct.unpack(">" + fmt, span(data, offset, struct.calcsize(">" + fmt)))


# Native FONT/NFNT adapter: decode the FontRec bitmap, locations and offset/width table.
def nfnt(data):
    (
        kind,
        first,
        last,
        maximum,
        kern,
        negative_descent,
        width,
        height,
        width_table_offset,
        ascent,
        descent,
        leading,
        words,
    ) = unpack("HhhhhhhhHhhhh", data)
    if not 0 <= first <= last <= 255 or not 0 < height <= 256 or not 0 < words <= 4096:
        raise ValueError("Invalid FONT/NFNT dimensions")
    if kind & 0x002C:  # Pixel depth and non-black-color flags.
        raise ValueError("Color FONT/NFNT is unsupported")
    count = last - first + 2  # Includes the missing-character glyph.
    bits = span(data, 26, 2 * words * height)
    locations = unpack(str(count + 1) + "H", data, 26 + len(bits))
    widths = span(data, 16 + 2 * width_table_offset, count * 2)
    if (
        any(a > b for a, b in zip(locations, locations[1:]))
        or locations[-1] > words * 16
    ):
        raise ValueError("Invalid FONT/NFNT location table")
    glyphs = []
    for code in range(256):
        index = code - first if first <= code <= last else count - 1
        if widths[index * 2] >= 128:
            index = count - 1
        offset, advance = widths[index * 2 : index * 2 + 2]
        if offset >= 128:
            raise ValueError("Missing FONT/NFNT replacement glyph")
        left, right = locations[index : index + 2]
        pixels = bytes(
            (bits[y * words * 2 + x // 8] >> (7 - x % 8)) & 1
            for y in range(height)
            for x in range(left, right)
        )
        glyphs.append((right - left, height, kern + offset, ascent, advance, pixels))
    return glyphs


# Native SFNT adapter: read the installed Geneva monochrome strike, without outline rasterization.
def sfnt(data, size):
    tables = {}
    for index in range(unpack("H", data, 4)[0]):
        tag, checksum, offset, length = unpack("4sIII", data, 12 + index * 16)
        tables[tag] = span(data, offset, length)
    cmap, bloc, bdat = (tables[k] for k in (b"cmap", b"bloc", b"bdat"))
    mapping = None
    for index in range(unpack("H", cmap, 2)[0]):
        platform, encoding, offset = unpack("HHI", cmap, 4 + index * 8)
        if platform == 0 and unpack("H", cmap, offset)[0] == 12:
            table = span(cmap, offset, unpack("I", cmap, offset + 4)[0])
            mapping = [
                unpack("III", table, 16 + j * 12)
                for j in range(unpack("I", table, 12)[0])
            ]
            break
    if mapping is None:
        raise ValueError("A Unicode format-12 cmap is required")
    strike = None
    for index in range(unpack("I", bloc, 4)[0]):
        entry = span(bloc, 8 + index * 48, 48)
        if entry[44:48] == bytes((size, size, 1, 1)):
            strike = entry
            break
    if strike is None:
        raise ValueError(f"No horizontal monochrome {size}px strike")
    start, table_size, count, color = unpack("IIII", strike)
    if color:
        raise ValueError("Color bitmap strike is unsupported")
    span(bloc, start, table_size)
    indexes = []
    for index in range(count):
        first, last, relative = unpack("HHI", bloc, start + index * 8)
        offset = start + relative
        form, image, base = unpack("HHI", bloc, offset)
        if form not in (1, 3) or image not in (1, 2, 6, 7) or first > last:
            raise ValueError("Unsupported bitmap strike subtable")
        word = 4 if form == 1 else 2
        wanted = last - first + 2
        available = (start + table_size - (offset + 8)) // word
        if available < wanted - 1:
            raise ValueError("Truncated bitmap index")
        # Some Apple strikes omit only the terminal sentinel. That last glyph stays unavailable.
        actual = min(wanted, available)
        positions = list(
            unpack(str(actual) + ("I" if form == 1 else "H"), bloc, offset + 8)
        )
        if actual < wanted:
            positions.append(None)
        indexes.append((first, last, image, base, positions))
    glyphs = []
    for code in range(256):
        unicode = ord(bytes((code,)).decode("mac_roman"))
        glyph_id = next(
            (g + unicode - a for a, z, g in mapping if a <= unicode <= z), 0
        )
        record = next((r for r in indexes if r[0] <= glyph_id <= r[1]), None)
        if record is None:
            raise ValueError("Missing mapped bitmap glyph")
        first, last, image, base, positions = record
        a, z = positions[glyph_id - first : glyph_id - first + 2]
        if z is None:
            glyphs.append((0, 0, 0, 0, 0, b""))
            continue
        if a > z:
            raise ValueError("Invalid mapped bitmap offsets")
        raw = span(bdat, base + a, z - a)
        if not raw:  # Controls/nonprinting characters have no strike image.
            glyphs.append((0, 0, 0, 0, 0, b""))
            continue
        height, width, x, y, advance = unpack("BBbbB", raw)
        metrics = 8 if image in (6, 7) else 5
        row_bits = ((width + 7) // 8) * 8 if image in (1, 6) else width
        pixels = span(raw, metrics, (row_bits * height + 7) // 8)
        expanded = bytes(
            (pixels[(row * row_bits + col) // 8] >> (7 - (row * row_bits + col) % 8))
            & 1
            for row in range(height)
            for col in range(width)
        )
        glyphs.append((width, height, x, y, advance, expanded))
    return glyphs


# Native build generator: record source hashes and emit only locally generated pixel tables.
def generate(output, geneva=None, chicago=None):
    lines = [
        "// Build-local font data; do not redistribute without permission.",
        "#pragma once",
        "struct MacBitmapGlyph { int width,height,x,y,advance; unsigned offset; };",
    ]
    for name, path, size in [("geneva", geneva, 9), ("chicago", chicago, 12)]:
        glyphs = [(0, 0, 0, 0, 0, b"")] * 256
        source = "unavailable"
        ascent = descent = leading = 0
        if path:
            data = Path(path).read_bytes()
            glyphs = (
                sfnt(data, size) if data[:4] in (b"\0\1\0\0", b"true") else nfnt(data)
            )
            if data[:4] not in (b"\0\1\0\0", b"true"):
                ascent, descent, leading = unpack("hhh", data, 18)
            else:
                ascent = max(g[3] for g in glyphs)
                descent = max(g[1] - g[3] for g in glyphs)
            source = f"{Path(path).name}; SHA256={hashlib.sha256(data).hexdigest()}"
        lines.append(
            f"inline constexpr int {name}_ascent = {ascent}, {name}_descent = {descent}, {name}_leading = {leading};"
        )
        lines.append(
            f"inline constexpr bool {name}_available = {bool(path).__str__().lower()};"
        )
        lines.append(
            f"inline constexpr const char *{name}_source = {json.dumps(source)};"
        )
        records, pixels = [], bytearray()
        for width, height, x, y, advance, bitmap in glyphs:
            records.append(
                "{"
                + ",".join(map(str, (width, height, x, y, advance, len(pixels))))
                + "}"
            )
            pixels.extend(bitmap)
        lines.append(
            f"inline constexpr MacBitmapGlyph {name}_glyphs[256] = "
            + "{"
            + ",".join(records)
            + "};"
        )
        lines.append(
            f"inline constexpr unsigned char {name}_pixels[] = "
            + "{"
            + ",".join(map(str, pixels or b"\0"))
            + "};"
        )
    lines.append(
        "inline constexpr unsigned mac_roman_unicode[128] = {"
        + ",".join(
            str(ord(bytes((index,)).decode("mac_roman"))) for index in range(128, 256)
        )
        + "};"
    )
    Path(output).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("--geneva")
    parser.add_argument("--chicago")
    args = parser.parse_args()
    generate(args.output, args.geneva, args.chicago)
