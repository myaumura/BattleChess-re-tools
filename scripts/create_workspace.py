"""Copy the recovery tools into a new private directory outside this repository."""

import argparse
from pathlib import Path
import shutil


def create(destination):
    root = Path(__file__).resolve().parents[1]
    destination = destination.resolve()
    if destination == root or root in destination.parents:
        raise ValueError(
            "The private workspace must be outside the public tools repository"
        )
    if destination.exists():
        raise ValueError(
            "Workspace already exists; choose a new directory to preserve its contents"
        )
    destination.mkdir(parents=True)
    shutil.copytree(
        root / "tools",
        destination / "tools",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    for folder in (
        "source/macintosh",
        "source/system7/fonts",
        "tools/3rd-party",
        "recovered",
        "assets",
        "docs/recompilation",
    ):
        (destination / folder).mkdir(parents=True, exist_ok=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    try:
        destination = create(parser.parse_args().workspace)
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Created private workspace: {destination}")
    print(
        "Supply your own input files there, then run its tools. No original data was copied."
    )
