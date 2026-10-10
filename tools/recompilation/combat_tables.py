"""Original CRUNCHAN tables and omitted archive-1 combat assets; no invented clips."""

import base64
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/scripts"))
from decode_archive import Decoder


# Native generation/validation (no original entrypoint): Load the recovered A5 global block
# and its original base address.
def globals_data():
    model = json.loads((ROOT / "recovered/recovery_model.json").read_text())
    block = next(b for b in model["blocks"] if b["name"] == "A5_globals")
    return block["address"], base64.b64decode(block["data"])


# Native generation/validation (no original entrypoint): Read count consecutive 255-terminated
# streams from the recovered globals.
def streams(address, count):
    start, data = globals_data()
    result = []
    position = address - start
    for _ in range(count):
        end = data.index(255, position)
        result.append(
            dict(address=start + position, bytes=list(data[position : end + 1]))
        )
        position = end + 1
    return result


# Original file offset 0x5382 (EXPANDDA, tools/3rd-party/dump.log): expand compressed combat
# timing into runtime command bytes.
def combat_timing():
    """EXPANDDA 0x5382: fcdd2 is a heap pointer, fcdd6 is compressed source."""
    result, expanded_offset = [], 0
    for source in streams(0xFCDD6, 72):
        raw, expanded, i = source["bytes"], [], 0
        while raw[i] != 255:
            value = raw[i]
            if value < 60:
                expanded.extend([0] * (value + 1))
                i += 1
            else:
                assert i + 1 < len(raw) - 1
                expanded.extend([value - 1, raw[i + 1]])
                i += 2
        expanded.append(255)
        result.append(
            dict(
                address=source["address"],
                expanded_offset=expanded_offset,
                compressed=raw,
                bytes=expanded,
            )
        )
        expanded_offset += len(expanded)
    assert expanded_offset <= 10000  # Original allocated destination size.
    assert result[0]["bytes"] == (
        [0] * 61
        + [0x83, 0x3F]
        + [0] * 31
        + [0x87, 0x4B]
        + [0] * 6
        + [0x8B, 0x45]
        + [0] * 18
        + [255]
    )
    return result


# Native generation/validation (no original entrypoint): Decode sound commands from an
# expanded combat timing stream.
def sound_events(timing):
    result, i = [], 0
    while timing[i] != 255:
        if timing[i] >= 128:
            assert i + 1 < len(timing) - 1
            result.append(
                dict(offset=i, bank=timing[i] & 15, parameter=timing[i + 1] - 64)
            )
            i += 2
        else:
            i += 1
    return result


# Native generation/validation (no original entrypoint): Resolve the original combat group
# selection into an extracted asset name.
def group_for(display_type, role1=False):
    # Dense switch dispatch at 0x12cf8 and 0x12d54; argument to SETUPSEQ.
    zero = display_type - 1
    special = {0: -7, 1: -3, 4: 1} if role1 else {1: -5, 4: -1}
    if zero in special:
        argument = special[zero]
        return f"combat_archive1_{argument + 7:02}", argument, 1
    argument = (zero + (6 if role1 else 0)) * 2 + 9
    index = argument - 3
    return f"combat_{(index - 6) // 4:02}_{index:02}", argument, 2


# Native generation/validation (no original entrypoint): Assemble defender and moving-attacker
# sequences, timing and sound metadata.
def combat(role0, role1):
    """Return role0 (defender) and role1 (moving attacker), display types 1..6."""
    assert 1 <= role0 <= 6 and 1 <= role1 <= 6
    selection, timing = streams(0xFC405, 72), combat_timing()
    result = {}
    for role, piece, index, is_role1 in [
        ("role0", role0, (role0 - 1) * 6 + role1 - 1, False),
        ("role1", role1, 36 + (role1 - 1) * 6 + role0 - 1, True),
    ]:
        name, argument, archive = group_for(piece, is_role1)
        result[role] = dict(
            group=name,
            archive=archive,
            setupseq_argument=argument,
            selection_address=selection[index]["address"],
            sequences=selection[index]["bytes"][:-1],
            timing_source_address=timing[index]["address"],
            timing_expanded_offset=timing[index]["expanded_offset"],
            timing_compressed=timing[index]["compressed"],
            timing=timing[index]["bytes"],
            sounds=sound_events(timing[index]["bytes"]),
        )
    return result


