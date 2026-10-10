# Battle Chess external compression and sound recovery

> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

Scope: the Macintosh version of Battle Chess. The Apple II release is a separate platform port; its files are not inputs to this analysis. See the [project map](../WORKFLOW.md) and [source inventory](SOURCE_INPUTS.md).

The supplied disk now provides `source/macintosh/extracted/ALLCANM1.data` and `ALLCANM2.data`. `extract_audio.py` recovers **15 distinct effects**, keeps every complete decompressed block, and writes unsigned 8-bit mono PCM WAVs in `assets/audio/`. Open `assets/audio/index.html` to listen. Indices are the original effect-table indices; descriptive names have not been guessed. No separate music soundtrack is established.

## Reproduce and verify

```sh
python3 tools/scripts/decode_archive.py
python3 tools/scripts/extract_audio.py
```

Extraction uses the reconstructed `recovered/recovery_model.json` A5 globals and original archive data forks. Rebuild the model with the project recovery workflow if changing inputs. The audio manifest records both archive hashes, compressed positions and sizes, decoded hashes, period words, byte selection, rate, duration, and filenames. Saved decoded files are reopened and compared; every saved WAV is reopened with `wave`, and its format, frame count and entire PCM payload must match. These are saved-output and decoder checks, not execution in a Macintosh emulator. A clean extraction was also run from the saved inputs. No audio was synthesized, denoised, normalized or resampled. There is no listening-capable tool in this session, so no perceptual quality claim is made.

## Compression: source evidence to working decoder

`0x8724` resets state and calls `0x8732`. It reads ten bytes: the first big-endian longword is the output size (`A5-0x22a6`), the next longword is compressed-length metadata, and bytes 8–9 begin the bitstream. `0x87dc` reads most-significant bit first, including when a disk buffer starts at an odd address. The on-disk order remains sequential bytes; the assembly's odd-address adjustment is memory alignment, not an alternate bit order.

`0x87b4` reconstructs a binary prefix tree: zero opens an internal node, left recursion appends zero to the code, then **one structural bit is consumed and discarded**, and right recursion appends one. One denotes a leaf followed by its eight-bit symbol (`0x881e`). That extra bit before the right subtree matters: treating this as an ordinary preorder Huffman serialization misaligns all later fields. Symbols and their code lengths are recorded at `A5-0x229a`.

`0x8832` builds an eight-bit lookup table and fallback entries for longer codes. `0x891c` emits the matching symbol and advances by the code length; it has no backreference, dictionary, delta, or RLE operation. `decode_archive.Decoder` implements the equivalent tree traversal and retains bit position between `read(count)` calls. `decode(data, offset=0)` returns the full block. This API also serves artwork and animation extraction. The test encodes a two-leaf tree by hand, checks full and split reads, and rejects truncation.

For all 20 stored sound blocks, consumed bit count equals the second header longword plus 57, and stored block bytes equal `8 + (second_word >> 3)`. Thus that field corresponds to consumed payload bits plus seven (a byte-rounding bias). This is an observed invariant, not a claim about an original compressor implementation. Every adjacent sound-table offset lands exactly at the next block boundary. All five effects duplicated between disks decode identically. These independent checks make the decoded output substantially stronger evidence than merely plausible audio bytes.

## Locating effects

Pointer initialization at `0x117b8` and `0x117c0` sets the sound-offset tables to `A5-0x2846` and `A5-0x26b2` (synthetic `0xfd7ba` and `0xfd94e`). `LOADSFX` at `0x128cc` selects disk 1 (`ALLCANM2`) for effect indices 0–4 and disk 0 (`ALLCANM1`) for 5–14, seeks to a four-byte table entry, resets the decoder, and requests up to 18,000 bytes. The header caps the actual decoded amount.

| Indices | Archive | Offsets (decimal) |
|---|---|---|
| 0–4 | ALLCANM2 | 765206, 769276, 781033, 788274, 792988 |
| 5–14 | ALLCANM1 | 70009, 78076, 85174, 89017, 101444, 105781, 112488, 115618, 120482, 124476 |

ALLCANM1 also stores exact copies of effects 0–4 at 38474, 42544, 54301, 61542 and 66256. The extractor verifies those duplicates without exporting duplicate WAVs.

## Playback, including the easily missed six bytes

`MACPLAYS` at `0x115fc` reads the period word at decoded offset 0 and a length word at offset 2. It computes `adjusted_period = max(20, period - 8 * signed_pitch)`. At `0x11654` it chooses decoded offset 4 as its sound-driver buffer; `0x11664` overwrites its mode word with zero, then `0x11670` computes `FixRatio(180, adjusted_period)` and stores that fixed-point rate at buffer offset 2. Consequently **decoded bytes 4–9 are header workspace, and PCM begins at decoded offset 10**. Many records have the obvious placeholder sequence `01 02 03 04 05 06`; some do not, so detecting it by magic bytes would be wrong.

At `0x1167c–0x1168c`, the driver byte count is twice the length word and the pointer is decoded offset 4. Therefore the faithfully selected PCM range is `[10, 4 + 2*length_word)`, not every byte after the scratch header. The complete decoded block sometimes contains additional trailing bytes, including over a hundred in effects 1 and 8. They remain in `.decoded.bin`; WAVs preserve precisely the PCM range passed by this call. The manifest exposes the number excluded.

Apple's [Inside Macintosh, Volume II, Sound Driver, pp. II-228–229](https://puyoman.net/documentation/Inside_Macintosh.pdf) defines mode zero as the free-form synthesizer with a six-byte header and a count of waveform bytes advanced every 44.93 microseconds. Applying that documented driver behavior to the game's ratio gives a neutral-pitch rate of `(1_000_000/44.93) * 180/period`. WAV stores the nearest integer rate, from 3,130 to 24,730 Hz across these effects. This approximates the documented timing and omits sub-Hz 16.16 ratio quantization; it does not claim cycle-accurate hardware timing or model the driver's interpolation. The PCM bytes remain unchanged, including silence near unsigned midpoint 128. Pitch variations invoked by gameplay are not separately exported.

## Reusable lessons

- Trace consumers as well as loaders: decoding alone would have included scratch bytes as sound and silently selected the wrong tail length.
- Follow disk selection and reconstructed global pointers before assigning assets to files. The same five samples on both disks are useful independent verification.
- Recognize lookup-table construction as an optimization of a simpler prefix tree. Reproduce the semantics rather than porting alignment and buffering machinery.
- Confirm a guessed serialization against exact adjacent block boundaries and duplicate records, not solely a recognizable first output byte.
- Keep complete decoded originals beside a presentation conversion, and document which executable instructions justify every discarded byte.
