"""The build must reject malformed or missing asset references."""

from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/recompilation"))
from catalog import generate


def check():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "frame.png").write_bytes(b"placeholder")
        frame = dict(png="frame.png", width=10, height=12, hotspot_x=-2, hotspot_y=4)
        manifest = root / "manifest.json"
        output = root / "assets.hpp"

        # Native generation/validation (no original entrypoint): Write a manifest fixture for
        # catalog rejection checks.
        def write(value):
            manifest.write_text(
                json.dumps(
                    dict(
                        groups=[dict(name="example", sequences=[dict(frames=[value])])]
                    )
                )
            )

        write(frame)
        generate(manifest, output)
        expected = output.read_bytes()
        for change in (
            {"png": "../outside.png"},
            {"png": "/absolute.png"},
            {"png": "missing.png"},
            {"width": 0},
            {"height": "bad"},
        ):
            write(frame | change)
            try:
                generate(manifest, output)
            except ValueError:
                pass
            else:
                raise AssertionError(f"accepted {change}")
            assert output.read_bytes() == expected
    print("Catalog validation passed")


if __name__ == "__main__":
    check()