# Native generation/validation (no original entrypoint): Recover omitted archive-one combat
# groups using the existing raw asset schema.
def extract_extra(output):
    """Same raw asset/manifest schema as extract_external_graphics, without previews."""
    start, data = globals_data()
    archive = (ROOT / "source/macintosh/extracted/ALLCANM1.data").read_bytes()
    groups = []
    for argument in [-7, -5, -3, -1, 1]:
        offsets = struct.unpack_from(">4I", data, 0xFD85E + (argument - 3) * 8 - start)
        name = f"combat_archive1_{argument + 7:02}"
        for kind, label, (meta_offset, compressed_offset) in [
            ("delta", name, offsets[:2]),
            ("static", name + "_bases", offsets[2:]),
        ]:
            meta = archive[meta_offset:compressed_offset]
            decoder = Decoder(archive, compressed_offset)
            raw = decoder.read()
            bit_decoder = Decoder(archive, compressed_offset)
            shapes, sequences, position, consumed, bits = [], [], 0, 0, 0
            unit = 6 if kind == "delta" else 4
            while position + unit <= len(meta) and meta[
                position : position + 4
            ] != bytes(4):
                w, h, hx, hy = struct.unpack_from(">BBbb", meta, position)
                size = ((w + 3) // 4) * h
                shape = dict(
                    width=w,
                    height=h,
                    hotspot_x=hx,
                    hotspot_y=hy,
                    decoded_offset=consumed,
                )
                if kind == "delta":
                    shape["compressed_bit_length"] = struct.unpack_from(
                        ">H", meta, position + 4
                    )[0]
                    bits += shape["compressed_bit_length"]
                    if size:
                        bit_decoder.read(size)
                    assert (
                        bits == 0
                        or bit_decoder.bit - (compressed_offset + 8) * 8 == bits
                    ), (
                        label,
                        len(shapes),
                        shape,
                        bit_decoder.bit - (compressed_offset + 8) * 8,
                        bits,
                    )
                shapes.append(shape)
                consumed += size
                position += unit
            assert consumed == len(raw), (label, consumed, len(raw))
            if kind == "delta":
                assert meta[position : position + 6] == bytes(6)
                position += 6
                count = meta[position]
                position += 1
                for _ in range(count):
                    length, base = meta[position : position + 2]
                    indices = list(meta[position + 2 : position + 2 + length])
                    assert len(indices) == length and all(
                        i < len(shapes) for i in indices
                    )
                    sequences.append(
                        dict(
                            base_selector=base,
                            deltas=indices,
                            base_source=(
                                "standing" if base & 128 else "companion combat bases"
                            ),
                        )
                    )
                    position += 2 + length
                assert position == len(meta)
                assert bits == decoder.bit - (compressed_offset + 8) * 8
            else:
                assert position == len(meta) or meta[position:] == bytes(4)
            folder = output / label
            folder.mkdir(parents=True, exist_ok=True)
            for filename, content in [("metadata.bin", meta), ("decoded.2bpp", raw)]:
                (folder / filename).write_bytes(content)
                assert (folder / filename).read_bytes() == content
            groups.append(
                dict(
                    name=label,
                    archive=1,
                    metadata_offset=meta_offset,
                    compressed_offset=compressed_offset,
                    compressed_end=(decoder.bit + 7) // 8,
                    decoded_bytes=len(raw),
                    kind=kind,
                    shapes=shapes,
                    sequences=sequences,
                )
            )
    return dict(groups=groups)


# Native generation/validation (no original entrypoint): Extract missing combat assets and
# validate all generated combat pair metadata.
def generate(output):
    manifest = extract_extra(output)
    existing = json.loads((ROOT / "assets/external_graphics/manifest.json").read_text())
    groups = {g["name"]: g for g in existing["groups"] + manifest["groups"]}
    for group in manifest["groups"]:
        for seq in group["sequences"]:
            selector = seq["base_selector"]
            bases = groups["standing" if selector & 128 else group["name"] + "_bases"][
                "shapes"
            ]
            assert (selector & 127) < len(bases)
    pairs = [
        dict(role0_type=a, role1_type=v, **combat(a, v))
        for a in range(1, 7)
        for v in range(1, 7)
    ]
    for pair in pairs:
        for role in ["role0", "role1"]:
            entry = pair[role]
            assert all(event["bank"] < 15 for event in entry["sounds"])
            assert all(
                i < len(groups[entry["group"]]["sequences"]) for i in entry["sequences"]
            )
    manifest["combat"] = pairs
    manifest["movement_timing"] = streams(0xFD372, 144)
    path = output / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    assert json.loads(path.read_text()) == manifest
    print(
        f'{len(manifest["groups"])} extra groups, {len(pairs)} verified combat pairs: {path}'
    )


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/extra_animation")
