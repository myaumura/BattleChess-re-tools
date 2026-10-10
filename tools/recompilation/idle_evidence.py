"""Audit stored idle scripts and direct Macintosh callers; no playback policy."""

import base64
import hashlib
import json
from pathlib import Path
import struct
import sys

TARGETS = {
    "DOWALK": 0xD3BC,
    "STARTANI": 0x133C4,
    "WAITANIM": 0x131F2,
    "ACTIVATE": 0x134CC,
    "SETUPSEQ": 0x11E9C,
    "SETUPSEF": 0x11BE4,
    "HANDLEAL": 0x14048,
    "DISKSEEK": 0x7C20,
    "DISKREAD": 0x7C46,
}


def code_blocks(model):
    """Original CODE payloads; exclude four-byte headers and the synthetic A5 table."""
    return [
        (b["address"], base64.b64decode(b["data"]))
        for b in model["blocks"]
        if b["name"].startswith("CODE_")
    ]


def read_memory(model, address, size):
    """Read a bounded span of the relocated evidence model, not a live address."""
    for block in model["blocks"]:
        data = base64.b64decode(block["data"])
        offset = address - block["address"]
        if 0 <= offset and offset + size <= len(data):
            return data[offset : offset + size]
    raise ValueError(f"Unmapped evidence span at {address:#x}")


def scan_calls(model):
    """Aligned direct-transfer candidates; embedded data can resemble instructions.

    Resolve A5 jump-table, PC-relative, absolute-long and BSR transfers. This is
    not a reachable-code disassembler and cannot resolve computed/indirect calls.
    """
    jump = {j["a5_offset"]: j["file_offset"] for j in model["jump_table"]}
    names = {address: name for name, address in TARGETS.items()}
    result = {name: [] for name in TARGETS}
    for start, data in code_blocks(model):
        for offset in range(4, len(data) - 1, 2):
            opcode = struct.unpack_from(">H", data, offset)[0]
            target, kind = None, None
            if opcode in (0x4EAD, 0x4EED) and offset + 4 <= len(data):
                target = jump.get(struct.unpack_from(">H", data, offset + 2)[0])
                kind = "JSR A5" if opcode == 0x4EAD else "JMP A5"
            elif opcode in (0x4EBA, 0x4EFA) and offset + 4 <= len(data):
                target = (
                    start + offset + 2 + struct.unpack_from(">h", data, offset + 2)[0]
                )
                kind = "JSR PC" if opcode == 0x4EBA else "JMP PC"
            elif opcode in (0x4EB9, 0x4EF9) and offset + 6 <= len(data):
                target = struct.unpack_from(">I", data, offset + 2)[0]
                kind = "JSR absolute" if opcode == 0x4EB9 else "JMP absolute"
            elif opcode & 0xFF00 == 0x6100:
                displacement = struct.unpack("b", bytes([opcode & 255]))[0]
                if displacement == 0:
                    if offset + 4 > len(data):
                        continue
                    displacement = struct.unpack_from(">h", data, offset + 2)[0]
                target, kind = start + offset + 2 + displacement, "BSR"
            if target in names:
                result[names[target]].append({"address": start + offset, "kind": kind})
    for calls in result.values():
        calls.sort(key=lambda c: c["address"])
    return result


