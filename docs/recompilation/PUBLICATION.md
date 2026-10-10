# Source repositories and private data

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

## Published projects

| Project | Contents | Current guide |
|---|---|---|
| [BattleChess](https://github.com/myaumura/BattleChess) | Native C11/C++17/SDL3 source, configuration and C/C++ tests | [Build and run](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md) |
| [BattleChess-re-tools](https://github.com/myaumura/BattleChess-re-tools) | Python extraction, pack preparation, checks and authored research docs | [Preparation and launch](../PREPARE_DATA.md) |

The native project's existing MIT license is retained; the tools repository also
uses MIT. Those licenses cover the repositories' source and authored text.
Original game/System files, extracted fonts and media, analysis dumps, generated
packs and data-dependent executables are outside the source distribution.

## Permanent locations

Use the [permanent folder layout](../PREPARE_DATA.md#preparation-flow):

```text
~/Games/BattleChess/
  repos/BattleChess/           native source checkout
  repos/BattleChess-re-tools/  tools source checkout
  originals/                  supplied disk and System files
  data/prepared-data/         generated pack
```

[`prepare_game_data.py`](../../scripts/prepare_game_data.py) accepts the original
disk and System container and creates a new prepared directory. It rejects an
existing destination, records input/output checksums and reopens generated files.
The native application builds and runs against that pack using `BC_DATA_DIR`.
See the [data contract](https://github.com/myaumura/BattleChess/blob/main/docs/DATA.md)
for its compilation/runtime boundary.

## Private recovery workbench

The original recovery workbench retains canonical inputs, Ghidra projects,
decompiler exports, decoded assets, evidence captures, the independent learning
port and Swift remake. Its `recompilation/` symlink points to the native sibling
checkout; historical records use that layout. Public clones do not require it to
prepare a launch pack.

## Source-only isolation check

[`check_publication.py`](../../scripts/check_publication.py) checks this tools tree
for excluded artifacts. [`standalone_check.py`](../../tools/recompilation_checks/standalone_check.py)
checks native source isolation using the private workbench's `recompilation/`
link; it is a workbench check, not an input required for pack preparation.
Current native build and sanitizer commands are in the
[build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md#checks-and-troubleshooting).

## Historical separation verification — 2026-10-03

- Public inventory: 77 source/configuration/documentation files; tools contain
  only `build.sh` and `run.sh`. No original binaries, fonts, media, resource
  headers, Ghidra files, or recovery generators occur in the public source tree.
- Isolated source-only build: 17/17 CTests passed with ASan/UBSan; the copied
  project built through its script from an unrelated working directory and a
  path containing spaces. Empty and incomplete app-data diagnostics passed.
- Final native app build: 24/24 CTests passed with ASan/UBSan in 41.54 seconds.
  This includes 113 animation cases, native smoke, and serial PTY integration.
- All eight relocated recovery checks passed. Strict saved original-frame
  comparison matched 163,370 visible pixels, excluding the recorded cursor.
- Run script passed native smoke from the parent directory with a relative
  `BC_DATA_DIR`, confirming build/runtime path agreement.
- All 6,394 reopened pack files match a fresh regeneration. The five generated
  catalogs/pixel outputs also match the preceding native build byte for byte.
- Preparation rejects existing outputs and destinations inside the public
  source tree without modifying the saved pack.
- Relocation rechecked all 328 baseline files: 295 unchanged, 33 source/tool/doc
  files differed. Existing canonical source, recovered model/code, Ghidra and
  user-owned cross-port files remain byte-identical. Concurrent native source
  edits were preserved rather than reverted. Recovery docs/tool paths and the
  data-loading adapter account for this task's changes.
- Shell syntax checks passed. The private Linux Docker wrapper was updated,
  but no new Linux/container or original Macintosh runtime session was run.

The old workbench build is archived; its CMake cache refers to the historical
layout. Use the public build scripts for current builds. The original/runtime
fidelity limitations remain unchanged by this separation.

Private verification records include `publication_validation/` and
`relocation_paths.json`; they are not distributed with this tools repository.
The baseline digest manifest records paths before relocation.

## Default core build after an app configuration — 2026-10-03

`tools/build.sh` now selects `BC_BUILD_APP=OFF` before forwarding caller options.
This keeps the default build independent of private data even when the CMake
cache previously enabled the application. An explicit `-DBC_BUILD_APP=ON` still
wins. The public README describes that behavior.

The relocated `tools/recompilation_checks/standalone_check.py` now seeds a stale
app configuration before invoking the default build. That regression failed
before the one-argument fix and passed afterward: 17/17 isolated core tests with
ASan/UBSan (7.54 seconds). The explicit app build also passed 24/24 tests with
ASan/UBSan (30.27 seconds). Source-only inventory and missing-data checks passed.
The public source now contains 76 files after the earlier isolation-test move.
No game logic or asset pack changed in that follow-up. These inventories and
test counts describe that dated source version; current status is maintained in
the native roadmap.
