"""Build a relocatable analysis model from verified original bytes, never the original project."""

import base64
import json
import re
import struct
from pathlib import Path

from analyze_dump import analyze, read_source

A5 = 0x100000
STRINGS = 0x200000


def prepare(root):
    memory, labels, _ = read_source(root)
    report = analyze(root)
    resources = {(r["type"], r["id"]): r for r in report["resources"]}

    def read(address, count):
        return bytes(memory[i] for i in range(address, address + count))

    blocks = []
    relocations = []

    def relocate(data, resource, destination_base):
        for i in range(resource["offset"], resource["offset"] + resource["size"], 2):
            value = struct.unpack(">H", read(i, 2))[0]
            offset = struct.unpack(">h", struct.pack(">H", value & 0xFFFE))[0]
            base = STRINGS if value & 1 else A5
            index = offset if destination_base != A5 else len(data) + offset
            assert 0 <= index <= len(data) - 4
            old = struct.unpack_from(">I", data, index)[0]
            new = (old + base) & 0xFFFFFFFF
            struct.pack_into(">I", data, index, new)
            relocations.append(
                dict(address=destination_base + offset, old=old, new=new)
            )

    def block(name, address, data, executable=False):
        blocks.append(
            dict(
                name=name,
                address=address,
                executable=executable,
                data=base64.b64encode(data).decode(),
            )
        )

    data, zero = resources["DATA", 0], resources["ZERO", 0]
    expanded = bytearray()
    cursor = zero["offset"]
    for i in range(data["offset"], data["offset"] + data["size"], 2):
        value = read(i, 2)
        expanded.extend(value)
        if value == b"\0\0":
            expanded.extend(bytes(struct.unpack(">H", read(cursor, 2))[0]))
            cursor += 2
    assert len(expanded) == report["a5_below"]
    relocate(expanded, resources["DREL", 0], A5)
    block("A5_globals", A5 - len(expanded), expanded)

    starts = set(j["file_offset"] for j in report["jump_table"])
    code_ranges = []
    code_buffers = {}
    for (kind, resource_id), resource in resources.items():
        if kind != "CODE" or resource_id == 0:
            continue
        start, size = resource["offset"], resource["size"]
        payload = bytearray(read(start, size))
        code_buffers[resource_id] = (start, bytes(payload))
        code_ranges.append((start + 4, start + size))
        for position in range(4, size - 3, 2):
            # LINK A6 with an even, nonpositive frame size.
            if payload[position : position + 2] == b"\x4e\x56":
                frame = struct.unpack_from(">h", payload, position + 2)[0]
                if frame <= 0 and frame % 2 == 0:
                    starts.add(start + position)
        if ("CREL", resource_id) in resources:
            relocate(payload, resources["CREL", resource_id], start)
            payload[0] &= 0x7F
        block(f"CODE_{resource_id}", start, payload, True)

    # Map original STRS bytes, including the eight omissions in the text exports.
    strings = resources["STRS", 0]
    begin = strings["offset"]
    end = begin + strings["size"]
    position = begin
    while position < end:
        if position not in memory:
            position += 1
            continue
        first = position
        while position < end and position in memory:
            position += 1
        block(
            f"STRS_{first - begin:x}",
            STRINGS + first - begin,
            read(first, position - first),
        )

    table = bytearray(report["a5_above"])
    for jump in report["jump_table"]:
        struct.pack_into(">HI", table, jump["a5_offset"], 0x4EF9, jump["file_offset"])
    block("A5_jump_table", A5, table, True)

    dense_switches = []
    sparse_switches = []
    calls = []
    jump_map = {j["a5_offset"]: j["file_offset"] for j in report["jump_table"]}
    for start, data in code_buffers.values():
        end = start + len(data)
        for i in range(4, len(data) - 3, 2):
            if data[i : i + 2] not in (b"\x4e\xad", b"\x4e\xed"):
                continue
            displacement = struct.unpack_from(">H", data, i + 2)[0]
            if displacement not in jump_map:
                continue
            calls.append(
                dict(
                    address=start + i,
                    target=jump_map[displacement],
                    is_jump=data[i : i + 2] == b"\x4e\xed",
                )
            )
            if displacement in (0x2A, 0x32):
                table_start = start + i + 4
                count = struct.unpack(">H", read(table_start, 2))[0] + 1
                width = 2 if displacement == 0x2A else 4
                table_end = table_start + 2 + count * (2 + width) - width
                if count > 256 or table_end > end:
                    continue
                positions = list(range(table_start + 2, table_end, 2 + width))
                targets = [p + struct.unpack(">h", read(p, 2))[0] for p in positions]
                if not all(start + 4 <= t < end and t % 2 == 0 for t in targets):
                    continue
                sparse_switches.append(
                    dict(
                        address=start + i,
                        table_start=table_start,
                        table_end=table_end,
                        width=width,
                        targets=targets,
                        values=[
                            int.from_bytes(read(p + 2, width), "big", signed=True)
                            for p in positions[:-1]
                        ],
                    )
                )
                continue
            if displacement != 0x3A:
                continue
            table_start = start + i + 4
            low, high = struct.unpack(">hh", read(table_start, 4))
            if not 0 <= high - low < 256:
                continue
            positions = list(
                range(table_start + 4, table_start + 8 + 2 * (high - low), 2)
            )
            targets = [p + struct.unpack(">h", read(p, 2))[0] for p in positions]
            if not all(start + 4 <= t < end and t % 2 == 0 for t in targets):
                continue
            dense_switches.append(
                dict(
                    address=start + i,
                    table_start=table_start,
                    table_end=positions[-1] + 2,
                    low=low,
                    high=high,
                    targets=targets,
                )
            )

    # Never seed apparent LINK words inside known name strings or switch tables.
    noncode = [(l["file_offset"], l["file_offset"] + 8) for l in labels]
    noncode += [
        (s["table_start"], s["table_end"]) for s in dense_switches + sparse_switches
    ]
    starts = sorted(
        a for a in starts if not any(low <= a < high for low, high in noncode)
    )
    # These names are hypotheses based on the immediately preceding entry seed.
    # Include the address to preserve colliding/truncated original names.
    names = {}
    for label in labels:
        preceding = [
            a
            for a in starts
            if a < label["file_offset"]
            and any(low <= a < label["file_offset"] < high for low, high in code_ranges)
        ]
        if preceding:
            address = max(preceding)
            names[str(address)] = f"{label['text']}_{address:08x}"
    names.update(
        {str(0x1DE08): "runtime_start_0001de08", str(0x163F2): "SEARCH_000163f2"}
    )
    traps = []
    for line in (root / "tools/3rd-party/dump.log").read_text().splitlines():
        match = re.match(r"^([0-9A-F]{8})  ([A][0-9A-F]{3}) +syscall +([^/]+)", line)
        if match and any(low <= int(match[1], 16) < high for low, high in code_ranges):
            traps.append(
                dict(
                    address=int(match[1], 16),
                    opcode=int(match[2], 16),
                    description=match[3].strip(),
                )
            )
    return dict(
        a5=A5,
        strings=STRINGS,
        blocks=blocks,
        starts=starts,
        names=names,
        jump_table=report["jump_table"],
        relocations=relocations,
        calls=calls,
        dense_switches=dense_switches,
        sparse_switches=sparse_switches,
        traps=traps,
        labels=labels,
    )


if __name__ == "__main__":
    folder = Path(__file__).resolve().parents[2]
    model = prepare(folder)
    assert len(model["sparse_switches"]) == 15
    first = model["sparse_switches"][0]
    assert (first["address"], first["table_end"]) == (0x280A, 0x281E)
    assert first["values"] == [162, 161, 169]
    assert first["targets"] == [0x281E, 0x2836, 0x2872, 0x287C]
    assert 0x257C in model["starts"] and 0x163F2 in model["starts"]
    assert any(
        s["address"] == 0x178C0 and (s["low"], s["high"]) == (1, 6)
        for s in model["dense_switches"]
    )
    output = folder / "recovered"
    output.mkdir(exist_ok=True)
    path = output / "recovery_model.json"
    path.write_text(json.dumps(model, indent=2) + "\n")
    assert json.loads(path.read_text()) == model
    # Minimal input lets headless create a program; loader replaces this block.
    (output / "seed.bin").write_bytes(b"\x4e\x75")
    print(
        f"Verified model: {len(model['starts'])} entry seeds, "
        f"{len(model['dense_switches'])} dense switches, "
        f"{len(model['relocations'])} relocations."
    )
