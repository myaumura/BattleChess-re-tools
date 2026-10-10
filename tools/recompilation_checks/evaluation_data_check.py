"""Compare every embedded evaluation constant with the recovered original DATA bytes."""

import base64
import json
from pathlib import Path
import re
import struct


# Native verification (no original entry point): decode the original A5 block and check
# material, positional, mask, and direction tables independently of the evaluator's logic.
def main():
    root = Path(__file__).resolve().parents[2]
    model = json.loads((root / "recovered/recovery_model.json").read_text())
    block = next(block for block in model["blocks"] if block["name"] == "A5_globals")
    data = base64.b64decode(block["data"])
    source = (root / "recompilation/lib/evaluation.c").read_text()
    for name, address, count in (
        ("material", 0xFED70, 7),
        ("centrality", 0xFED7E, 8),
        ("pawn_rank", 0xFED8E, 8),
        ("passed_rank", 0xFED9E, 8),
        ("pawn_file", 0xFEDAE, 8),
        ("castle_bonus", 0xFEDBE, 2),
        ("attack_rank", 0xFEDC2, 8),
        ("file_mask", 0xFEDD2, 8),
        ("rays", 0xF99E0, 8),
        ("knights", 0xF99F0, 8),
    ):
        match = re.search(rf"\b{name}\[\d+\]\s*=\s*\{{([^}}]+)\}}", source)
        assert match, name
        native = tuple(int(value.strip()) for value in match[1].split(","))
        original = struct.unpack_from(f">{count}h", data, address - block["address"])
        assert native == original, (name, native, original)
    print("All 10 native evaluation tables match original A5 DATA words")


if __name__ == "__main__":
    main()
