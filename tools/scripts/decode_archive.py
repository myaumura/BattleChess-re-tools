"""Battle Chess serialized Huffman blocks; translated from 0x8724/0x891c.

``decode(data, offset=0)`` returns exactly the header-declared output bytes.
``Decoder`` retains bit position for callers that consume an animation in chunks.
No third-party codec, guessed bytes, or asset-specific substitution is used.
"""

import struct


class Decoder:
    def __init__(self, data, offset=0):
        if offset < 0 or offset + 10 > len(data):
            raise ValueError("truncated Huffman header")
        self.data = data
        self.offset = offset
        self.size, self.header_word = struct.unpack_from(">II", data, offset)
        if self.size > 64 * 1024 * 1024:
            raise ValueError("implausible decoded length")
        self.bit = (offset + 8) * 8
        self.remaining = self.size
        symbols = set()

        def tree(depth=0):
            if depth > 16:
                raise ValueError("Huffman code exceeds game's 16-bit table")
            if self.bits(1):
                symbol = self.bits(8)
                if symbol in symbols:
                    raise ValueError("duplicate Huffman symbol")
                symbols.add(symbol)
                return symbol
            left = tree(depth + 1)
            # 0x87BE consumes a structural marker before the right subtree.
            self.bits(1)
            return (left, tree(depth + 1))

        self.tree = tree()
        self.tree_end_bit = self.bit
        self.symbols = len(symbols)

    def bits(self, count):
        value = 0
        for _ in range(count):
            if self.bit >= len(self.data) * 8:
                raise ValueError("truncated Huffman bitstream")
            value = (value << 1) | (
                (self.data[self.bit // 8] >> (7 - self.bit % 8)) & 1
            )
            self.bit += 1
        return value

    def read(self, count=None):
        if count is None:
            count = self.remaining
        if count < 0:
            raise ValueError("negative decode count")
        count = min(count, self.remaining)
        output = bytearray()
        for _ in range(count):
            node = self.tree
            while isinstance(node, tuple):
                node = node[self.bits(1)]
            output.append(node)
        self.remaining -= count
        return bytes(output)


def decode(data, offset=0):
    return Decoder(data, offset).read()


def self_check():
    # Two leaves: 0,A ; discarded right marker 1 ; 1,B. Then ABBA.
    bits = "0" + "1" + format(65, "08b") + "1" + "1" + format(66, "08b") + "0110"
    packed = int(bits.ljust((len(bits) + 7) // 8 * 8, "0"), 2).to_bytes(
        (len(bits) + 7) // 8, "big"
    )
    block = struct.pack(">II", 4, 0) + packed
    assert decode(block) == b"ABBA"
    decoder = Decoder(block)
    assert decoder.read(1) + decoder.read() == b"ABBA"
    assert decoder.read() == b""
    try:
        decode(block[:10])
    except ValueError:
        pass
    else:
        raise AssertionError("truncation accepted")


if __name__ == "__main__":
    self_check()
    print("Huffman self-check passed")
