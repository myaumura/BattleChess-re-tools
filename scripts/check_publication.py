"""Reject media, binary data and symlinks from this source-only repository."""

from pathlib import Path
import re
import sys


def violations(root):
    problems = []
    allowed = {".py", ".java", ".sh", ".md", ".json", ".yml", ".yaml"}
    names = {"LICENSE", "NOTICE", ".gitignore", ".gitattributes"}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in (".git", "__pycache__") for part in relative.parts):
            continue
        if path.is_symlink():
            problems.append(f"{relative}: symlinks are excluded")
        elif path.is_file():
            if path.name == ".DS_Store":
                continue
            if path.name not in names and path.suffix not in allowed:
                problems.append(f"{relative}: unexpected file type")
            data = path.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                problems.append(f"{relative}: non-text content")
                continue
            if "\0" in text or re.search(
                r"data:image/[a-zA-Z0-9.+-]+;base64,[a-zA-Z0-9+/]", text
            ):
                problems.append(f"{relative}: binary or embedded image content")
            if path.suffix == ".json" and path.name != "provenance.json":
                problems.append(
                    f"{relative}: generated JSON belongs in the private workspace"
                )
    return problems


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    problems = violations(root)
    if problems:
        sys.exit("\n".join(problems))
    print(
        "Publication check passed: text sources and documentation only; no media, binaries or symlinks."
    )
