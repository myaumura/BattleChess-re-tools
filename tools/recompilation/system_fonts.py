"""Extract the two plain bitmap strikes from a supplied System MacBinary resource fork."""

import argparse
import hashlib
from pathlib import Path
import struct
from bitmap_fonts import span, unpack, nfnt


# Native extraction (no Battle Chess entrypoint): enumerate bounded MacBinary resources.
def resources(binary):
    data_size, resource_size = unpack("II", binary, 83)
    fork = span(binary, 128 + ((data_size + 127) // 128) * 128, resource_size)
    data_offset, map_offset, data_length, map_length = unpack("IIII", fork)
    data = span(fork, data_offset, data_length)
    mapping = span(fork, map_offset, map_length)
    types, names = unpack("HH", mapping, 24)
    result = {}
    for i in range(unpack("H", mapping, types)[0] + 1):
        kind, count, references = unpack("4sHH", mapping, types + 2 + i * 8)
        for j in range(count + 1):
            entry = span(mapping, types + references + j * 12, 12)
            ident, name_offset = unpack("hH", entry)
            offset = int.from_bytes(entry[5:8], "big")
            value = span(data, offset + 4, unpack("I", data, offset)[0])
            name = ""
            if name_offset != 65535:
                name_start = names + name_offset
                length = span(mapping, name_start, 1)[0]
                name = span(mapping, name_start + 1, length).decode("mac_roman")
            if (kind, ident) in result:
                raise ValueError("Duplicate System resource")
            result[kind, ident] = (name, value)
    return result


# Native recovery of System7 CDEF0: decode its dcmp2 word dictionary from the same System file.
def control_code(binary):
    table = resources(binary)
    compressed = table[b"CDEF", 0][1]
    magic, header, version, flags, length, ident, extra, p1, p2 = unpack(
        "IHBBIHHBB", compressed
    )
    if (
        (magic, header, version, flags, ident, p1, p2)
        != (0xA89F6572, 18, 9, 1, 2, 0, 2)
        or length > 1048576
        or length % 2
    ):
        raise ValueError("Unsupported CDEF0 compression")
    decompressor = table[b"dcmp", 2][1]
    prefix = bytes.fromhex("000000084eba206e4e75000c00047000")
    start = decompressor.find(prefix)
    if start < 0 or decompressor.find(prefix, start + 1) >= 0:
        raise ValueError("Missing or ambiguous original dcmp2 dictionary")
    dictionary = unpack("256H", decompressor, start)
    output = bytearray()
    offset = header
    while len(output) < length:
        flags = span(compressed, offset, 1)[0]
        offset += 1
        for bit in range(8):
            if len(output) == length:
                break
            if flags & (128 >> bit):
                index = span(compressed, offset, 1)[0]
                output.extend(struct.pack(">H", dictionary[index]))
                offset += 1
            else:
                output.extend(span(compressed, offset, 2))
                offset += 2
    if offset != len(compressed):
        raise ValueError("Trailing CDEF0 compressed data")
    return bytes(output)


# Native extraction (no Battle Chess entrypoint): resolve face/size through original FOND associations.
def extract(source, output):
    binary = Path(source).read_bytes()
    table = resources(binary)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    print("System MacBinary SHA256=" + hashlib.sha256(binary).hexdigest())
    _, icon = table[b"ICON", 0]
    if len(icon) != 128:
        raise ValueError("Unexpected System stop icon")
    target = output / "Stop.ICON"
    if target.exists() and target.read_bytes() != icon:
        raise ValueError("Refusing to replace a different stop icon")
    target.write_bytes(icon)
    for family, name, size in [(0, "Chicago", 12), (3, "Geneva", 9)]:
        actual_name, fond = table[b"FOND", family]
        if actual_name != name:
            raise ValueError("Unexpected System family name")
        entries = [
            unpack("HHh", fond, 54 + i * 6) for i in range(unpack("H", fond, 52)[0] + 1)
        ]
        matches = [
            ident for point, style, ident in entries if point == size and style == 0
        ]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous plain bitmap strike")
        ident = matches[0]
        _, data = table[b"NFNT", ident]
        nfnt(data)
        target = output / f"{name}{size}.NFNT"
        if target.exists() and target.read_bytes() != data:
            raise ValueError(f"Refusing to replace a different font: {target}")
        target.write_bytes(data)
        print(
            f"{target.name}: FOND{family}, NFNT{ident}, SHA256={hashlib.sha256(data).hexdigest()}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system_macbinary")
    parser.add_argument("output_directory")
    parser.add_argument(
        "--control-code", help="Optional path for decoded CDEF0 investigation input"
    )
    args = parser.parse_args()
    extract(args.system_macbinary, args.output_directory)
    if args.control_code:
        Path(args.control_code).write_bytes(
            control_code(Path(args.system_macbinary).read_bytes())
        )
