"""Compare rebuilt 2-bit frames with independently saved recovery PNGs."""

import json
from pathlib import Path
import re
import struct
import sys
import zlib


def check(build):
    root = Path(__file__).resolve().parents[2]
    build = Path(build)
    header = (build / "animation_data.hpp").read_text()

    # Native generation/validation (no original entrypoint): Parse one generated C++ array for
    # comparison with independently recovered assets.
    def table(name):
        body = re.search(r" " + name + r"\[\] = \{(.*?)\};", header).group(1)
        return json.loads("[" + body.replace("{", "[").replace("}", "]") + "]")

    frames, clips = table("animation_frames"), table("animation_clips")
    groups = {name: (first, count) for name, first, count in table("animation_groups")}
    pixels = (build / "animation_pixels.bin").read_bytes()
    manifest = json.loads((root / "assets/external_graphics/manifest.json").read_text())
    checked = 0
    for group in manifest["groups"]:
        for i, seq in enumerate(group["sequences"]):
            first, count = clips[groups[group["name"]][0] + i]
            assert count == len(seq["frames"])
            for j, reference in enumerate(seq["frames"]):
                width, height, hotspot_x, hotspot_y, offset = frames[first + j]
                assert [width, height, hotspot_x, hotspot_y] == [
                    reference[k] for k in ("width", "height", "hotspot_x", "hotspot_y")
                ]
                png = (
                    root / "assets/external_graphics" / reference["png"]
                ).read_bytes()
                assert png[:8] == b"\x89PNG\r\n\x1a\n"
                assert struct.unpack(">II", png[16:24]) == (width, height)
                rows = zlib.decompress(png[41:-16])
                for y in range(height):
                    row = rows[y * (1 + 4 * width) : (y + 1) * (1 + 4 * width)]
                    assert row[0] == 0
                    for x in range(width):
                        value = pixels[offset + y * width + x]
                        expected = (
                            (0, 0, 0, 255)
                            if value == 1
                            else (255, 255, 255, 0 if value == 3 else 255)
                        )
                        assert tuple(row[1 + 4 * x : 5 + 4 * x]) == expected, (
                            group["name"],
                            i,
                            j,
                            x,
                            y,
                        )
                checked += 1
    assert checked == 4424
    extra = json.loads((build / "extra_animation/manifest.json").read_text())
    assert sum(len(g["sequences"]) for g in extra["groups"]) == 206
    assert len(extra["combat"]) == 36
    print(
        f"{checked} rebuilt frames match saved recovery PNGs; 206 additional sequences validated"
    )


if __name__ == "__main__":
    check(Path(sys.argv[1]))
