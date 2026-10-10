"""Transfer original 78-byte saves through MacBinary II; never re-encode the board."""

import argparse
import binascii
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/scripts"))
from extract_disk import split_macbinary


def export_save(data, name):
    """Native transfer adapter for DOSAVE 0x929c..0x92a8: Game/IPBC, empty resource fork."""
    encoded = name.encode("mac_roman")
    if (
        len(data) != 78
        or not 1 <= len(encoded) <= 63
        or b":" in encoded
        or b"\0" in encoded
    ):
        raise ValueError(
            "Expected a 78-byte save and a 1..63-byte Macintosh filename without colon/NUL"
        )
    header = bytearray(128)
    header[1] = len(encoded)
    header[2 : 2 + len(encoded)] = encoded
    header[65:73] = b"GameIPBC"
    struct.pack_into(">II", header, 83, 78, 0)
    header[122:124] = b"\x81\x81"
    struct.pack_into(">H", header, 124, binascii.crc_hqx(header[:124], 0))
    return bytes(header) + data + bytes(50)


def import_save(blob):
    """Native transfer adapter for DOLOAD 0x9100/0x918e: unwrap an identified game data fork."""
    name, data, resource = split_macbinary(blob)
    if (
        len(blob) != 256
        or len(data) != 78
        or resource
        or blob[65:73] != b"GameIPBC"
        or blob[74]
        or blob[82]
        or blob[120:122] != b"\0\0"
    ):
        raise ValueError(
            "Expected a Game/IPBC MacBinary save with a 78-byte data fork and no resource fork"
        )
    if blob[122] not in (0, 129):
        raise ValueError("Unsupported MacBinary version")
    if blob[122] == 129 and (
        blob[123] != 129
        or struct.unpack_from(">H", blob, 124)[0] != binascii.crc_hqx(blob[:124], 0)
    ):
        raise ValueError("Invalid MacBinary II header CRC/version")
    return data


def main():
    """Native CLI: explicit paths, exclusive output and saved-byte verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["export", "import"])
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--name", help="Macintosh filename for export; defaults to source stem"
    )
    args = parser.parse_args()
    created = False
    try:
        with args.source.open("rb") as input_file:
            source = input_file.read(79 if args.command == "export" else 257)
        result = (
            export_save(source, args.name or args.source.stem)
            if args.command == "export"
            else import_save(source)
        )
        with args.output.open("xb") as output:
            created = True
            output.write(result)
        if args.output.read_bytes() != result:
            raise OSError("Saved transfer bytes differ")
    except (OSError, ValueError) as error:
        if created:
            args.output.unlink(missing_ok=True)
        parser.exit(1, f"{error}\n")
    print(f"{args.command}: {args.output} ({len(result)} bytes); saved output verified")


if __name__ == "__main__":
    main()
