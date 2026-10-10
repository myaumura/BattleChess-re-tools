"""Build the public tree alone; require no original files or recovery toolchain."""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile


def main():
    root = (Path(__file__).resolve().parents[2] / "recompilation").resolve()
    excluded = {".git", "__pycache__", ".DS_Store", ".cache"}
    source_files = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and not any(
            part in excluded or part.startswith("build")
            for part in p.relative_to(root).parts[:-1]
        )
        and p.name not in excluded
    ]
    forbidden = {".png", ".wav", ".bin", ".img", ".nfnt", ".icon", ".2bpp", ".data"}
    permitted_images = {
        "resources/icon.png",
        "resources/perspective.png",
        "resources/flat.png",
        "resources/combat.png",
    }
    assert not any(
        p.suffix == ".py" for p in source_files
    ), "Python remains in the public tree"
    bundled = [
        str(p.relative_to(root))
        for p in source_files
        if p.suffix.lower() in forbidden
        and str(p.relative_to(root)) not in permitted_images
    ]
    generated = {"assets.hpp", "original.hpp", "bitmap_fonts.hpp", "animation_data.hpp"}
    bundled += [str(p.relative_to(root)) for p in source_files if p.name in generated]
    assert not bundled, f"Original/media files remain in public tree: {bundled}"
    assert sorted(p.name for p in (root / "tools").iterdir() if p.is_file()) == [
        "build.sh",
        "run.sh",
    ]
    with tempfile.TemporaryDirectory(prefix="bc-standalone-") as directory:
        isolated = Path(directory) / "public source"
        for source in source_files:
            target = isolated / source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        # An earlier app configuration must not make the default core build need data.
        stale = subprocess.run(
            [
                "cmake",
                "-S",
                str(isolated),
                "-B",
                str(isolated / "build"),
                "-DBC_BUILD_APP=ON",
            ],
            capture_output=True,
            text=True,
        )
        assert stale.returncode and "BC_DATA_DIR" in stale.stderr
        subprocess.run(
            [str(isolated / "tools/build.sh"), "-DBC_SANITIZE=ON"],
            cwd=directory,
            check=True,
        )
        no_data = subprocess.run(
            [str(isolated / "tools/run.sh")],
            cwd=directory,
            env={"PATH": os.environ["PATH"]},
            capture_output=True,
            text=True,
        )
        assert no_data.returncode and "BC_DATA_DIR" in no_data.stderr
        missing = subprocess.run(
            [
                "cmake",
                "-S",
                str(isolated),
                "-B",
                str(Path(directory) / "missing-data"),
                "-DBC_BUILD_APP=ON",
            ],
            capture_output=True,
            text=True,
        )
        assert missing.returncode and "BC_DATA_DIR" in missing.stderr
        empty = Path(directory) / "empty-data"
        empty.mkdir()
        incomplete = subprocess.run(
            [
                "cmake",
                "-S",
                str(isolated),
                "-B",
                str(Path(directory) / "incomplete-data"),
                "-DBC_BUILD_APP=ON",
                f"-DBC_DATA_DIR={empty}",
            ],
            capture_output=True,
            text=True,
        )
        assert incomplete.returncode and "missing assets.hpp" in incomplete.stderr
    print("Standalone source-only build and missing-data diagnostic verified")


if __name__ == "__main__":
    main()
