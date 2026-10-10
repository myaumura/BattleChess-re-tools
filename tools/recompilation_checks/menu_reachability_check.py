"""Check the recovered Macintosh menu route, without inventing animation or RNG calls."""

import base64
import json
from pathlib import Path


# Native source-evidence check (no original entrypoint): verify menu dispatch, button
# producers and generic menu gate against the recovered original machine bytes.
def check(root):
    model = json.loads((root / "recovered/recovery_model.json").read_text())
    blocks = [(b["address"], base64.b64decode(b["data"])) for b in model["blocks"]]

    # Native adapter: read original bytes from the recovery model's mapped code blocks.
    def original(address, size):
        for start, data in blocks:
            if start <= address and address + size <= start + len(data):
                return data[address - start : address - start + size]
        raise AssertionError(hex(address))

    expected = {
        0x102B0: "426dadd8",  # clear Macintosh button state
        0x102C0: "70013b40add8",  # Button() true -> 1
        0x1039C: "426dadd8",  # inactive window -> 0
        0x1046A: "70013b40add8",  # content click -> 1
        0x10322: "a93e",  # MenuKey
        0x103F6: "a93d",  # MenuSelect
        0x10328: "4eba0232",  # -> HANDLEME 0x1055c
        0x10402: "4eba0158",  # -> HANDLEME 0x1055c
        0x291C: "4a6df0aa",  # pending Macintosh command before GETMSG
        0x2928: "426df0aa",
        0x266C: "426dadb6",  # generic menu mode initially off
        0x2A54: "70011b40adb8",  # generic subtype3 -> secondary button flag
        0x2C08: "4a2dadb8",  # generic menu entry requires that flag
        0x2C7C: "70013b40adb6",  # only generic-menu enable store
        0x4956: "302dadde",  # previous button state
        0x4972: "302dadd8",  # current button state
        0x499E: "7002c06efffe",  # subtype includes selected button mask bit1
        0x49C0: "0c6e0003fffe",  # loop masks are 1 and2
        0xB602: "4ead0632",  # dormant generic menu's shared RNG draw
    }
    for address, text in expected.items():
        assert original(address, len(text) // 2) == bytes.fromhex(text), hex(address)
    switch = next(s for s in model["dense_switches"] if s["address"] == 0x2964)
    assert switch["low"] == 1 and switch["high"] == 3
    assert switch["targets"] == [0x2CC6, 0x2974, 0x2A6A, 0x2A4E]
    jump = {j["a5_offset"]: j["file_offset"] for j in model["jump_table"]}
    assert jump[0x46A] == 0x10296  # USEPOINT polls actual Macintosh HANDLEEV
    # USEPOINT0x492c: enumerate every normal Macintosh button transition.
    produced = set()
    for before in (0, 1):
        for after in (0, 1):
            for mask in (1, 2):
                if before & mask != after & mask:
                    produced.add(((after >> (mask - 1)) & 1) + (mask & 2))
    assert produced == {0, 1} and 3 not in produced
    # Catch newly discovered direct writers instead of silently widening the claim.
    dump = (root / "tools/3rd-party/dump.log").read_text().splitlines()
    stores = [
        int(line[:8], 16)
        for line in dump
        if ("move.w     [A5 - 0x5228]," in line or "clr.w      [A5 - 0x5228]" in line)
    ]
    assert stores == [0x102B0, 0x102C2, 0x1039C, 0x1046C], stores
    print("Macintosh Toolbox menu route and secondary-button gate verified")


if __name__ == "__main__":
    check(Path(__file__).resolve().parents[2])
