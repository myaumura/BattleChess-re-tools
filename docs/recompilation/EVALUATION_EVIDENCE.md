# Original static evaluation

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

`tools/3rd-party/dump.log` is the instruction authority. `recovered/BattleChess_recovered.c` identifies function boundaries; its formulas were checked against the disassembly, including signed word operations and two unusual control-flow paths. No replacement chess heuristic or fitted weights are used.

`lib/evaluation.c` translates CALCPVTA (`0xe696`), both PAWNSTRV routines (`0xf5c2`, `0xf5fe`), PIECEPOS (`0xf69e`), and the STATEVAL routines (`0xf6f2`, `0xf7e4`, `0xf94c`). The no-op at `0xfc2c` is not needed by these entries.

## State and integration

CALCPVTA runs once at the search root. It builds two sets of six 120-square signed-word positional tables at original `A5-0x5f88` (`0xfa078`), computes material total/pawn material/balance/phase (`0xfede4..0xfedea`), the special-endgame flag (`0xfeeb4`), initial pawn-file masks, and the side-to-move score (`0xfede2`). These tables stay fixed through the search. Recomputing them for every child would change the algorithm.

`BCEvaluation.root_side` represents `0xfabc2`, which the caller supplies separately from the position's current side. CALCPVTA's king-neighborhood adjustment uses only the kingside bit from CALCCAST (`0xc4dc`), supplied by `bc_game_castling_rights`; blocked paths and attacked transit squares are not part of that flag.

STATEVAL executes before PERFORM. It returns the score gained by the moving side, accounts for captures/castling/en passant/promotion, and updates a separate next-ply pawn-mask record. Its capture adjustment uses current global `0xfac8c`, not the parent static score. FINDMOVE initially assigns the root score to that global and changes it during iterative search.

The native `BCPawnState` uses named arrays instead of the original interleaved memory layout. Each record still holds the original four 16-bit masks: occupied files and doubled files for each side. Callers retain distinct previous and next records, and retain scratch records between siblings and searches. CALCPVTA clears only the root record; it does not clear higher-ply masks.

## Original constants

All arrays below are exact big-endian signed words from the initialized `A5_globals` block in `recovered/recovery_model.json`. `tests/evaluation_data_check.py` independently decodes that block and compares every embedded word.

| A5 model address | Native table | Original words |
|---|---|---|
| `0xfed70` | material | 0, 4096, 2304, 1216, 768, 768, 256 |
| `0xfed7e` | centrality | 3, 2, 1, 0, 0, 1, 2, 3 |
| `0xfed8e` | pawn rank | 0, 0, 0, 2, 4, 8, 30, 0 |
| `0xfed9e` | passed rank | 0, 0, 10, 20, 40, 60, 70, 0 |
| `0xfedae` | pawn file | 0, 0, 2, 5, 6, 2, 0, 0 |
| `0xfedbe` | castling bonus | 4, 32 |
| `0xfedc2` | attack rank | 0, 0, 0, 0, 1, 2, 4, 4 |
| `0xfedd2` | file masks | 1, 2, 4, 8, 16, 32, 64, 128 |

Direction arrays at `0xf99e0` and `0xf99f0` are also compared by the check. Addresses in this table are initialized-memory addresses, not code/file offsets.

## Preserved instruction-level details

- `0xe784..0xe79c`: material-minus-8192 wraps as a signed word before MAX and signed division by 256. Material accumulation and positional arithmetic likewise preserve word writes. `word` and `shift_word` express this without signed C overflow or depending on the host's negative right-shift behavior.
- `0xea42..0xeb42`: sliding scores include the blocking square, then halve subsequent square contributions after a blocker other than queen or the matching slider. Pawns stop the scan. Slider color is not tested.
- `0xec1e..0xec26`: the special-endgame king-distance expression masks the complete sum: `(square - enemy_king + abs(rank_difference)) & 7`. It is not replaced with Manhattan distance.
- `0xf330..0xf3c2`: the apparent passed-pawn rook-bonus loop initializes its global index to one, then tests whether it is at most zero. Its body is unreachable; the native translation does not invent a rook bonus from that dead body. The scratch-global write has no value read by the evaluator/search interface.
- `0xfa2a..0xfa82`, followed by `0xfafa..0xfb38`: promotion removes a pawn from the **old next-ply mask** to compute its structural delta, then copies the previous record over that modification. The resulting next masks still contain the previous pawn file. Two identical promotions with different stale next masks can score differently; a regression check preserves this behavior.
- `0xfabe..0xfaec`: non-pawn capture adjustment starts at absolute reference score **256 inclusive**, with the original root-side/sign comparison.
- Pawn masks approximate files, not per-file counts. Three pawns on one file remain represented by one occupied bit and one doubled bit. Incremental updates retain this original limitation.

## Validation and limits

`evaluation_check.c` passes a standalone Clang C11 build with `-Wall -Wextra -Werror`, AddressSanitizer, and UndefinedBehaviorSanitizer. It checks initial root material/phase/score, independently derived pawn-square values, quiet-move delta, isolated/doubled penalties, special-endgame king formulas, capture-sign thresholds, castling bonuses, en passant masks, and stale-slot promotion ordering. `evaluation_data_check.py` passes the independent original-byte comparison for all ten tables.

These are assembly-backed native checks. An independent execution comparison against original 68000 evaluation code has not run: the available `m68kexec` binary exits with SIGKILL, including an ad-hoc-signed temporary copy; the local upstream source lacks the `phosg` build dependency. No original-machine or emulator equivalence is claimed from the native tests alone.