def collect(root):
    """Re-read archive tables/scripts and their known dispatch paths from original bytes."""
    root = Path(root)
    model_path = root / "recovered/recovery_model.json"
    model = json.loads(model_path.read_text())
    archive_path = root / "source/macintosh/extracted/ALLCANM1.data"
    archive = archive_path.read_bytes()
    offsets = struct.unpack(">6I", read_memory(model, 0xFD7A2, 24))
    sizes = struct.unpack(">6I", read_memory(model, 0xFD5E2, 24))
    meta = archive[offsets[2] : offsets[3]]
    if len(meta) != sizes[2] or offsets[3] - offsets[2] != sizes[2]:
        raise ValueError("Idle metadata does not match the original size table")
    pos, shapes, decoded_size = 0, [], 0
    while pos + 6 <= len(meta) and meta[pos : pos + 6] != bytes(6):
        width, height, hx, hy, bits = struct.unpack_from(">BBbbH", meta, pos)
        shapes.append(
            dict(
                width=width,
                height=height,
                hotspot_x=hx,
                hotspot_y=hy,
                compressed_bits=bits,
            )
        )
        decoded_size += ((width + 3) // 4) * height
        pos += 6
    if meta[pos : pos + 6] != bytes(6) or pos + 6 >= len(meta):
        raise ValueError("Missing idle shape terminator/script count")
    pos += 6
    count, pos = meta[pos], pos + 1
    mapping = read_memory(model, 0xFF314, 64)  # SETUPMSQ/PUTPIECE perspective selector.
    sequences = []
    for index in range(count):
        if pos + 2 > len(meta):
            raise ValueError("Truncated idle script header")
        length, selector = meta[pos : pos + 2]
        deltas = list(meta[pos + 2 : pos + 2 + length])
        if len(deltas) != length or any(d >= len(shapes) for d in deltas):
            raise ValueError("Invalid idle delta list")
        if not selector & 0x80:
            raise ValueError("Idle script has an unresolved non-standing base")
        shape = selector & 0x7F
        states = [
            dict(type=byte & 7, orientation=byte >> 3)
            for byte, value in enumerate(mapping)
            if value == 17 + shape
        ]
        sequences.append(
            dict(
                index=index,
                archive_offset=offsets[2] + pos,
                base_selector=selector,
                standing_shape=shape,
                display_states=states,
                deltas=deltas,
                frames=length + 1,
            )
        )
        pos += 2 + length
    if pos != len(meta):
        raise ValueError("Trailing idle metadata")
    sys.path.insert(0, str(root / "tools/scripts"))
    from decode_archive import Decoder

    decoder = Decoder(archive, offsets[3])
    decoded = decoder.read()
    compressed_end = (decoder.bit + 7) // 8
    if len(decoded) != decoded_size or compressed_end != offsets[3] + sizes[3]:
        raise ValueError(
            "Decoded idle data does not match the original shape/size tables"
        )
    if decoder.bit - (offsets[3] + 8) * 8 != sum(s["compressed_bits"] for s in shapes):
        raise ValueError("Idle compressed frame lengths disagree")
    if decoded != (root / "assets/external_graphics/idle/decoded.2bpp").read_bytes():
        raise ValueError("Saved idle pixels differ from fresh archive decoding")
    words = ("c396", "c392", "d7a2", "d7aa", "d7ae", "d5e2", "d5ea", "d5ee")
    references = {
        word: [
            start + i
            for start, data in code_blocks(model)
            for i in range(4, len(data) - 1, 2)
            if data[i : i + 2] == bytes.fromhex(word)
        ]
        for word in words
    }
    globals_block = next(b for b in model["blocks"] if b["name"] == "A5_globals")
    globals_data = base64.b64decode(globals_block["data"])
    aliases = []
    for offset in range(0, len(globals_data) - 3, 2):
        value = struct.unpack_from(">I", globals_data, offset)[0]
        if 0xFD7A2 <= value < 0xFD7BA or 0xFD5E2 <= value < 0xFD5FA:
            aliases.append(dict(address=globals_block["address"] + offset, value=value))
    duplicates = [
        [a["index"], b["index"]]
        for i, a in enumerate(sequences)
        for b in sequences[i + 1 :]
        if (a["base_selector"], a["deltas"]) == (b["base_selector"], b["deltas"])
    ]
    # HANDLEEV sparse table 0x102ce: count, then displacement/value pairs.
    event_table = read_memory(model, 0x102CE, 32)
    event_count = struct.unpack_from(">H", event_table)[0]
    events = {}
    for i in range(event_count):
        displacement, value = struct.unpack_from(">hH", event_table, 2 + 4 * i)
        events[value] = 0x102D0 + 4 * i + displacement
    null_call = read_memory(model, events[0], 4)
    if null_call[:2] != bytes.fromhex("4eba"):
        raise ValueError("Unexpected null-event branch")
    wrapper_address = events[0] + 2 + struct.unpack_from(">h", null_call, 2)[0]
    wrapper = read_memory(model, wrapper_address, 8)
    if wrapper[:2] != bytes.fromhex("486d") or wrapper[4:6] != bytes.fromhex("4ead"):
        raise ValueError("Unexpected null-event clock wrapper")
    displacement = struct.unpack_from(">H", wrapper, 6)[0]
    helper = next(
        j["file_offset"] for j in model["jump_table"] if j["a5_offset"] == displacement
    )
    clock = read_memory(model, helper, 10)
    if clock[:6] != bytes.fromhex("225f205f20b8") or clock[8:] != bytes.fromhex("4ed1"):
        raise ValueError("Unexpected null-event clock helper")
    null_clock = dict(
        wrapper=wrapper_address,
        helper=helper,
        destination=model["a5"] + struct.unpack_from(">h", wrapper, 2)[0],
        low_memory_address=struct.unpack_from(">H", clock, 6)[0],
    )
    # HANDLEAL dense switch: low/high, default, then eight relative target words.
    handler_table = struct.unpack(">11h", read_memory(model, 0x140BA, 22))
    if handler_table[:2] != (1, 8):
        raise ValueError("Unexpected animation handler switch bounds")
    branches = [0x140C0 + 2 * i + handler_table[3 + i] for i in range(8)]
    handlers = []
    for branch in branches:
        wrapper = read_memory(model, branch, 8)
        if wrapper[:6] != bytes.fromhex("2f2efffc4eba"):
            raise ValueError("Unexpected animation handler wrapper")
        handlers.append(branch + 6 + struct.unpack_from(">h", wrapper, 6)[0])
    return dict(
        scope="Static byte/asset audit; aligned direct-transfer candidates are not a complete call graph",
        sources={
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (
                model_path,
                archive_path,
                root / "source/macintosh/BattleChess.bin",
            )
        },
        code_blocks=len(code_blocks(model)),
        archive=dict(
            metadata_offset=offsets[2],
            compressed_offset=offsets[3],
            compressed_end=compressed_end,
            decoded_bytes=len(decoded),
        ),
        shape_count=len(shapes),
        shapes=shapes,
        sequences=sequences,
        frame_counts=[s["frames"] for s in sequences],
        duplicate_sequences=duplicates,
        references=references,
        initialized_aliases=aliases,
        direct_calls=scan_calls(model),
        null_event_target=events[0],
        null_event_clock=null_clock,
        handler_branches=branches,
        handler_targets=handlers,
        trigger_status="unrecovered",
        limitations="Computed aliases, indirect callers and live selection/time gates remain unresolved; stored scripts do not prove idle execution",
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    output = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else root / "docs/recompilation/idle_evidence.json"
    )
    report = collect(root)
    output.write_text(json.dumps(report, indent=2) + "\n")
    assert json.loads(output.read_text()) == report
    print(
        f"{len(report['sequences'])} idle scripts / {sum(report['frame_counts'])} frames; trigger unrecovered"
    )
