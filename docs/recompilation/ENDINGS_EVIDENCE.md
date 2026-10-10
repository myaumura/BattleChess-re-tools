# Original Macintosh endings and repetition

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

Sources: `recovered/BattleChess_recovered.c`, checked against the literal 68000 instructions in `tools/3rd-party/dump.log`. Message text was checked against `source/macintosh/BattleChess.bin`. These routines do not implement modern FIDE claim/automatic-draw rules.

## Move history predicates

`REPEATMO` (`0xc60c`) accepts exactly `special == 0 && captured == 0 && piece != 6 && piece != 0`. Castling/special records are barriers, as are pawn moves, captures and the zero-piece sentinel. `FIFTYMOV` (`0xc670`) counts backward until this predicate fails. The native history keeps the original 103-record window; no independent halfmove clock is needed.

`REPETITI` (`0xc6bc..0xc8ea`) starts its count at one and walks piece source/destination chains backward on alternating plies. At each current destination it skips the piece if that destination is the source of a later same-side move; otherwise it follows that piece backward until its source returns to the destination at the candidate boundary. Odd candidate intervals are shortened by one ply, restarting the piece scan. It counts repeated intervals, stopping at a non-repeatable record. This is a literal move-chain translation, not board hashing, and deliberately does not add castling rights or en-passant position fields. The nonzero parameter limits the initial reversible scan to four records; original search uses that short cycle test.

The implementation shifts the original history coordinates so `end == history_count`, current record is `end-1`, and the zero-piece sentinel is the lower bound zero. The assembly at `0xc768` decrements the current index before reading it; `0xc898` restarts the scan whenever the candidate boundary moves, even if its distance is already even. Both details are preserved explicitly.

## Caller gates and exact messages

| Original call path | Condition and result |
| --- | --- |
| `READOPTI 0x5812` | `FUN07128` finds no legal move, then calls `DOCHECKM`. Otherwise stores the attack/check flag and accepts human input. |
| `CHECKOPT 0x58bc`, human move case `0x5a52` | Enters/stores/animates the move. If the next side is computer, schedules search; otherwise calls `FUN07128` then `DOCHECKM` only on no legal move. No repetition/fifty gate. |
| `CHECKOPT`, board setup case `0x5ade` | Resets the current move marker via `FUN057c8`; schedules computer or performs the same no-legal-move test. |
| `RETURNAN 0x5c38`, no chosen piece | Routes to `DOCHECKM` except the distinct unequal-mode/no-previous-move reset path. |
| `RETURNAN`, chosen move, equal player modes | First enters/stores the move, then requires total ply counter `<120`, `FIFTYMOV()<100`, `REPETITI(0)<3`, and score `>-0x880` to continue animation/search. Any failed condition shows resignation and resets after acknowledgement. |
| `RETURNAN`, chosen move, unequal player modes | Animates/promotes, then calls `FUN07128` / `DOCHECKM`; no repetition/fifty resignation gate. |
| `DOCHECKM 0x716a` | Caller establishes no legal moves. If opponent does not attack current king: stalemate. Otherwise `BUILDCHE`, side swap, and presentation-only king capture, then mate message. Both wait and reset. |

The normal equal-mode computer-result case is computer/computer. Human/human play does **not** acquire an automatic threefold or fifty-move result merely because both mode numbers are equal: its caller never enters `RETURNAN`.

| Message offset passed to CHESSALE | Pascal string file offset | Exact text |
| --- | --- | --- |
| `0x282` | `0x406` | `Black resigns` |
| `0x2a0` | `0x424` | `White resigns` |
| `0x458` | `0x5dc` | `Check and mate.` |
| `0x468` | `0x5ec` | `Stalemate. How boring!` |

Resignation selects `0x282` when the side-to-move **after** the entered move is zero, otherwise `0x2a0`. This counterintuitive presentation is retained. There is no separate automatic draw message in this path. Check is a continuing position flag, not a terminal condition.

The total counter is `A5-0x5438` (`DAT_000fabc8`): new game `0x5692` zeros it, `MAKEMOVE 0x6290` increments it and `TAKEBACK 0x62d0` decrements it. It must be supplied independently from capped history length to `bc_computer_resignation`.

## Search use

`SLBDG 0x1738e` also calls these predicates. At search ply one, three repetitions zero score field `+0x1a` and terminate that node. Otherwise it adds `(DAT_000ff0a6 / 4) * multiplier` to fields `+0x18/+0x1a`: multiplier three for quiet count >=96, else two for repetitions >=2, else one for quiet count >19, else zero. Beyond search ply two, `REPETITI(1)>1` zeroes `+0x1a` and terminates the node. These are search evaluation gates, not human-game adjudication.

## Native state and validation

The predicates derive their result only from `BCGame.history`; full `BCGame` undo snapshots therefore restore repetition and reversible counts together with the board. The original 78-byte save format contains no history: EXPANDSA resets the current move marker when loading, so native load and board setup establish empty/current-sentinel history. Neither operation invents historical repetitions from a board image. See FILE_SETUP_EVIDENCE.md for the recovered save layout.

`tests/adjudication_check.c` covers two legal knight cycles (counts two/three), short search mode, pawn/special barriers, undo restoration, the 100-halfmove gate, exact 120-ply and -2176 score boundaries, side-specific resignation IDs, Fool's Mate, and stalemate. Standalone C11 compilation with `-Wall -Wextra -Werror` and execution passed. This does not claim execution of the original Macintosh application or UI acknowledgement/reset behavior.

Native integration: `main.cpp` waits for the recovered king-capture animation before presenting the exact mate message. Acknowledgement resets the board, matching `DOCHECKM -> WAITTOEN -> FUN_00005692`; stalemate follows the same acknowledgement/reset path. The expanded SDL smoke check exercises both endings and asserts the reset. Computer-only resignation gates remain disconnected until the original computer player is translated.
