"""Small invented binary fixtures; no original game or System bytes."""

import struct


def macbinary(name, data=b"", resource=b""):
    encoded = name.encode("mac_roman")
    header = bytearray(128)
    header[1] = len(encoded)
    header[2 : 2 + len(encoded)] = encoded
    struct.pack_into(">II", header, 83, len(data), len(resource))
    return bytes(header) + data + bytes(-len(data) % 128) + resource


def bitmap_font():
    # A and missing glyph: two rows, x locations 0/3/5, bearings 0/0.
    header = struct.pack(">HhhhhhhhHhhhh", 0, 65, 65, 4, -1, -1, 3, 2, 10, 1, 1, 0, 1)
    return (
        header
        + bytes((0xB8, 0, 0x50, 0))
        + struct.pack(">3H", 0, 3, 5)
        + bytes((1, 4, 1, 3))
    )


def resource_file(entries):
    """Build a MacBinary resource map from (type, ID, name, bytes) entries."""
    groups = {}
    data = bytearray()
    names = bytearray()
    for kind, ident, name, payload in entries:
        name_offset = 65535
        if name:
            encoded = name.encode("mac_roman")
            name_offset = len(names)
            names.extend(bytes([len(encoded)]) + encoded)
        groups.setdefault(kind, []).append((ident, name_offset, len(data)))
        data.extend(struct.pack(">I", len(payload)) + payload)
    types = bytearray(struct.pack(">H", len(groups) - 1))
    references = bytearray()
    for kind, records in groups.items():
        types.extend(
            struct.pack(
                ">4sHH", kind, len(records) - 1, 2 + 8 * len(groups) + len(references)
            )
        )
        for ident, name_offset, offset in records:
            references.extend(struct.pack(">hHII", ident, name_offset, offset, 0))
    type_list = types + references
    map_length = 28 + len(type_list) + len(names)
    header = struct.pack(">4I", 256, 256 + len(data), len(data), map_length)
    mapping = (
        header
        + bytes(8)
        + struct.pack(">HH", 28, 28 + len(type_list))
        + type_list
        + names
    )
    return macbinary("System", resource=header + bytes(240) + data + mapping)
