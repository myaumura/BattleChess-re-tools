"""Rebuild cumulative original 2-bit frames, retaining pixels lost by PNG previews."""

import base64
import hashlib
import json
from pathlib import Path
import struct
import sys


# Native generation/validation (no original entrypoint): Rebuild cumulative two-bit frames and
# emit runtime animation assets.
def generate(root, output, extra=None):
    sys.path.insert(0, str(root / "tools/scripts"))
    from extract_external_graphics import pixels, xor_frame

    manifest = json.loads((root / "assets/external_graphics/manifest.json").read_text())
    groups = [(g, root / "assets/external_graphics") for g in manifest["groups"]]
    if extra:
        extra = Path(extra)
        groups += [(g, extra.parent) for g in json.loads(extra.read_text())["groups"]]
    raw_shapes = {}
    for group, directory in groups:
        raw = (
            directory / group.get("decoded_path", group["name"] + "/decoded.2bpp")
        ).read_bytes()
        shapes = []
        for info in group["shapes"]:
            width, height, offset = (
                info[k] for k in ("width", "height", "decoded_offset")
            )
            pixel_count = ((width + 3) // 4) * height
            if offset < 0 or offset + pixel_count > len(raw):
                raise ValueError("Invalid shape span: " + group["name"])
            shapes.append(
                dict(
                    info,
                    values=pixels(raw[offset : offset + pixel_count], width, height),
                )
            )
        raw_shapes[group["name"]] = shapes
    frames, clips, ranges, data = [], [], [], bytearray()

    # Native generation/validation (no original entrypoint): Append a frame descriptor and
    # its indexed pixels to the output buffers.
    def append_frame(shape):
        frames.append(
            [shape[k] for k in ("width", "height", "hotspot_x", "hotspot_y")]
            + [len(data)]
        )
        data.extend(shape["values"])

    for group, _ in groups:
        first_clip = len(clips)
        sequences = group["sequences"]
        if not sequences:
            for shape in raw_shapes[group["name"]]:
                clips.append([len(frames), 1])
                append_frame(shape)
        for sequence in sequences:
            selector = sequence["base_selector"]
            if (
                selector & 0x80
                or group["name"] == "idle"
                or group["name"].startswith("move_")
            ):
                base = "standing"
            else:
                base = (
                    group["name"] + "_bases"
                    if group["name"].startswith("combat_archive1_")
                    else "combat_bases_" + f"{int(group['name'].split('_')[-1])+1:02}"
                )
            current = raw_shapes[base][selector & 0x7F]
            first = len(frames)
            append_frame(current)
            for delta in sequence["deltas"]:
                current = xor_frame(current, raw_shapes[group["name"]][delta])
                append_frame(current)
            clips.append([first, len(frames) - first])
        ranges.append([group["name"], first_clip, len(clips) - first_clip])
    lines = [
        "// Generated original cumulative frames and scripts. Do not edit.",
        "#pragma once",
        "struct GeneratedAnimFrame { int width,height,hx,hy; unsigned offset; };",
        "struct GeneratedAnimClip { unsigned first,count; };",
        "struct GeneratedAnimGroup { const char *name; unsigned first,count; };",
        "struct GeneratedAnimStream { unsigned offset,count; };",
    ]

    # Native generation/validation (no original entrypoint): Serialize animation table
    # entries into the generated C++ header.
    def append_array(kind, name, entries):
        lines.append(
            f"inline constexpr {kind} {name}[] = {{"
            + ",".join("{" + ",".join(json.dumps(x) for x in e) + "}" for e in entries)
            + "};"
        )

    append_array("GeneratedAnimFrame", "animation_frames", frames)
    append_array("GeneratedAnimClip", "animation_clips", clips)
    append_array("GeneratedAnimGroup", "animation_groups", ranges)
    block = next(
        b
        for b in json.loads((root / "recovered/recovery_model.json").read_text())[
            "blocks"
        ]
        if b["name"] == "A5_globals"
    )
    globals_data = base64.b64decode(block["data"])
    script_bytes = []
    for name, address, count in [
        ("combat_selection", 0xFC405, 72),
        ("move_timing", 0xFD372, 144),
    ]:
        position = address - block["address"]
        entries = []
        for _ in range(count):
            end = globals_data.index(255, position) + 1
            entries.append([len(script_bytes), end - position])
            script_bytes.extend(globals_data[position:end])
            position = end
        append_array("GeneratedAnimStream", name, entries)
    from combat_tables import combat_timing

    entries = []
    for stream in combat_timing():
        entries.append([len(script_bytes), len(stream["bytes"])])
        script_bytes.extend(stream["bytes"])
    append_array("GeneratedAnimStream", "combat_timing", entries)
    lines.append(
        "inline constexpr unsigned char animation_script_bytes[] = {"
        + ",".join(map(str, script_bytes))
        + "};"
    )
    from combat_tables import group_for

    lines.append(
        "inline constexpr const char *animation_combat_groups[] = {"
        + ",".join(
            json.dumps(group_for(t, role)[0])
            for role in (False, True)
            for t in range(1, 7)
        )
        + "};"
    )
    for name, address, count, format_code in [
        ("animation_offset_x", 0xFF73C, 8, "h"),
        ("animation_offset_y", 0xFF74C, 8, "h"),
        ("animation_fade_masks", 0xFED2E, 16, "H"),
    ]:
        values = struct.unpack_from(
            ">" + str(count) + format_code, globals_data, address - block["address"]
        )
        lines.append(
            "inline constexpr int "
            + name
            + "[] = {"
            + ",".join(map(str, values))
            + "};"
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "animation_data.hpp").write_text("\n".join(lines) + "\n")
    assert (output / "animation_data.hpp").read_text() == "\n".join(lines) + "\n"
    (output / "animation_pixels.bin").write_bytes(data)
    report = dict(
        sequences=sum(len(g["sequences"]) for g, _ in groups),
        sequence_frames=sum(c[1] for c in clips)
        - sum(len(g["shapes"]) for g, _ in groups if not g["sequences"]),
        groups=len(groups),
        clips=len(clips),
        frames=len(frames),
        pixels=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    (output / "animation_assets.json").write_text(json.dumps(report, indent=2) + "\n")
    assert (output / "animation_pixels.bin").read_bytes() == data
    assert json.loads((output / "animation_assets.json").read_text()) == report
    print(json.dumps(report))


if __name__ == "__main__":
    generate(
        Path(sys.argv[1]).resolve(),
        Path(sys.argv[2]).resolve(),
        sys.argv[3] if len(sys.argv) > 3 else None,
    )
