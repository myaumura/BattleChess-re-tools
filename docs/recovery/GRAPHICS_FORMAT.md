> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

Scope: the Macintosh version of Battle Chess. The Apple II release is a separate platform port; its files are not inputs to this analysis. See the [project map](../WORKFLOW.md) and [source inventory](SOURCE_INPUTS.md).

The disk artwork is recovered in the graphics gallery (private workspace: `assets/external_graphics/index.html`): **3 screens, 1,813 stored shapes, 440 local animation sequences, and 4,424 reconstructed sequence frames**. The stored-shape count includes both complete static drawings and XOR delta patches. The frame count includes each sequence's initial drawing and all successive deltas, including repeated frames; it is not a count of unique drawings or complete fights.

Run `python3 tools/scripts/extract_external_graphics.py` from the BattleChess project root. It reads the original extracted `source/macintosh/extracted/ALLCANM1.data` and `ALLCANM2.data`, the reconstructed A5 globals in `recovered/recovery_model.json`, and the shared [Huffman decoder](../../tools/scripts/decode_archive.py). It writes only `assets/external_graphics/`. Original files remain untouched. manifest.json (private workspace: `assets/external_graphics/manifest.json`) records archive hashes, file offsets, dimensions, signed hotspots, delta bit lengths, sequence selectors, and output paths. Raw metadata and decoded packed pixel bytes accompany every group.

**How the format was identified.** The embedded function names provide useful entry points, but the data layout comes from following the actual instructions. `sub_000117ac` installs pointers to offset and size tables in the expanded A5 globals. `LOADBOAR` at original application file offset `0x117fe` reads static-shape metadata, resets the decoder, and calls `SETUPSEF` at `0x11be4`. That function copies four descriptor bytes per shape and requests `ceil(width / 4) * height` decoded bytes. The factor of four establishes four two-bit pixels per byte. `DECODEW` at `0x8a92` adds an alignment byte after odd-length rows in RAM; that byte is not present in the compressed stream. The extractor uses the unpadded stored stride and preserves the decoded stream separately.

`SETUPSEQ` at `0x11e9c` walks six-byte records, then a counted sequence list. Its selective-loading path adds each record's final word to a running bit position before seeking directly into the compressed block. The extraction checks these positions against actual Huffman consumption **for every delta record**, as well as checking the complete decoded byte count. This gives independent evidence that record boundaries are correct, not merely a visually plausible width guess.

| Stored static descriptor | Meaning |
|---|---|
| Byte 0 | Width, unsigned pixels |
| Byte 1 | Height, unsigned pixels |
| Byte 2 | Horizontal hotspot, signed byte |
| Byte 3 | Vertical hotspot, signed byte |

Animation delta descriptors append a big-endian unsigned 16-bit compressed bit length. A six-byte zero descriptor terminates the delta table; a one-byte sequence count follows it. Each sequence contains a one-byte delta count, a one-byte initial-shape selector, and that many one-byte delta indices. A zero-width or zero-height delta consumes no pixels and leaves the current shape unchanged. The first descriptor's bit length includes the serialized Huffman tree; later lengths include only the corresponding pixel symbols. All sums match the shared decoder's exact final bit position.

Static descriptor tables end at their declared metadata length or a four-byte zero terminator. Each pixel block begins immediately after that metadata. `metadata.bin` preserves the actual table, including terminators and sequence lists where present. `decoded.2bpp` preserves exactly the bytes yielded by Huffman decoding, including any unused low pixel bits in the last stored byte of a row. PNGs crop to the declared width.

**Pixel states and masks.** This is not four-level grayscale. Bytes contain pixels in bits `7:6`, `5:4`, `3:2`, `1:0`, left to right. The original monochrome conversion table at application offset `0x855c` maps only state `01` to black ink. The masking table at `0x8048`, used by the blitter at `0x7f76`, preserves the destination only where a source pixel is `11`.

| Two-bit state | PNG interpretation |
|---|---|
| `00` | Opaque white |
| `01` | Opaque black |
| `10` | Opaque white under the traced monochrome conversion |
| `11` | Transparent |

States `00` and `10` must remain distinct during animation reconstruction even though both display white in these PNG previews. They can XOR to different later states. The raw two-bit streams retain that distinction. Transparent PNG pixels have alpha zero; no replacement background is burned into the artwork. These previews use the original conversion-table orientation, without runtime opponent recoloring or screen-mode changes.

