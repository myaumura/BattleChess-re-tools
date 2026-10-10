# Macintosh code recovery

> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

This directory describes the Macintosh port only. The Apple II release is the same game on a different platform, not an additional source of compatible code or assets. See the [project map](../WORKFLOW.md).

Start with **readable_core.c (private workspace: `recovered/readable_core.c`)** for readable, hand-translated C. It contains nine routines covering 0x88 coordinates, piece-list initialization/rebuilding, packed board snapshots, display encoding, occupancy, and the message ring. Original assembly offsets and any deliberate differences are documented beside each function. This file compiles and has a runnable self-check; it is not a playable game.

**BattleChess_recovered.c (private workspace: `recovered/BattleChess_recovered.c`)** is the broader, fresh Ghidra export: 625 emitted C bodies, 673 resolved A5 call/jump sites, 27 modeled dense-switch sites, and 12 modeled sparse-switch sites. It includes `MAIN_0000257c`, `SEARCH_000163f2`, and the piece movement branches at `SEARCHSM_00017832`. The earlier C export did not decompile the central SEARCH function.

This larger file is C-style pseudocode, not buildable recovered source. **143 emitted bodies still contain bad-data stops**, mainly around unsupported Macintosh traps. Three functions fail with native decompiler process errors (`0x46c8`, `0x129a2`, `0x1bdf8`). The two former parameter-analysis failures now emit after applying the existing two-byte stack convention to analyzer-discovered leaf routines. Emission does not establish semantic correctness. Function names inferred from nearby eight-character labels remain provisional; register-based runtime helpers and Pascal trap stack effects still need work. The model validates 38 dense and 15 sparse tables; Ghidra attaches 27 and 12 respectively to recognized containing functions. Switch cases may use destination addresses instead of selector values. More reachable code can expose additional bad-data stops; these counts are not a semantic-coverage score. See [reconstruction notes](RECONSTRUCTION_NOTES.md) for before/after evidence and remaining limits.

The model uses synthetic `A5=0x100000` and `STRS=0x200000`. CODE addresses retain their offsets in the original file. Globals such as `DAT_000f95d6` therefore correspond to original `A5-0x6a2a`; they are not historical Macintosh RAM addresses. DATA/ZERO expansion, 179 DREL/CREL fixups, and loaded jump stubs are reconstructed before disassembly. The original binary fills the eight STRS bytes omitted by the text exports. Every one of the 143,480 known export bytes is checked against it before analysis. No original dump or Ghidra project was edited.

Supporting files:

- functions.tsv (private workspace: `recovered/functions.tsv`): addresses, names, emission status, and bad-data-stop flags.
- recovery_model.json (private workspace: `recovered/recovery_model.json`): deterministic original-binary blocks, relocation audit, entry seeds, labels, call targets, and dense tables.
- decompile_summary.txt (private workspace: `recovered/decompile_summary.txt`): actual emitted/failed/truncated counts.
- rebuild.log (private workspace: `recovered/rebuild.log`): Ghidra analysis and decompiler diagnostics.

From the BattleChess project root, reproduce and test with:

```sh
python3 tools/scripts/extract_assets.py
python3 tools/scripts/rebuild_recovery.py
clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -DBC_SELF_TEST recovered/readable_core.c -o /tmp/bc-core
/tmp/bc-core
```

The extractor and model preparation use Python's standard library. Full C regeneration uses installed **Ghidra 12.1.3 and OpenJDK 21**; the runner defaults to their Homebrew paths on this machine. Optional positional arguments supply another Ghidra `libexec` directory and Java executable. Its project and caches live in a temporary directory; the resulting C and diagnostics stay here. `prepare_recovery.py` and `RecoverBattleChess.java` are the reconstruction sources.

Verification performed: the C self-check passed under address/undefined-behavior sanitizers; a fresh isolated Ghidra rebuild emitted the saved C; the runner reopened it and checked MAIN, SEARCH, a direct A5 target, dense piece-switch branches, sparse command branches, and the repaired leaf prototypes. Asset regeneration reopened and compared original payloads and decoded PNG pixels. These checks do not replace running the original Macintosh game or establish equivalence of the automatically decompiled engine.

The **picture gallery (private workspace: `assets/index.html`)** contains ten PNG previews from eleven embedded graphic resources. Five original PICT files are preserved; the text/vector PICT 10001 has no reliable PNG preview. The source PICTs retain their original bytes with the standard [512-byte file header](https://developer.apple.com/documentation/appkit/nspictimagerep/pictrepresentation) added.

The original Macintosh disk image supplies the external animation/audio archives. See [asset notes](ASSETS.md) for extraction and decoding status; these external assets do not by themselves resolve the executable’s Macintosh runtime calls.

## Translation provenance

Native C work belongs in `cross-port/`. Preserve the existing comments and self-check when moving routines from `readable_core.c`; keep game logic independent of SDL. The broader export is a reference to investigate, not a file to compile wholesale. The early C/header pair is preserved in `source/legacy-decompile/` relative to the project root.

For each translated routine, retain its original label and file offset or range, explain its inferred purpose, and record intentional behavior changes and remaining uncertainty. For fields, retain useful A5-relative offsets. Distinguish original executable file offsets from the reconstruction's synthetic addresses; do not reproduce synthetic addresses as native pointer values. A successful compilation or self-check does not establish equivalence to execution of the original game.

The generation chain is `tools/scripts/rebuild_recovery.py` → `tools/scripts/prepare_recovery.py` → headless Ghidra running `RecoverBattleChess.java` → `recovered/BattleChess_recovered.c` (paths relative to the project root). Change the generator or analysis model for reproducible export fixes; keep hand translations separate.
