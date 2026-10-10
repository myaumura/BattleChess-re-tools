"""Reproduce the original assembly call-site index, including stack arguments."""

import json
from pathlib import Path
import re
import sys

TARGETS = {110: "DOWALK_0xd3bc", 156: "STARTANI_0x133c4", 159: "WAITANIM_0x131f2"}


def collect(lines):
    """Keep each matching call and the fourteen preceding instructions."""
    instructions = []
    calls = []
    for line in lines:
        if not re.match(r"^[0-9A-F]{8} ", line):
            continue
        match = re.search(r"\bjsr\s+.*?/\* export_(110|156|159) \*/", line)
        if match:
            calls.append(
                dict(
                    call_address="0x" + line[:8].lower(),
                    callee=TARGETS[int(match[1])],
                    instruction=line,
                    preceding_instructions=instructions[-14:],
                )
            )
        instructions.append(line)
    return dict(
        source="tools/3rd-party/dump.log",
        scope="All disassembled export_110, export_156, export_159 calls; DOWALK local recursive calls documented separately.",
        calls=calls,
    )


def generate(root, output):
    value = collect((root / "tools/3rd-party/dump.log").read_text().splitlines())
    output.write_text(json.dumps(value, indent=2) + "\n")
    assert json.loads(output.read_text()) == value
    print(f'{len(value["calls"])} original animation call sites')


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    output = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else root / "docs/recompilation/animation_calls.json"
    )
    generate(root, output)