**Reconstructing animation.** `DELIGATE` at `0x116fa` initializes the static shape index to `0x11`. `SETUPSEQ` resolves an initial selector with bit 7 set to global shape `0x11 + (selector & 0x7f)`, i.e. the corresponding shape from the main standing set. A selector without bit 7 uses the local combat static-shape base. The first six `ALLCANM2` groups and the idle group use the standing set; combat groups use their companion static tables. The extractor explicitly selects between those base sets and records the choice in each sequence.

`MAKESHAP` at `0x95bc` takes the previous displayed shape and the next delta, creates their union rectangle using signed hotspots, fills it with transparent state `11`, copies the old shape, then applies an XOR blit (`0x7ffc`, particularly `0x801c`/`0x802e`) for the delta. The next delta applies to this new result, not repeatedly to the original base. Callers such as the movement handler around `0x143xx` pass the currently displayed shape back to `MAKESHAP`, confirming cumulative reconstruction.

For a shape with hotspot `(hx, hy)`, its upper-left corner relative to its placement anchor is `(-hx, -hy)`. The frame PNG includes its union bounds, and the manifest retains the updated hotspot. The local gallery places successive PNGs at those anchors rather than allowing differently sized frames to jump around. Source padding is excluded from the visible rectangle; decoded bytes remain available for a future byte-exact blitter implementation.

**Archive coverage.** Table addresses below are synthetic A5-global addresses in `recovery_model.json`; archive offsets are decimal byte offsets in the original disk data forks.

| Table or block | Use |
|---|---|
| A5 globals `0xfd7a2`, 6 longs | `ALLCANM1` metadata/pixel pairs: `(0,192)` standing pieces; `(26903,27332)` idle deltas; `(37520,37544)` flat pieces |
| A5 globals `0xfd7f6`, 6 longs | Screen and other data offsets; only entries 0, 1, and 3 are pictures |
| `ALLCANM1` 127815 | Perspective board, 512 × 340 stored pixels |
| `ALLCANM1` 141796 | Flat board, 512 × 340 stored pixels |
| `ALLCANM1` 183469 | Title illustration, 512 × 340 stored pixels |
| A5 globals `0xfd85e`, 60 longs | Thirty `ALLCANM2` metadata/pixel pairs; movement groups 0–5, then combat deltas and companion static drawings |

`LOADSCRE` at `0x119d4` requests `0xaa00` decoded bytes. The screen buffer stride is `0x80` bytes (512 two-bit pixels), yielding 340 stored rows. Runtime display/rendering code uses a smaller active height in some paths; the extractor retains all 340 stored rows, including bottom padding.

The other screen-table entries are deliberately not rendered as pictures: entry 2 at 151469 is the opening-library block read by `0x5e1c`; entry 4 at 202278 contains the literal space-holder string; entry 5 at 202309 is another decoded opening-data block used around `0x14e1c`. Decoding arbitrary bytes as a bitmap would produce invented artwork.

The `ALLCANM2` table contains real delta groups 0–6, 10, 12, 16, 22, 24, and 28. Static companion groups are 7, 11, 13, 17, 23, 25, and 29. Groups 8, 9, 14, 15, 18, 19, 20, 21, 26, and 27 contain `this is just a space holder.` rather than artwork; they are recorded in the manifest. This is the table's actual content, not an extraction failure. Group names preserve table indices; the extractor does not guess a complete piece-vs-piece combat mapping from those indices.

**Verification and limits.** The script has a runnable packed-pixel and hotspot/XOR self-check. A fresh run decoded every non-placeholder graphics table, checked complete decoded lengths, checked every delta's compressed-bit boundary, validated sequence indices and base references, and reopened every saved PNG to decompress and compare its pixels with the generated pixel buffer. Saved raw bytes and the JSON manifest were also reopened and compared. This is saved-output validation and reproducible extraction, separate from executing the original Macintosh application.

The title, perspective board, standing king, walking king, combat frames (including a shattered-piece frame), and flat-piece artwork were visually inspected from the saved PNGs. Recognizable artwork is present. The extractor does not validate the original game's timing, scripted travel over the board, sound/event scheduling, opponent recoloring, clipping in every screen mode, or complete two-piece fight choreography. The gallery's 100 ms interval is explicitly a preview speed, not a recovered game tick rate. The 440 local sequences and their frames are recovered; a faithful battle player would additionally need those runtime control scripts.
