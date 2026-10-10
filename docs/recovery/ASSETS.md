# Recovered Macintosh media

> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

These assets come from the Macintosh version of Battle Chess. The Apple II folder contains another platform port of the same game; do not mix it into this asset pipeline. Native C/SDL work in `cross-port/` can use these decoded PNGs and WAVs. See the [project map](../WORKFLOW.md).

Recovered from the verified application bytes (also represented in the supplied text exports): **11 graphic resources**, with original payloads in `raw/`, five standalone `.pict` files, and **10 PNG previews**. Open `index.html` to browse. `manifest.json` records original resource IDs, offsets, byte lengths, SHA-256 hashes, dimensions, and cursor hotspots.

| Resource | Result |
|---|---|
| PICT 400–403 | Four 50 × 100 monochrome piece drawings: bishop, knight, queen, rook |
| PICT 10001 | Original text/vector picture preserved as `.pict`; no trustworthy PNG available |
| ICN# 128–130 | Three 32 × 32 icons with transparency masks |
| ICON 3 | One 32 × 32 monochrome icon |
| CURS 400–401 | Two 16 × 16 cursors, masks and hotspots preserved |

Rebuild from the BattleChess project root with `python3 tools/scripts/extract_assets.py`. Only the Python standard library is required. It reuses `analyze_dump.read_dump`, rejects unavailable source bytes, preserves and reopens every raw payload, validates the exact bitmap PICT structure and PackBits row lengths, and reopens/decompresses the saved PNGs to compare their pixels with the decoded source. The four rendered PICTs were also visually inspected; the drawings are present. The PNG icon/cursor previews preserve their masks; these cursors have no invert-background pixels.

The `.pict` files add a 512-byte zero file header before the unchanged PICT resource payload. Modern macOS `sips` produced blank previews for PICT 400–403, so the extractor decodes their bitmap records directly. Both `sips` and AppKit rejected the text/vector PICT 10001. It is preserved intact rather than replaced with a blank or invented approximation. This is format conversion, not target-game/emulator validation.

**External archives are now recovered.** `tools/scripts/extract_disk.py` (relative to the project root) extracts `ALLCANM1` and `ALLCANM2` from the verified Macintosh HFS image while preserving both forks. Audio gallery (private workspace: `assets/audio/index.html`) contains 15 distinct original sound effects as WAVs; [audio format notes](AUDIO_FORMAT.md) document the Huffman decoder and the exact playback slice. These are sound effects; a separate music soundtrack has not been established.

External graphics (private workspace: `assets/external_graphics/index.html`) contains three screens and 4,424 reconstructed frames across 440 local sequences, plus the stored shapes and delta patches. [Graphics format notes](GRAPHICS_FORMAT.md) explain mask/ink pixels, signed anchors and cumulative XOR reconstruction. Preview timing is illustrative; full fight choreography is not reproduced. Reproduce the complete workflow using [the project guide](../WORKFLOW.md). Neither decoded assets nor static C output have been validated in a running Macintosh game.
