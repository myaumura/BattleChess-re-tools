# Native recovery evidence

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

This folder records how Macintosh behavior was recovered for
[BattleChess](https://github.com/myaumura/BattleChess). Its dated observations,
original offsets and validation limits support the native implementation.

For installation and play, use the [final preparation and launch guide](../PREPARE_DATA.md).
For extraction and translation, use the [reverse-engineering process](../WORKFLOW.md#reverse-engineering-process)
and [script inventory](../TOOLS.md). The [publication guide](PUBLICATION.md)
explains which repositories contain source, tools and user-supplied data.

## Evidence by topic

| Area | References |
|---|---|
| Graphics and controls | [Presentation](PRESENTATION_EVIDENCE.md), [dialogs](RESOURCE_DIALOGS.md), [menus](MENU_REACHABILITY_EVIDENCE.md) |
| Movement and combat | [Call sites](ANIMATION_CALLS.md), [scheduler](ANIMATION_RUNTIME.md), [combat tables](ANIMATION_COMBAT.md) |
| Computer play | [Search](SEARCH_EVIDENCE.md), [evaluation](EVALUATION_EVIDENCE.md), [time controls](TIME_CONTROL_EVIDENCE.md), [endings](ENDINGS_EVIDENCE.md) |
| Files and serial play | [Save/setup](FILE_SETUP_EVIDENCE.md), [idle/modem](IDLE_MODEM_EVIDENCE.md) |
| Validation | [Original execution](ORIGINAL_RUNTIME_EVIDENCE.md), [platform records](PLATFORM_VALIDATION.md) |
| Further recovery | [Remaining work](REMAINING_RECOVERY_PLAN.md), [progress](RECOVERY_PROGRESS.md), [development discipline](DEVELOPMENT.md) |

## Native implementation recorded on 2026-10-03

A separate C11 core and C++17/SDL3 application for the Macintosh recovery. `cross-port/` remains your independent project and is neither compiled nor modified here. Only recovered engine behavior is implemented: no rules or AI from the Swift remake have been substituted.

This version supports human and computer players using translated Macintosh move rules, opening book, evaluation and search, with the original perspective/flat graphics. The inspector tabs, custom grid, side badges, and arbitrary animation preview are removed. Original shape selectors, anchors, layering, hit-test tables, and 2-bit side recoloring are used directly. See [presentation evidence](PRESENTATION_EVIDENCE.md).

The native port now connects computer play, original movement/combat, mate/stalemate presentation, file open/save, board setup, resource menus/dialogs, and modem play through a POSIX serial device. Human White / Mac Black is the original initial mode. Packaged System7 Chicago12 and Geneva9 bitmap resources supply interface and About text; the host retains native SDL and OS adapters where the original used Toolbox.

**Original-runtime parity is only partly established.** The canonical game was booted in Mini vMac's Macintosh IIx configuration with System7. Its initial 511×320 scene matches the native rendering apart from the cursor. About failed and an observed turn did not complete, so stable reference gameplay still needs investigation. Animation timing, sound, computer decisions, complete Toolbox appearance, save interoperability and physical modem compatibility remain open. See [original-runtime evidence](ORIGINAL_RUNTIME_EVIDENCE.md) for the exact inputs and comparison boundary.

Recorded status **2026-10-03**. The visible game area uses WIND400's 511×320 dimensions and dialog pushbuttons activate on release. macOS saves retain `Game`/`IPBC` Finder identity; MacBinary/HFS transfer and modem retry boundaries retain their preceding validation. The new idle byte/caller audit recovers twelve bishop scripts and 218 frames, without a proven trigger. The recorded macOS suite passed all 32 CTests with ASan/UBSan enabled (37.34 seconds), including native smoke and strict saved initial-frame comparison. The preceding 31-test pass also ran Cocoa smoke. The Linux baseline passed 29 tests, X11 smoke and 113 animation cases; later changes still need a Linux rerun. No browser or new original-emulator session was run. [Remaining recovery work](REMAINING_RECOVERY_PLAN.md) lists the next steps and their acceptance checks; [the execution log](RECOVERY_PROGRESS.md) records completed work.

## Layout

The [native repository](https://github.com/myaumura/BattleChess) contains `lib/`,
`src/`, `tests/`, build configuration and build/run scripts. This
[tools repository](https://github.com/myaumura/BattleChess-re-tools) contains
extraction, pack generators, data-dependent checks and these evidence documents.
Original inputs and generated packs belong outside both source checkouts; the
[preparation guide](../PREPARE_DATA.md#preparation-flow) defines their locations.

Older records use `recompilation/` for the native checkout and `source/`,
`recovered/` and `assets/` for private workbench artifacts. These are historical
provenance paths, not directories that a public clone must contain.

## Recovered animation execution

Moves now use the original DOWALK graph: turns, per-square walking, knight obstacle reactions, rook transformations, paired combat, and the original 16-stage bit-mask fade. Castling and en passant run their original sequential submoves. Promotion animates the pawn first, then presents the original four picture choices and replaces the piece; undo/replay remain quick placement paths. Checkmate queues the original artificial king capture selected by BUILDCHE.

Both archives provide **646 sequences / 6,824 cumulative frames**, including **206 sequences omitted by the previous archive extractor**. Pack preparation preserves the original two-bit pixels for correct side coloring. All 36 ordered combat table entries and the eight animation handlers are recovered; the king/king table is empty in the original. Combat timing requires EXPANDDA decompression, yielding 7,607 bytes across 72 streams. Walking/turning uses 144 timing streams. Sound events use original effect IDs and pitch-period adjustment; SDL replaces the Mac sound driver.

Evidence and native translations:

- [Call sites and graph construction](ANIMATION_CALLS.md), including the checkmate and quick placement paths.
- [Eight handlers and scheduler](ANIMATION_RUNTIME.md).
- [Combat tables and missing archive groups](ANIMATION_COMBAT.md).
- Private assembly call-site index `animation_calls.json`, generated by [`animation_calls.py`](../../tools/recompilation/animation_calls.py) in a recovery workbench.

The twelve stored idle entries contain **218 frames** using the bishop's four standing views; entries4..7 are duplicated as8..11. A [reproducible byte/caller audit](IDLE_MODEM_EVIDENCE.md#script-and-caller-recovery--2026-10-03) freshly decodes those pixels and traces the null-event clock path. No original idle trigger is established, so automatic idle behavior remains absent. The initial scene has also been compared with the running original; animation timing and complete sequence behavior still need runtime comparison. SDL audio buffering and conversion are platform adaptations, and the native clock maps to 60 ticks per second.

## Build and run

Use the [preparation and launch guide](../PREPARE_DATA.md) for the supported inputs,
permanent data directory and launch command. The native application consumes a
prepared pack through `BC_DATA_DIR` / `--data`. Its build does not extract original
files or regenerate the pack.

Compiler, CMake, SDL3, sanitizer and platform commands are maintained in the
[native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md).
The [data contract](https://github.com/myaumura/BattleChess/blob/main/docs/DATA.md)
lists the pack files required at compilation and runtime.

## Controls

Click a piece, then its destination. Promotion uses the original four picture choices after the pawn travels. File → New Game asks the original confirmation; Move → Take Back / Replay restore native position snapshots. Settings switches between original 2D and 3D boards and Human/Mac control for either side; Modem control is available when a serial device is configured. Command/Ctrl+N, O, S, B, R, Q provide the corresponding shortcuts. Move → Force Move (Command/Ctrl+F) stops thinking at the recovered search stop points; Suggest Move (Command/Ctrl+M) runs the original hint search without changing the board. Take Back and Replay pause automatic computer turns; Force Move resumes a Mac turn. Loading preserves the original scheduling order: the loaded side’s existing player setting decides whether to start thinking, before the file’s player settings replace it. Escape dismisses a menu/selection or cancels confirmation; Enter accepts an alert. Pass `--flat` to start with the flat board.

Menus support press-drag-release selection, heading switching and enabled-item highlights, following the Macintosh MenuSelect flow.

Dialog pushbuttons commit on mouse release inside the same button. Releasing outside or over another button cancels the press; leaving and returning before release is allowed. Focus loss, dialog replacement and keyboard completion clear pending mouse input. Picture choices and editable fields retain their separate resource behavior. Pressed/disabled button graphics remain unverified.

File → Open Game / Save / Save As use native OS file pickers and the recovered 78-byte data format. Save writes a temporary sibling and renames it only after successful completion, including `Game`/`IPBC` Finder metadata on macOS. Opaque bytes from an opened file are preserved. Human/Mac/Modem player settings are preserved, including modem control code `2` when no device is configured. Connect a serial device to play a loaded modem-controlled side; unsupported control code `3` is rejected. History is absent from the original file format and is cleared on open. MacBinary/HFS transfer is verified; original-executable save exchange remains untested. Automated UI checks exercise the file-result path; interactive OS file-picker operation is not covered by those checks.

For save transfer, [`save_interchange.py`](../../tools/recompilation/save_interchange.py)
preserves the data bytes and Finder identity in a MacBinary container.
[Save evidence](FILE_SETUP_EVIDENCE.md#save-transfer--2026-10-03)
contains permanent save paths, format limits and the optional HFS check.

File → Set Up Board temporarily uses the original flat board and two side palettes. Click a board piece to pick it up, then another square to place it; click outside to discard it. Palette rows are king, queen, rook, bishop, knight, pawn. Board Setup → Clear Board asks confirmation; Restore board restores the entry position; Done applies the original validation and clears move history. Side to move is retained, matching the recovered editor.

Level offers the original Novice, fixed thinking times and custom-minute dialog. Custom minutes are not stored in the original save format, so loading that level reopens the dialog.

The original title appears while assets load, without an added start screen. New-game/clear confirmations, messages, promotion and About use original resource rectangles. About recovers the MacPlay bitmap and positioned text from PICT10001, rendered with the original System7 Geneva9 bitmap strike. Chicago12 supplies interface text. Recovered CDEF0/QuickDraw button corners and the default ring match all 448 compared System7 confirmation pixels; the recovered StopAlert ICON0 matches all 1,024 compared icon pixels. Full window, disabled-control and pressed-state appearance remains unverified. Control details and comparison scope are recorded in [resource-dialog evidence](RESOURCE_DIALOGS.md).

## Modem play

After preparing the pack, supply a POSIX serial device or pseudo-terminal with
`--serial DEVICE` when launching the native application. See the
[native README](https://github.com/myaumura/BattleChess/blob/main/README.md#controls)
for current launch usage.

The adapter uses the original 300-baud, 8-data-bit, no-parity, one-stop-bit configuration. Settings → Modem White/Black enables the original control mode; the Modem menu provides Dial Number, Hang Up, Auto Answer, and Talk using recovered resources and command bytes. No TCP matchmaking or replacement protocol is added.

The original binary protocol carries moves, promotion choices, 33-byte board snapshots, acknowledgments, and ending signals. Native input validation rejects malformed frames and stale promotion choices. The original checksum and shared-buffer retry behavior remain documented rather than silently repaired. Serial work runs outside the SDL thread; File/Quit and window close send the original quit line before a bounded native shutdown.

Two-process PTY checks exercise the session code and the actual SDL host, including move exchange, board replacement, promotion validation, saved modem settings, and both quit paths. These tests establish the native serial path; physical modem operation and interoperability with the running Macintosh original remain unverified. See [protocol and idle evidence](IDLE_MODEM_EVIDENCE.md).

## Source and provenance

The following paths name the source versions used during the 2026-10-03 recovery.
Native filenames and module boundaries may have changed since that record;
tool generators now live under `tools/recompilation/` in this repository.

| Recorded file | Role |
|---|---|
| `lib/recovered_core.c`, `.h` | The existing nine hand translations from `../recovered/readable_core.c`, with shared declarations moved into a C/C++ header; original comments and self-check preserved |
| `lib/board.c` | New translations of piece insertion and board reset, verified against assembly and the recovered initial-data table |
| `lib/game.c`, `.h` | Original move ordering, attack tests, king-safety filtering, castling, en passant, and promotions; function addresses in source |
| `lib/adjudication.c`, `.h` | Original move-chain repetition, reversible-move counter, computer resignation gates, mate/stalemate and exact terminal messages; [evidence](ENDINGS_EVIDENCE.md) |
| `lib/save_game.c`, `.h`, `lib/setup_board.c`, `.h` | Original 78-byte save data and settings, transactional native file I/O, original setup-validation order/messages; [evidence](FILE_SETUP_EVIDENCE.md) |
| `lib/book.c`, `.h` | Original opening tree traversal and RNG, connected to computer play and hints |
| `lib/evaluation.c`, `lib/search.c`, `lib/search_moves.c` | Original evaluation, selective search and specialized move order; [evaluation evidence](EVALUATION_EVIDENCE.md), [search evidence](SEARCH_EVIDENCE.md) |
| `lib/time_control.c`, `src/computer_player.cpp` | Original thinking budgets and native asynchronous computer coordinator; [time evidence](TIME_CONTROL_EVIDENCE.md) |
| `lib/modem_protocol.c`, `lib/modem_session.c`, `src/modem_host.h` | Original wire format and session behavior, POSIX serial transport and asynchronous native host; [evidence](IDLE_MODEM_EVIDENCE.md) |
| `src/main.cpp`, `src/setup_ui.cpp`, `src/resource_dialog.cpp` | SDL input/file pickers, original board-editor flow, resource dialogs, native undo snapshots |
| `lib/presentation.cpp`, `tools/original_tables.py` | Original hit tests and reproducible extraction of shape/position/color/menu tables |
| `tools/catalog.py` | Generates `build/assets.hpp` from the existing external-graphics manifest, validates frame references, and reopens generated output |
| `tools/save_interchange.py` | Wraps/unwraps save data in MacBinary with original Finder identity; bounds input, refuses overwrite and verifies saved bytes |
| `tests/board_check.cpp` | Initial board, insertion validation, piece-list relationships, display codes, and packed snapshot checks |
| `tests/catalog_check.py` | Rejects missing, escaping, and malformed asset references without replacing existing generated output |

Reference chain for the new translations (offsets are in the original executable file):

- `INSERTPI`, `0x57dc–0x5808`: write the piece and side bytes at `board + square*4`, retaining the list-index word. Native boundary checks reject invalid piece codes, sides, and squares rather than corrupting memory.
- Clear-board helper, `0x4c7a–0x4c8a`: clear `0x1e0` bytes at `A5-0x6c54`.
- `RESETGAM`, `0x5724–0x57be`: clear board; insert back ranks/pawns; rebuild piece lists; set side 0/opponent 1. The back-rank table at `A5-0x65e0` contains `3,5,4,2,1,4,5,3`.
- This is the board-reset routine, not the full NEWGAME/application reset flow. Unrepresented game state is not invented.

The application uses recovered `SETUPMSQ` display codes to select flat sprite indices. Visual inspection confirms `002.png` is a knight and `004.png` is a queen; older Swift notes reverse those two labels. Those unrelated files were not changed.

Private canonical evidence is `BattleChess.bin`, `dump.log` and `recovery_model.json` in the recovery workbench. Synthetic A5 addresses never become native pointers. New work here does not overwrite the original broad Ghidra export or readable C reference.

## Validation and limits

CTest checks cover recovered core/reset, ordered move generation, book traversal, graphics tables, catalog validation, and SDL input/rendering. Move checks include opening perft 20/400/8902, illegal move rejection, snapshot restoration, en passant, castling, promotion, and king attack detection. SDL smoke exercises e4, Take Back, and Replay through both board coordinate maps and promotion order, save/reopen and failed loads, setup validation/restore, New Game confirmation, and mate/stalemate alerts. Animation checks cover 27,832 graph geometries, all eight handlers, Fool’s Mate king-capture selection, 113 integrated movement/capture/turn/special cases (including both sides of all nonempty combat pairings and knight obstacles), and comparison of 4,424 rebuilt frames with the previously saved PNGs. New core checks cover repetition cycles and barriers, resignation thresholds, exact save byte layout and save/reopen, malformed-file rejection, and setup validation/history reset. The original save format contains no move history, so loading cannot restore historical repetition or castling rights. All assertions remain enabled in Release builds.

The opening book is embedded reproducibly from `ALLCANM1.data`. Novice searches depth two; other levels try the original book and then the recovered selective search. Suggestions use the original book/depth-two path. Evaluation checks independently compare all ten embedded tables with recovered DATA, including signed-word arithmetic and stale promotion scratch state. Search checks cover root RNG consumption, deterministic depth-limited results, legality, cancellation, Force Move, time limits and terminal scores. The worker integration checks book continuation, Novice, hints, Force Move and cancellation. See [development and provenance conventions](DEVELOPMENT.md).

These are assembly-backed translations and native checks. They do not prove identical move choices across a full original Macintosh session; clock scheduling, event polling, animation/audio timing and computer decisions still need broader comparison with the running original. The initial-scene match is recorded separately in [original-runtime evidence](ORIGINAL_RUNTIME_EVIDENCE.md). The retained generic animated-menu code is outside the normal Macintosh mouse path; native menus therefore add no artificial animation or RNG draws. See [Macintosh menu reachability](MENU_REACHABILITY_EVIDENCE.md). Capture fades share the computer RNG.

The preceding macOS Clang build recorded on 2026-10-03 passed all 31 address/undefined-behavior sanitizer CTests, including save transfer, native smoke, actual-host PTY checks and all 113 animation integration cases. Cocoa smoke and the separate real HFS transfer also passed. The `original_frame_viewport` check requires a 511×320 game area plus the native 20-pixel menu and compares all 163,370 original pixels at 2×, excluding the cursor. Its CTest fixture regenerates the native capture even when only that test is selected. This uses the saved original capture and is not a new original-executable run. The Linux baseline passed 29 CTests, X11 smoke and 113 animation cases before the later host/save changes; current source still needs a Linux rerun. Reproduction instructions, source hashes and dated records are in [PLATFORM_VALIDATION.md](PLATFORM_VALIDATION.md). Other Unix variants remain untested. Complete original-runtime equivalence and audible/timing equivalence are not established by these checks.

Current smoke and sanitizer commands are maintained in the
[native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md#checks-and-troubleshooting).
The counts above describe historical checks, not a fresh run of current source.

## Original font inputs

The historical reference used Chicago12 and Geneva9 bitmap resources extracted
from the System7 disk used for original-runtime comparison. FOND associations
establish the families and sizes; hashes are recorded in the
[font provenance](../recovery/SYSTEM_FONTS.md).

The current preparation command reads the supplied System MacBinary container
and writes these resources into the external pack. The
[preparation guide](../PREPARE_DATA.md#3-supply-the-original-files) defines the supported input;
fonts are not bundled in either source repository.

The installed modern Geneva strike is not assumed identical to System7. About's
sixteen original text runs fit their untouched clip rectangles using the recorded
bitmap pixels. These checks do not establish complete Control Manager or
QuickDraw raster parity; see [resource-dialog evidence](RESOURCE_DIALOGS.md).
