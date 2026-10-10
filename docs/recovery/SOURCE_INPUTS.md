# Original inputs and reference exports

> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

Apple II and Macintosh are two platform ports of the same Battle Chess game. This project uses the Macintosh port consistently; Apple II files are not missing Macintosh assets.

- `macintosh/BattleChess.img`: original Macintosh HFS disk image; authoritative disk source.
- `macintosh/BattleChess.bin`: canonical MacBinary application, verified against the disk extraction.
- `macintosh/extracted/`: reproducible disk extraction, including both forks and the manual. `Battle_Chess.bin` is a relative symlink to the canonical application, not a second copy.
- `macintosh/BattleChess.txt`, IDA sidecars and `BattleChess.gpr`/`.rep`: preserved analysis exports and databases. Database backups remain intact.
- `legacy-decompile/BattleChess.c` and `.h`: preserved early Ghidra pseudocode export, not native C source or the current recovery output.
- `apple-ii/`: a different platform release and its archive metadata. It is not an input to the Macintosh port. The duplicate screenshot is a relative symlink.

The disk image, MacBinary containers, and extracted forks represent different layers of the same source, not competing versions. Retain the image to reproduce the extraction. Run `python3 tools/scripts/extract_disk.py` from the project root to regenerate extracted files; it verifies the application against the canonical binary before writing outputs.

Current reconstructed pseudocode and hand-translated C remain in `recovered/`; your native C work belongs in `cross-port/`.

For C development, start with readable_core.c (private workspace: `recovered/readable_core.c`), consult current pseudocode (private workspace: `recovered/BattleChess_recovered.c`), and work in cross-port/ (private workspace: `cross-port`). Preserve the original inputs as evidence.
