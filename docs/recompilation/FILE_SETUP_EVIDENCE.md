# Original Macintosh save and setup recovery

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

`tools/3rd-party/dump.log` is the assembly authority; recovered C helps locate routines.

## Data fork (78 bytes)

DOLOAD 0x90ca initializes read length to 0x4e (78), reads from offset zero into A5-0x14d8 (EB28) at 0x918e. DOSAVE initializes the same length at 0x91e2–0x91e4 and writes the same buffer at 0x92e0. Create uses creator `IPBC` and type `Game` at 0x929c–0x92a2. Finder metadata is not needed to decode the bytes, but DOLOAD's file picker filters for `Game` at 0x9100. The native macOS writer now adds that type/creator through `com.apple.FinderInfo` before committing its temporary data fork.

| Offset | Bytes | Evidence |
|---|---:|---|
| 0 | 40 | Opaque prefix; SAVEREQ does not populate it |
| 40 | 1 | Side to move, FILLSAVE called with EB50 at 0x8d4c |
| 41 | 32 | Two squares per byte, rank-major 0x88 traversal; high nibble first; piece bits 0..2, side bit 3 |
| 73 | 1 | Opaque/padding; FILLSAVE writes exactly 33 bytes |
| 74 | 1 | Level low byte, PUTSETTI called with EB72 at 0x8d58 |
| 75 | 1 | Bits 0..1 black player; 2..3 white player; 4 board mode; 5 AD96; 6 sound |
| 76 | 2 | Opaque trailing bytes |

PUTSETTI 0x7558 explicitly clears AD96 before packing, so save clears bit 5. GETSETTI 0x74b4 extracts it when loading. Original EXPANDSA resets engine state (0x57c8) and rebuilds lists; no move history is serialized. Therefore history, repetition and historical castling rights cannot be restored from this file.

Native `BCSaveFile` retains all 78 bytes. Encoding updates only original populated bytes, preserving opaque bytes from a loaded file; new files start zeroed. The recovered startup image at synthetic A5 address 0xfeb28 contains 78 zero bytes. This establishes the initial buffer image, not the meaning of its opaque fields or every later writer. Byte-layout compatibility of known fields and total size is established; an original-emulator load of newly generated files has not been performed. This is not a new JSON or custom format.

Native decoding additionally rejects wrong lengths, piece code 7, invalid side, and invalid setup boards before rebuilding lists. Output is unchanged on failed decode. File reads require exactly 78 bytes and report I/O errors. Native saves use a same-directory temporary file and rename only after successful metadata/write/close, preserving the previous target on failure. A macOS metadata failure returns failure before rename. The rollback branch has been reviewed but not fault-injected.

## Save transfer — 2026-10-03

[`save_interchange.py`](../../tools/recompilation/save_interchange.py) wraps or unwraps the data fork without re-encoding any board/settings/opaque byte. Export emits a MacBinary II container with a Mac Roman filename, `Game`/`IPBC` identity, 78-byte data fork, empty resource fork, header CRC and 128-byte padding. Ancillary Finder fields and dates are zero; this is a game-transfer adapter rather than archival metadata preservation. Import accepts the supported MacBinary header forms, verifies II CRC/version, identity, exact fork sizes and container length, then emits the original 78 bytes. The actual native game still validates the decoded position when opening it.

After cloning the tools at the permanent location, keep saves in `~/Games/BattleChess/saves/`. The export example assumes `native.game` already exists; import assumes `original-save.bin` was obtained from the original system:

```sh
BC_ROOT="$HOME/Games/BattleChess"
mkdir -p "$BC_ROOT/saves"
python3 "$BC_ROOT/repos/BattleChess-re-tools/tools/recompilation/save_interchange.py" \
  export "$BC_ROOT/saves/native.game" "$BC_ROOT/saves/transfer.bin" --name "Saved Game"
python3 "$BC_ROOT/repos/BattleChess-re-tools/tools/recompilation/save_interchange.py" \
  import "$BC_ROOT/saves/original-save.bin" "$BC_ROOT/saves/imported.game"
```

Use MacBinary mode when copying the container onto an HFS disk (`hcopy -m`), so the classic file receives its Finder identity for the original application's Open Game dialog. Each output path must be new: the command refuses overwrite, bounds its input reads, reopens the saved result and removes its own partial output on failure. Plain raw data copies lose Finder metadata when transferred through a filesystem or archive that does not preserve it.

