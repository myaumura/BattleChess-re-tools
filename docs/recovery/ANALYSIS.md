> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

Scope: the Macintosh version of Battle Chess. The Apple II release is a separate platform port; its files are not inputs to this analysis. See the [project map](../WORKFLOW.md) and [source inventory](SOURCE_INPUTS.md).

**Current recovery status (2026-09-08).** The original Macintosh binary and HFS image are now available and verified. Disk extraction supplies both ALLCANM archives; sound extraction produces 15 WAVs. A fresh Ghidra reconstruction emits 625 C bodies (143 with bad-data stops, three native failures); nine hand-translated routines compile and pass self-checks. See [workflow and learning guide](../WORKFLOW.md), [C reconstruction](RECONSTRUCTION_NOTES.md), [sound format](AUDIO_FORMAT.md), and [graphics format](GRAPHICS_FORMAT.md). The original analysis below retains its address-level findings, updated where later recovery supersedes them.

The supplied exports contain **MacPlay’s Battle Chess 1.0.2**, with the embedded version description `MacPlay’s Battle Chess 1.0.2.\r©1988-93 Interplay Productions.` The useful code is present, but the flat import obscures its resource structure, runtime initialization, and indirect calls. This is a static analysis, not an emulator-validated reconstruction of the game.

All hexadecimal addresses below are **offsets in the exported file**, matching Ghidra’s `ram:` addresses. They are not original Macintosh runtime addresses. Initial inputs were `tools/3rd-party/dump.log`, `source/macintosh/BattleChess.txt`, and `source/legacy-decompile/BattleChess.c`; none was modified. Later checks use `source/macintosh/BattleChess.bin` and `source/macintosh/BattleChess.img`.

**Container and coverage.** The first 128 bytes form a MacBinary header: filename `Battle Chess`, type `APPL`, creator `IPBC`, empty data fork, and a 143,318-byte resource fork beginning at `0x80`. The adjacent `!` in Ghidra's `APPLIPBC!` string is Finder flags, not part of the creator code. This interpretation follows the [original MacBinary specification](https://www.cryer.co.uk/file-types/b/bin_/original_mac_binary_format_proposal.htm). The resource header identifies resource data at file offset `0x180`, the map at `0x22b03`, and 85 resources.

The utility treats strings, resource headers, relocation records, and jump-table metadata as instructions. For example, its first alleged instruction incorporates the start of the filename. At `0x257a`, a segment-header word consumes the actual `LINK` opcode at `0x257c`, so the linear listing misses the main function’s real instruction boundary. These are interpretation problems, not evidence of encrypted or corrupt code.

The C export has 323 function definitions, 100 `halt_baddata()` statements, and ten additional “Unable to decompile” reports. The failed functions include `0x163f2`, the central search routine. Of 249 jump-table entries, 189 target addresses lack a matching function definition in this C export. This measures entry-point coverage, not percentage of recovered code.

**Resource map.** End addresses are exclusive; CODE payload sizes include their headers. Segment IDs are intentionally nonconsecutive.

| CODE ID | Payload start | End | Bytes | Observed responsibilities |
|---|---|---|---:|---|
| 0 | `0x1e20a` | `0x1e9e2` | 2,008 | A5 sizes and jump table; not ordinary executable code |
| 1 | `0x1ddfc` | `0x1e206` | 1,034 | Startup, relocation, switch dispatch, arithmetic helpers |
| 2 | `0x2578` | `0x5482` | 12,042 | Main entry, commands, board setup, piece lists, move execution |
| 3 | `0x180f0` | `0x1d3cc` | 21,212 | Large runtime/library region, including string and file routines |
| 4 | `0x54a8` | `0x7e42` | 10,650 | Game orchestration, opening-library traversal, board serialization, disk access |
| 5 | `0x7eb6` | `0x95a2` | 5,868 | Decoding, load/save, text and input helpers |
| 6 | `0x1d3d0` | `0x1ddf8` | 2,600 | Runtime/platform helpers |
| 7 | `0x95b8` | `0xe606` | 20,558 | Rendering, attacks, repetition/fifty-move logic, move generation |
| 10 | `0xe610` | `0x1169c` | 12,428 | Mac windows/events/menus, messages, serial communication, sound |
| 14 | `0x116bc` | `0x180c0` | 27,140 | Animation loading/playback and chess search |

These are mixed-purpose segments, not cleanly separated modern modules. Responsibilities are supported by code and embedded labels, rather than a recovered source-file list.

