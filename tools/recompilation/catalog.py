"""Compile the existing recovery manifest into a C++ table, without copying media."""

import json
from pathlib import Path
import sys


# Native generation/validation (no original entrypoint): Validate the recovery manifest and
# emit the native frame/clip catalog.
def generate(manifest, output):
    root = manifest.parent.resolve()
    value = json.loads(manifest.read_text())
    frames, clips = [], []
    for group in value["groups"]:
        for index, sequence in enumerate(group["sequences"]):
            first = len(frames)
            for frame in sequence["frames"]:
                path = frame["png"]
                if Path(path).is_absolute() or not (
                    root / path
                ).resolve().is_relative_to(root):
                    raise ValueError(f"frame path escapes asset directory: {path}")
                if not (root / path).is_file():
                    raise ValueError(f"missing frame: {path}")
                numbers = [
                    frame[k] for k in ("width", "height", "hotspot_x", "hotspot_y")
                ]
                if any(type(n) is not int or not -32768 <= n <= 32767 for n in numbers):
                    raise ValueError("invalid frame geometry")
                if numbers[0] <= 0 or numbers[1] <= 0:
                    raise ValueError("empty frame")
                frames.append(
                    "{"
                    + json.dumps("external_graphics/" + path)
                    + ","
                    + ",".join(map(str, numbers))
                    + "}"
                )
            if len(frames) == first:
                raise ValueError("empty sequence")
            clips.append(
                "{"
                + json.dumps(f'{group["name"]}/{index:03}')
                + f",{first},{len(frames)-first}"
                + "}"
            )
    if not clips:
        raise ValueError("no animation clips")
    text = "// Generated from assets/external_graphics/manifest.json; do not edit.\n"
    text += "struct Frame { const char *path; int width, height, hx, hy; };\n"
    text += "struct Clip { const char *name; int first, count; };\n"
    text += "inline constexpr Frame frames[] = {\n" + ",\n".join(frames) + "\n};\n"
    text += "inline constexpr Clip clips[] = {\n" + ",\n".join(clips) + "\n};\n"
    output.write_text(text)
    assert output.read_text() == text
    print(
        f"Catalog: {len(clips)} clips, {len(frames)} frames; media referenced in place"
    )


if __name__ == "__main__":
    generate(Path(sys.argv[1]), Path(sys.argv[2]))