The new CTest checks exact fork/header bytes, preserved opaque data, bad CRC/type/forks/length rejection, existing-output preservation and cleanup after a real size-limited partial write. The macOS save test verifies the actual 32-byte Finder attribute. An optional real HFS check uses installed hfsutils on a new writable copy of the canonical image, imports and exports the save through both raw and MacBinary modes, reopens all 78 bytes and verifies `Game`/`IPBC` in the returned header. It restores hfsutils' global `~/.hcwd` registry in `finally` and checks the canonical disk hash.

The optional [`save_interchange_check.py`](../../tools/recompilation_checks/save_interchange_check.py)
HFS mode requires a private workbench with canonical `source/macintosh/BattleChess.img`
and installed hfsutils. Its `--hfs-output` must be a new directory outside the source
checkouts. This mode temporarily updates and restores `~/.hcwd`; it is not part of
normal launch preparation.

Final macOS sanitizer checks passed 31/31; the separate HFS transfer also passed. This establishes native/container/HFS transfer. No original save was available, and no original-game session was run, so loading a native save in the original and an original-written save in the native app remain unverified. Logs and hashes are in [platform validation](PLATFORM_VALIDATION.md).

## Setup validation

CHECKBOA 0x6eb8–0x70c4 checks in this order: <=16 pieces for White then Black; no extra White then Black kings; a White then Black king exists; kings not adjacent; no pawn on rank 1 or 8; side to move must not attack the other king. It permits the moving side to be in check. It does not impose an eight-pawn limit or reconstruct promotion provenance. `bc_setup_validate` preserves this order and original English messages. Native malformed piece/side rejection precedes these rules to protect fixed-size piece lists.

Successful setup commit resets move history and rebuilds lists, corresponding to FUN_0x70ce (0x57c8 reset, CALCPIEC, clear ABCA). The assembly-based setup interaction recovery is recorded below.

## Checks run

Standalone clang C11 builds with `-Wall -Wextra -Werror` passed for `tests/save_game_check.c` and `tests/setup_board_check.c`, linked with save/setup/game/board/recovered_core. Save test independently asserts original initial-board nibbles, field offsets, total length rejection, preserved opaque bytes, settings flags, roundtrip board, real file save/reopen, oversized-file rejection and transactional malformed rejection. Setup test covers missing king, adjacent kings, end-rank pawn, wrong-side check, allowed current-side check, too many pieces, and cleared history after commit.

## Setup interaction recovered from assembly

BOARDSET 0x2d9c–0x339c is missing from auto-decompiled C but present in `dump.log`. Entry saves board bytes (480 bytes at 0x2efa–0x2f2a), temporarily forces board mode 1 (2D), swaps normal menus for setup menu 405, and disables File items 1/2/3/5. Exit restores presentation mode/menus. CHECKOPT setup case 0x5ade calls BOARDSET and then engine reset 0x57c8.

Palette drawing 0x2e2c–0x2ec0 emits six pieces in engine-code order 1..6, with visible-piece mapping from C3FE+1. Anchors are (30,30+40*i) for display-side 0 (engine black) and (474,30+40*i) for display-side 1 (engine white). Coordinates are original content coordinates; native host adds its 20-pixel menu offset when drawing and subtracts it for clicks. Use the existing original sprite anchor/hotspot handling.

The original sparse switch at 0x2f4c contains five command/offset pairs relative to 0x2f4c:

| Command | Target | Interaction |
|---|---|---|
| 0x1002 | 0x2f64 | Click board square: place/replace held piece and clear hand; otherwise pick up/remove existing piece |
| 0x1003 | 0x30fc | Discard held piece then test palette |
| 0x3000 | 0x3234 | Clear Board, after CHESSALE confirmation result 0x1003 |
| 0x3002 | 0x329e | Restore original board snapshot and clear hand |
| 0x3003 | 0x32e0 | Done: CHECKBOA; show error and remain, or restore normal menus and return |

Palette lookup uses `(y-20)/40` with signed truncation, row 0..5, y>0; x strictly between 15 and 45 for black or 455 and 487 for white. Original event handling clamps content y to at least 15 before dispatch. It scans 32 sprite slots before creating another palette piece (0x31bc). The helper models this as a board-piece count after discarding the previous held piece. The native capacity-error wording is not claimed as a decoded original string. No side-to-move control appears in this BOARDSET loop, so side is preserved.

`setup_ui.cpp` translates this state/input flow without SDL dependencies; host owns the original menu/palette and confirmation. `setup_ui_check.cpp` passed a strict C++17 build and tests pickup/drop, outside deletion, palette color/piece, capacity, clear, restore, validation on Done, and preserved side. Visual/editor integration is not covered by this standalone check.
