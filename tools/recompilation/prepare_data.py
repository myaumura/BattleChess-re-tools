"""Prepare local native data without putting original resources in the source repo."""

from pathlib import Path
import argparse
import hashlib
import json
import shutil

from animation_assets import generate as animation
from bitmap_fonts import generate as fonts
from catalog import generate as catalog
from combat_tables import generate as combat
from original_tables import generate as tables


def prepare(output):
    root = Path(__file__).resolve().parents[2]
    output = output.resolve()
    public = (root / "recompilation").resolve()
    if output == public or public in output.parents:
        raise ValueError(
            "Keep prepared original data outside the public source repository"
        )
    output.mkdir(parents=True, exist_ok=False)
    font_inputs = root / "source/system7/fonts"
    catalog(root / "assets/external_graphics/manifest.json", output / "assets.hpp")
    tables(root, output / "original.hpp")
    fonts(
        output / "bitmap_fonts.hpp",
        font_inputs / "Geneva9.NFNT",
        font_inputs / "Chicago12.NFNT",
    )
    extra = output / "extra_animation"
    extra.mkdir()
    combat(extra)
    animation(root, output, extra / "manifest.json")
    archive = (root / "source/macintosh/extracted/ALLCANM1.data").read_bytes()
    book = archive[0x24FAD : 0x24FAD + 32000]
    assert len(book) == 32000
    (output / "opening_book.bin").write_bytes(book)
    shutil.copytree(root / "assets", output / "assets")
    # Reopen the saved pack and retain checksums for reproducibility checks.
    files = {
        str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob("*"))
        if p.is_file()
    }
    (output / "checksums.json").write_text(json.dumps(files, indent=2) + "\n")
    assert json.loads((output / "checksums.json").read_text()) == files
    print(f"Prepared {len(files)} data files in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", type=Path, help="New directory outside the public source tree"
    )
    prepare(parser.parse_args().output)