Other important resources: `STRS/0` at `0x184` (2,022 bytes), `DATA/0` at `0x96e` (6,346 bytes), `ZERO/0` at `0x223c` (680 bytes), `DREL/0` at `0x24e8` (140 bytes), and six `CREL` resources. The application also has menus, dialogs, pictures, icons, balloon-help strings, and a `vers` resource. See `dump_analysis.json` for every resource, including IDs, sizes, and names.

**Runtime reconstruction.** CODE 0 specifies `0x7e8` bytes above A5, `0x6c54` bytes below A5, a `0x7c8`-byte jump table, and table offset `0x20`. There are 249 eight-byte entries. Calls enter two bytes into each entry. This matches Apple’s [Classic 68K jump-table documentation](https://dev.os9.ca/techpubs/mac/runtimehtml/RTArch-118.html).

For these exports, the conversion is:

```text
entry index = (A5 call displacement - 0x22) / 8
target file offset = CODE payload start + 4 + entry's routine offset
```

| Call | CODE ID | Target | Meaning established from code/labels |
|---|---:|---|---|
| `A5+0x22` | 1 | `0x1de08` | Startup |
| `A5+0x3a` | 1 | `0x1df54` | Dense switch dispatch using inline data |
| `A5+0x7a` | 2 | `0x5130` | `PERFORM`, board-move state transformation |
| `A5+0xb2` | 2 | `0x257c` | `MAIN` |
| `A5+0x21a` | 4 | `0x6912` | `FWMEMCPY`, byte-copy helper |
| `A5+0x35a` | 7 | `0xc410` | `ATTACKS` |
| `A5+0x37a` | 7 | `0xc23e` | `PIECEATT` |
| `A5+0x4ca` | 10 | `0xfe2e` | `SUCCMSG`, advance a message-ring pointer |

Do not read expressions such as `(**(code **)(unaff_A5 + 0x21a))` as proof that the source used function pointers. The assembly calls executable A5 jump-table entries. Ghidra has lost that distinction.

Startup at `0x1de08` loads `STRS` through `0x1e0c2`, saves the resulting string base, initializes globals through `0x1de98`, performs additional runtime setup, and calls `MAIN` via `A5+0xb2`. It eventually reaches `ExitToShell`.

At `0x1de98`, DATA is copied word by word into the region ending at A5. Each zero word introduces an additional zero-byte count from ZERO. Replaying this algorithm consumes all 340 ZERO counts and expands 6,346 DATA bytes to **27,732 bytes, exactly `0x6c54`**. DATA therefore cannot simply be mapped at `A5-0x6c54` as raw bytes.

The relocation loop at `0x1dee4` reads signed word offsets. Bit zero chooses the saved string base versus A5; the cleared offset locates the longword to adjust. DREL uses A5 as the destination base. The CODE loader at `0x1de48` handles the high-bit marker in certain segment headers and applies corresponding CREL records. A correct Ghidra memory model must account for both relocation families.

**Embedded names and a specific decompiler failure.** Many routines are followed by eight-character ASCII labels. Examples include `MAIN`, `CALCPIEC`, `FILLSAVE`, `SEARCH`, `SEARCHLO`, and `SUCCMSG`. They are stronger evidence than invented function names, but names are truncated and can collide: several routines have `SEARCHSM`. The JSON records label addresses, not automatically inferred function starts.

At `0x178c0`, the code calls `A5+0x3a`, which resolves to the dispatcher at `0x1df54`. That dispatcher pops the return address and interprets following words as a switch table. The words at `0x178c4` onward are therefore inline data. Both flat disassembly and Ghidra’s C incorrectly continue through them as instructions; the C invents a stack bit operation and stops at `halt_baddata()`. Repairing this switch pattern is essential to recovering piece move generation. Similar runtime dispatchers exist at `0x1df2c` and `0x1df40`.

**Chess representation.** The engine uses 0x88 square indexing, directly evidenced by rank increments of 16 and `(square & 0x88) == 0` checks in `0x17570`, `0x17da0`, and assembly near `0x1790a`. The square parser at `0x666e` computes `(rank-'1')*16 + (file-'a')` for valid coordinate characters.

| A5-relative location | Interpretation | Evidence |
|---|---|---|
| `-0x6c54 + square*4` | Piece code, byte | Insert, serialize, move-generation routines |
| `-0x6c53 + square*4` | Side, byte | Same routines; two side values |
| `-0x6c52 + square*4` | Piece-list index, word | `0x4c8c` initializes to `0x10`; assembly near `0x4e50` installs an index |
| `-0x6a74 + side*0x20 + index*2` | Piece-list square byte, then piece-code byte | `0x4c8c`, `0x17570` |
| `-0x6a2c`, `-0x6a2b` | Current side/opponent during search | Swapped around recursion in `0x168d0` |
| `-0x6a2a` | Search ply, word | Incremented/decremented around recursion |
| `-0x6600` | Two signed pawn-direction words | Expanded DATA contains `+16, -16` |
| `-0x3288` | 64-byte display-board representation | `0xfc2e` |

The board region has 120 four-byte slots: enough to include square `0x77`, with gaps between playable ranks. It should not be described as a contiguous 64-square array, nor does it require storage for all 128 possible 0x88 indices.

Piece code `0` is empty; `6` is a pawn, supported by pawn movement and promotion handling. Code `1` is strongly indicated as king by castling construction at `0x17c96`; the remaining codes should be confirmed before assigning complete names. The expanded display conversion table at `A5-0x3c02` is `[0,2,5,6,1,3,4]`: graphics piece numbers differ from engine piece numbers.

At `0x6c8c` (`FILLSAVE`), serialization writes one side byte followed by 32 bytes holding two four-bit square records each. A square nibble is `piece | (side << 3)`, and the first square goes in the high nibble. This establishes a **33-byte board snapshot**, not the complete save-file format. The surrounding save/history fields need separate tracing.

**Search and animation.** `0x163f2` is explicitly followed by the `SEARCH` label, but the original Ghidra export fails to decompile it. The reconstructed export now emits this function; that is not proof of semantic correctness. Its caller `0x168d0` swaps sides, increments ply, recurses, negates the returned score, restores state, and compares scores against bounds. This is strong evidence for negamax-style alpha-beta search. The code initializes 24 ply slots and permits recursive descent while ply is below 23; that is an internal capacity bound, not a claim that each difficulty level searches 24 plies.

Useful search entry points are `0x16280` (clears per-ply candidate storage, label `CLEARKIL`), `0x16592` (ordered candidate selection, `SEARCHSE`), `0x168d0` (search/evaluate candidate loop, `SEARCHLO`), `0x174ea` (promotion choices 2 through 5), `0x17570` (capture candidates), `0x17832` (piece-dispatched move generation), `0x17c96` (castling candidates), and `0x17da0` (en-passant candidates). Exact evaluation weights, depth policy, and any transposition-table implementation are not established by this pass.

Animation work is concentrated in the earlier part of CODE 14, with labels such as `LOADBOAR`, `GETCOMBA`, `SETUPSEQ`, `LOADMOVE`, `LOADSFX`, `CRUNCHAN`, `WAITANIM`, and `STARTANI`. CODE 5 contains bitstream decoding at `0x891c`, including a byte-indexed fast table and a fallback table walk; this was subsequently confirmed as a Huffman prefix decoder with a custom tree serialization. Strings reference external `ALLCANM1` and `ALLCANM2` data files. Both have now been extracted from the Macintosh HFS image. See the dedicated audio and graphics format notes for working decoders and evidence.

One small routine is completely understood: `0xfe2e` (`SUCCMSG`) adds 20 to a message pointer and wraps `A5-0x5130` back to `A5-0x51d0`. That describes eight 20-byte message slots. Calls from `0x42d6` and `0x48f2` populate message type 5 and coordinate fields before advancing the pointer.

**Reconstruction performed.** The separate Ghidra rebuild follows this approach: preserve file offsets as a reference, define each CODE payload and its headers, seed functions from the 249 resolved jump targets, allocate a synthetic A5 world, expand DATA/ZERO, apply DREL/CREL with a mapped string base, and resolve A5 calls. Then repair inline switch tables and model Macintosh A-line traps and runtime calling conventions before trusting recovered prototypes. Embedded names can guide renaming after function boundaries are checked. The highest-value initial targets are `MAIN` at `0x257c`, `SEARCH` at `0x163f2`, and the move-generation switch at `0x178c0`.

**Reproducibility and limits.** Run `python3 tools/scripts/analyze_dump.py` from the BattleChess project root. It regenerates `dump_analysis.json`, rejects conflicting byte observations, validates resource bounds and jump-entry opcodes, checks the DATA/ZERO expansion against CODE 0, and reopens the saved JSON to verify it. Numeric JSON offsets are decimal.

The utility’s displayed byte columns supply 143,446 of 143,488 file positions. Ghidra’s untruncated byte fields fill 34 more with no conflicts. Eight bytes were unavailable from those literal columns: `0x414–0x417` and `0x432–0x435`, inside resignation strings. The original binary now supplies them, after agreement with all 143,480 known bytes is checked. Replaying `m68kdasm --68k` against that binary reproduces the supplied log exactly. The application extracted from the HFS disk also matches the entire original MacBinary file byte for byte. The existing Ghidra project remains unchanged, and no Macintosh execution was performed.
