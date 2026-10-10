# Original selective search

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

`lib/search.c` translates the Macintosh search controller; it does not substitute a generic minimax implementation. The canonical evidence is `tools/3rd-party/dump.log`; `recovered/BattleChess_recovered.c` supplies a secondary reading, with its inferred pointer types checked against assembly.

| Original file offset | Native responsibility |
| --- | --- |
| `0x160b4` FINDMOVE | Iterative depth, aspiration lower bound, fail-low repeat, mate-mode depth steps, stopping |
| `0x16246` | Thinking-time gate (native monotonic clock replaces the Macintosh timer) |
| `0x16280` CLEARKIL | Two killers per ply and initial advanced-pawn squares |
| `0x16376` CALLSEAR | Root candidate count and terminal score |
| `0x163f2` SEARCH | Copied frame state, quiescent stand-pat, mate/stalemate score, killer update |
| `0x16592` SEARCHSE | PV, previous-target captures, killers, remaining target captures, pawn extension, castling/quiet moves, en passant |
| `0x168d0` SEARCHLO | Full/null windows, re-search, best/PV updates and original four-point adjustment |
| `0x16c86` SEARCHUP | Original two-slot killer replacement rule |
| `0x16d82` SLBGB | Duplicate suppression between generation phases |
| `0x16e4c` SLBUC | Static score pruning while retaining the best rejected score |
| `0x16e8e` SLBU | Shallow capture pruning, STATEVAL delta, check/pawn extensions, legality, root RNG |
| `0x1738e` SLBDG | Repetition cutoffs and reversible-move root-score adjustment |
| `0x17482` | Copy child principal variation and record the current move |

The 24 original search frames have named fields corresponding to offsets `0x00..0x1e` and a 24-move child line at `0x20`. Native pointers do not reproduce the physical 68k layout. Search keeps all 103 retained game-history entries plus up to 24 hypothetical moves for FIFTYMOV/REPETITI; the ordinary game snapshot remains sufficient for move generation and undo.

CALCPVTA tables are fixed at the search root. STATEVAL runs before applying each candidate, with the current root score (`A5-0x5374`) as its capture reference. Pawn-state slots remain alive across siblings and iterative depths. The original root-only LCG is shared with opening-book selection through the caller-owned state. Initialized advanced-pawn rank starts `(96, 16)` were read from recovered A5 address `0xff76c`.

The move callbacks are the separately translated SEARCHSM routines in `lib/search_moves.c`. `bc_game_search_apply` preserves list holes/indices and restores rejected positions. Search takes/restores complete native snapshots in place of the original reverse-PERFORM path; this does not reorder the list.

Native differences: clock/poll callbacks replace Toolbox/menu calls; explicit cancellation returns a result flag, and FINDMOVE returns instead of waiting in the original command loop. A timeout is ignored within the first iteration, then checked between iterations and after completed candidate evaluation. No artificial node cap is added. Depth-only checks use null clock callbacks.

Validation in `tests/search_check.c`: exactly 20 original LCG draws for the initial depth-one root, repeatability from identical state/seed, legal depth-two selection, untouched caller position/history, cancellation, mate score `-32000` and stalemate score zero. The standalone check passed with AddressSanitizer and UndefinedBehaviorSanitizer. These are native translation checks, not a full original-CPU trace comparison or GUI acceptance.

The optional caller-owned `BCSearchSession` preserves pawn scratch slots across FINDMOVE invocations, including cancelled searches. Only the root slot is replaced from CALCPVTA. This retains STATEVAL's stale-slot promotion behavior. Passing a null session intentionally requests fresh scratch state for isolated deterministic checks; the computer-player host should retain one session across moves and new games.

The native game record reserves all 127 original history slots: 103 committed moves plus 24 hypothetical plies. Search appends without shifting the committed history, so CALCCAST retains old king/rook move barriers throughout a deep search. Committing a computer result uses a separate trusted move entry point with the normal 103-entry retention rule. The regression checks both boundaries and rejects overflow transactionally.

The host follows CHECKOPT (`0x58bc`), RETURNAN (`0x5c38`) and FINDHINT (`0x6794`). Take Back and Replay leave computer play paused. LOADREQ calls EXPANDSA before GETSETTI: the loaded side's pre-load player setting determines the pending computer request (`0x6e8a..0x6ea8`), then saved settings replace player controls. This unusual ordering is preserved rather than silently corrected. Equal-mode resignation is checked after committing the move and before starting its animation.

PRINTHIN (`0x66d0`) runs twenty two-tick source/destination outline phases. SETAPEN (`0xbec4`) and DRAWBUFD (`0xbe32`) supply the original absolute-x pixel pattern; source changes before the delay, destination afterward. Native hint helpers and boundary tests preserve this sequence.

Book, search and captured-piece fades share the original initialized RNG state (`0xffd14`, value 1). FADESHAP consumes fifteen draws per fade (`0xbc7a`). Native search works on a private RNG copy and publishes it before playback begins; the UI does not run capture animation concurrently with a search. The retained generic HANDLEME consumes random draws for animated-menu sound pitch (`0xb602`), but the normal Macintosh mouse adapter cannot enter that secondary-button menu route. Macintosh menus use Toolbox MenuSelect/MenuKey. The native port therefore correctly adds no menu RNG draws; see `MENU_REACHABILITY_EVIDENCE.md`.
