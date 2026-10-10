# Tool inventory

For normal use, follow [the preparation and launch guide](PREPARE_DATA.md) and run
[prepare_game_data.py](../scripts/prepare_game_data.py). It calls the required
helpers automatically. The paths below identify source files in this repository;
these are reference implementations, not a checklist of extra preparation steps.

See the [reverse-engineering diagrams](WORKFLOW.md) for how the stages connect.
The resulting pack is consumed by [BattleChess](https://github.com/myaumura/BattleChess).

## Extraction and reconstruction

| Source | Purpose / inputs |
|---|---|
| [analyze_dump.py](../tools/scripts/analyze_dump.py) | Verify dump bytes against the MacBinary application; inspect resources, DATA/ZERO and A5 jump entries. Optional supplemental Ghidra listing. |
| [extract_disk.py](../tools/scripts/extract_disk.py) | Extract HFS disk files and both forks using hfsutils; create a missing canonical application or verify an existing one. |
| [prepare_recovery.py](../tools/scripts/prepare_recovery.py) | Build the private relocation/call/switch model from the verified application and dump. |
| [extract_assets.py](../tools/scripts/extract_assets.py) | Recover embedded PICT/icon/cursor resources, preserving raw bytes and verifying bitmap previews. |
| [decode_archive.py](../tools/scripts/decode_archive.py) | Serialized Huffman decoder and data-free `ABBA` self-check. |
| [extract_audio.py](../tools/scripts/extract_audio.py) | Decode external effects; preserve complete blocks and export only the traced playback slice. |
| [extract_external_graphics.py](../tools/scripts/extract_external_graphics.py) | Decode two-bit graphics, signed hotspots and cumulative XOR frames; generate a private gallery. |
| [check_layout.py](../tools/scripts/check_layout.py) | Isolated regeneration against a complete saved private baseline, with simulated HFS extraction. |

## Analysis and native data generation

| Source | Purpose / invocation arguments |
|---|---|
| [animation_calls.py](../tools/recompilation/animation_calls.py) | Index assembly animation calls; optional output JSON path. |
| [idle_evidence.py](../tools/recompilation/idle_evidence.py) | Audit idle scripts and bounded direct-call candidates; optional output JSON path. |
| [original_tables.py](../tools/recompilation/original_tables.py) | Generate native tables: `WORKSPACE OUTPUT_HEADER`. |
| [catalog.py](../tools/recompilation/catalog.py) | Validate frame references and generate a native catalog: `MANIFEST OUTPUT_HEADER`. |
| [combat_tables.py](../tools/recompilation/combat_tables.py) | Recover combat timing, sound events and additional frames; optional output directory. |
| [animation_assets.py](../tools/recompilation/animation_assets.py) | Generate animation headers/pixel data: `WORKSPACE OUTPUT_DIRECTORY [EXTRA_MANIFEST]`. |
| [bitmap_fonts.py](../tools/recompilation/bitmap_fonts.py) | Decode bitmap fonts: `OUTPUT_HEADER [--geneva INPUT] [--chicago INPUT]`; unavailable-font flags can be generated without originals. |
| [system_fonts.py](../tools/recompilation/system_fonts.py) | Extract System bitmap resources: `SYSTEM_MACBINARY OUTPUT_DIRECTORY [--control-code OUTPUT]`. |
| [save_interchange.py](../tools/recompilation/save_interchange.py) | MacBinary save transfer: `export SOURCE OUTPUT [--name NAME]` or `import SOURCE OUTPUT`; refuses overwrite. |
| [compare_original_frame.py](../tools/recompilation/compare_original_frame.py) | Compare private captures: `NATIVE_IMAGE --original ORIGINAL_IMAGE [--exact-viewport]`. |
| [prepare_data.py](../tools/recompilation/prepare_data.py) | Produce a private data pack in a new `OUTPUT_DIRECTORY`, outside native source. |

## Recovery and integration checks

| Source | Prerequisites |
|---|---|
| [catalog_check.py](../tools/recompilation_checks/catalog_check.py) | Synthetic catalog/path-validation fixtures; no original data. |
| [save_interchange_check.py](../tools/recompilation_checks/save_interchange_check.py) | Synthetic saves and CLI rejection/round-trip checks. Optional `--hfs-output NEW_DIRECTORY` additionally requires hfsutils and a private original HFS image. |
| [bitmap_fonts_check.py](../tools/recompilation_checks/bitmap_fonts_check.py) | Synthetic glyph checks plus supplied original Chicago12/Geneva9/Stop resources. Optional local System/Geneva inputs extend coverage. |
| [menu_reachability_check.py](../tools/recompilation_checks/menu_reachability_check.py) | Private recovery model and compatible native-source checkout. |
| [evaluation_data_check.py](../tools/recompilation_checks/evaluation_data_check.py) | Private recovery model and compatible native evaluation source. |
| [idle_evidence_check.py](../tools/recompilation_checks/idle_evidence_check.py) | Private model, original binary and ALLCANM1 data. Includes synthetic call-scanner cases. |
| [animation_assets_check.py](../tools/recompilation_checks/animation_assets_check.py) | Private model/media and generated native pack directory as its positional argument. |
| [modem_native_check.py](../tools/recompilation_checks/modem_native_check.py) | Built native executable and private data-pack path as positional arguments; POSIX pseudo-terminal support. |
| [standalone_check.py](../tools/recompilation_checks/standalone_check.py) | Compatible native checkout linked as `recompilation/`, CMake and a compiler; validates that separate source project without game data. |

## Public-repository maintenance

Run these from the tools checkout:

- `python3 scripts/prepare_game_data.py --disk GAME.img --system System.bin --output NEW_FOLDER`
  runs the complete launch-data preparation,
  validates inputs/dependencies and publishes only a verified pack.
- `python3 scripts/create_workspace.py NEW_EXTERNAL_DIRECTORY` copies tool sources
  to a new private workspace and creates empty directories; it preserves existing destinations.
- `python3 scripts/check_publication.py` checks the working tree for unexpected
  file types, non-text content, generated JSON, embedded image data and symlinks.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` exercises
  binary decoders, graphics/fonts, save transfer, catalogs, import safety, command boundaries, preparation cleanup and publication checks.

Original inputs, generated tables, raw/base64 recovery models, disassembly logs,
decompiler output, original/OS media and emulator captures are excluded. Third-party
programs are linked in [dependencies](DEPENDENCIES.md), rather than copied as binaries.
