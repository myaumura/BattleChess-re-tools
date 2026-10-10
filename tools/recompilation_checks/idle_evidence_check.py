"""Check original idle bytes and the limits of the direct-call audit."""

from pathlib import Path
import base64
import json
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "tools/recompilation"))
from idle_evidence import collect, scan_calls


def check():
    report = collect(root)
    assert (
        report.get("frame_counts") == [29, 28, 28, 29] + [13] * 8
    ), "Expected the twelve original idle scripts, including repeated entries"
    assert report["archive"]["metadata_offset"] == 26903
    assert report["archive"]["compressed_offset"] == 27332
    assert report["archive"]["compressed_end"] == 37520
    assert report["archive"]["decoded_bytes"] == 22235
    assert report["shape_count"] == 32
    assert report["duplicate_sequences"] == [[4, 8], [5, 9], [6, 10], [7, 11]]
    assert [s["standing_shape"] for s in report["sequences"]] == [0, 1, 2, 3] * 3
    assert [s["display_states"] for s in report["sequences"]] == [
        [{"type": 1, "orientation": orientation}]
        for _ in range(3)
        for orientation in (1, 3, 5, 7)
    ]
    assert report["references"]["c396"] == [0x117B2, 0x1187C, 0x1190C]
    assert report["references"]["c392"] == [0x117DA, 0x1188A, 0x11918]
    for word in ("d7aa", "d7ae", "d5ea", "d5ee"):
        assert report["references"][word] == []
    assert report["initialized_aliases"] == []
    calls = report["direct_calls"]
    assert len(calls["STARTANI"]) == 5
    assert len(calls["WAITANIM"]) == 59
    assert all(
        0xD3BC <= c["address"] < 0xE5FE
        for name in ("STARTANI", "WAITANIM")
        for c in calls[name]
    )
    assert [c["address"] for c in calls["ACTIVATE"]] == [
        0x133BC,
        0x137B0,
        0x1382C,
        0x13FA2,
        0x141C6,
    ]
    assert [c["address"] for c in calls["SETUPSEQ"]] == [0x12878, 0x12DE4, 0x12E64]
    assert report["null_event_target"] == 0x102EE
    assert report["null_event_clock"] == {
        "wrapper": 0x103B2,
        "helper": 0x1D6DA,
        "destination": 0xFF198,
        "low_memory_address": 0x20C,
    }
    assert report["handler_targets"] == [
        0x14244,
        0x151BC,
        0x1553C,
        0x14576,
        0x155F2,
        0x1508C,
        0x14E4A,
        0x147A2,
    ]
    assert report["trigger_status"] == "unrecovered"
    # A future direct caller must appear; include signed backward PC transfers and
    # a truncated instruction. Aligned embedded data remains a stated audit limit.
    probe = {
        "blocks": [
            {
                "name": "CODE_probe",
                "address": 0xD3AC,
                "data": base64.b64encode(
                    bytes.fromhex(
                        "4ead0022 4ead0022 4eba0006 4eb9000133c4 61fc 6100fffa 4eba"
                    )
                ).decode(),
            }
        ],
        "jump_table": [{"a5_offset": 0x22, "file_offset": 0xD3BC}],
    }
    detected = scan_calls(probe)
    assert detected["DOWALK"] == [
        {"address": 0xD3B0, "kind": "JSR A5"},
        {"address": 0xD3B4, "kind": "JSR PC"},
        {"address": 0xD3BE, "kind": "BSR"},
        {"address": 0xD3C0, "kind": "BSR"},
    ]
    assert detected["STARTANI"] == [{"address": 0xD3B8, "kind": "JSR absolute"}]
    with tempfile.TemporaryDirectory(prefix="bc-idle-evidence-") as directory:
        output = Path(directory) / "idle.json"
        subprocess.run(
            [
                sys.executable,
                str(root / "tools/recompilation/idle_evidence.py"),
                str(output),
            ],
            cwd=directory,
            check=True,
        )
        assert json.loads(output.read_text()) == report
    print("Twelve idle scripts and the bounded direct-call audit verified")


if __name__ == "__main__":
    check()
