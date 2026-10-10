"""Reproduce resource/jump-table findings from the verified original binary.

Run: python3 tools/scripts/analyze_dump.py
Every known text-export byte must match the original before analysis.
An additional Ghidra BattleChess.txt listing is optional.
"""

import json
import re
import struct
from pathlib import Path


def read_dump(root):
    memory = {}
    labels = []

    def add(address, data):
        for offset, value in enumerate(data, address):
            if offset in memory and memory[offset] != value:
                raise ValueError(f"Conflicting exports at {offset:#x}")
            memory[offset] = value

    for line in (root / "tools/3rd-party/dump.log").read_text().splitlines():
        label = re.match(r'^([0-9A-F]{8}).*dc\.b +"([A-Z][A-Z0-9_ ]{7})"$', line)
        if label:
            labels.append(dict(file_offset=int(label[1], 16), text=label[2].rstrip()))
        match = re.match(r"^([0-9A-F]{8})  ((?:[0-9A-F]{4} )*[0-9A-F]{4}) ", line)
        if match:
            add(int(match[1], 16), bytes.fromhex(match[2]))
    utility_bytes = len(memory)
    supplement = root / "source/macintosh/BattleChess.txt"
    text = supplement.read_text() if supplement.exists() else ""
    for line in text.splitlines():
        match = re.match(r"ram:([0-9a-f]{8}) +([0-9a-f]+) +", line)
        if match and len(match[2]) % 2 == 0:
            add(int(match[1], 16), bytes.fromhex(match[2]))

    return memory, labels, utility_bytes


def read_source(root):
    """Verify every exported byte before filling gaps from the original binary."""
    memory, labels, utility_bytes = read_dump(root)
    original = (root / "source/macintosh/BattleChess.bin").read_bytes()
    for address, value in memory.items():
        if address >= len(original) or original[address] != value:
            raise ValueError(f"Original binary disagrees with exports at {address:#x}")
    return dict(enumerate(original)), labels, utility_bytes


def analyze(root):
    memory, labels, utility_bytes = read_source(root)

    def read_bytes(address, size):
        # Missing bytes fail here rather than silently becoming zeros.
        return bytes(memory[i] for i in range(address, address + size))

    def read_u16(address):
        return struct.unpack(">H", read_bytes(address, 2))[0]

    def read_u32(address):
        return struct.unpack(">I", read_bytes(address, 4))[0]

    def read_pascal_string(address):
        return read_bytes(address + 1, memory[address]).decode("mac_roman")

    resource_base = 128 + (read_u32(83) + 127) // 128 * 128
    data_base = resource_base + read_u32(resource_base)
    map_base = resource_base + read_u32(resource_base + 4)
    types = map_base + read_u16(map_base + 24)
    names = map_base + read_u16(map_base + 26)
    resources = []
    for index in range(read_u16(types) + 1):
        entry = types + 2 + index * 8
        kind = read_bytes(entry, 4).decode("mac_roman")
        references = types + read_u16(entry + 6)
        for number in range(read_u16(entry + 4) + 1):
            reference = references + number * 12
            start = data_base + (read_u32(reference + 4) & 0xFFFFFF) + 4
            size = read_u32(start - 4)
            assert data_base <= start <= start + size <= map_base
            name = read_u16(reference + 2)
            resources.append(
                dict(
                    type=kind,
                    id=struct.unpack(">h", read_bytes(reference, 2))[0],
                    offset=start,
                    size=size,
                    name="" if name == 65535 else read_pascal_string(names + name),
                )
            )
    lookup = {(r["type"], r["id"]): r for r in resources}
    code0 = lookup["CODE", 0]["offset"]
    above, below, table_size, table_offset = struct.unpack(">4I", read_bytes(code0, 16))
    jumps = []
    for index in range(table_size // 8):
        offset, opcode, segment, trap = struct.unpack(
            ">4H", read_bytes(code0 + 16 + index * 8, 8)
        )
        assert (opcode, trap) == (0x3F3C, 0xA9F0)
        resource = lookup["CODE", segment]
        assert offset + 4 < resource["size"]
        jumps.append(
            dict(
                a5_offset=table_offset + index * 8 + 2,
                segment=segment,
                segment_offset=offset + 4,
                file_offset=resource["offset"] + 4 + offset,
            )
        )

    # Reproduce startup at 0x1de98: copy words; zero words introduce extra
    # zero-byte counts from ZERO. DBF is entered before the clearing body.
    data = lookup["DATA", 0]
    zero = lookup["ZERO", 0]
    cursor = zero["offset"]
    globals_data = bytearray()
    for address in range(data["offset"], data["offset"] + data["size"], 2):
        value = read_bytes(address, 2)
        globals_data.extend(value)
        if value == b"\0\0":
            globals_data.extend(bytes(read_u16(cursor)))
            cursor += 2
    assert len(globals_data) == below
    assert cursor == zero["offset"] + zero["size"]
    version = lookup["vers", 1]["offset"]
    return dict(
        filename=read_pascal_string(1),
        file_type=read_bytes(65, 4).decode(),
        creator=read_bytes(69, 4).decode(),
        version=read_pascal_string(version + 6),
        version_description=read_pascal_string(version + 7 + memory[version + 6]),
        utility_bytes=utility_bytes,
        combined_bytes=len(memory),
        unknown_offsets=sorted(set(range(max(memory) + 1)) - memory.keys()),
        resource_fork_offset=resource_base,
        resource_fork_size=read_u32(87),
        resource_map_offset=map_base,
        resources=resources,
        embedded_labels=labels,
        a5_above=above,
        a5_below=below,
        jump_table=jumps,
        globals_size=len(globals_data),
        display_piece_map=list(globals_data[below - 0x3C02 : below - 0x3C02 + 7]),
    )


if __name__ == "__main__":
    folder = Path(__file__).resolve().parents[2]
    result = analyze(folder)
    # Regression check against independent evidence in the startup and C export.
    assert result["version"] == "1.0.2"
    assert len(result["jump_table"]) == 249
    assert (
        next(j for j in result["jump_table"] if j["a5_offset"] == 0x21A)["file_offset"]
        == 0x6912
    )
    assert result["globals_size"] == 0x6C54
    output = folder / "dump_analysis.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    assert json.loads(output.read_text()) == result
    print(
        f"Verified {len(result['resources'])} resources, 249 jump entries, "
        f"{result['globals_size']} global bytes; "
        f"{len(result['unknown_offsets'])} bytes remain unknown.\n{output}"
    )
