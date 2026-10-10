# Macintosh menus and the retained animated-menu routines

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

The original Macintosh menu path uses Toolbox `MenuSelect`/`MenuKey`. Adding
scrolling menu caps or their random sound draws to that path would change the
recovered behavior. The presence of MENUDOWN/MENUUP in the executable does not
establish that Macintosh menu clicks execute them.

## Executed Macintosh input route

All addresses below are original file offsets in `tools/3rd-party/dump.log`.

- USEPOINT `0x492c` calls export137 at `0x4930`; the recovered A5 jump table maps
  this to Macintosh HANDLEEV `0x10296`.
- HANDLEEV obtains Toolbox events at `0x102ac`. Command-key events use
  `MenuKey` at `0x10322`, then call HANDLEME `0x1055c` at `0x10328`.
- Mouse handling `0x103bc` calls `FindWindow`; the menubar case calls
  `MenuSelect` at `0x103f6`, then the same HANDLEME at `0x10402`.
- HANDLEME `0x1055c` dispatches the resource menu ID and item to Macintosh
  handlers, then clears the highlight with `HiliteMenu(0)` at `0x10604`.
  Those handlers write the pending command at A5:F0AA where appropriate.
- GETCOMMA checks F0AA at `0x291c`, clears it at `0x2928`, and returns it before
  entering generic GETMSG at `0x2934`.

## Why ordinary Macintosh clicks do not enter the animated-menu route

Generic menu mode A5:ADB6 is cleared at startup `0x266c`. Its only direct
nonzero assignment is `0x2c7e`, guarded by secondary-button flag A5:ADB8 at
`0x2c08`. The only direct assignment of 1 to ADB8 is `0x2a56`, the generic
button subtype **3** branch of the recovered switch at `0x2964`.

USEPOINT `0x4972–0x49c6` derives generic button subtypes from changed button
bits, iterating masks 1 and 2. Subtype 3 requires bit 1 set in A5:ADD8. The
Macintosh producers of ADD8 are exhaustively visible as four direct stores:

| Offset | Stored state | Reason |
| --- | --- | --- |
| `0x102b0` | 0 | Start polling |
| `0x102c2` | 1 | Toolbox `Button()` reports down |
| `0x1039c` | 0 | Inactive window |
| `0x1046c` | 1 | Content-window mouse down |

Thus normal Macintosh event production provides only 0/1 and cannot generate
subtype 3. Ordinary Macintosh menu selection never enters ADB6 and therefore
never calls generic HANDLEME `0xb51a` from `0x2bb0`.

This is a static proof for the recovered normal Macintosh mouse event path,
not a claim of absolute unreachability under memory corruption, arbitrary
injected generic messages, patched code, or an unexamined platform port.
No emulator execution or timing comparison was performed.

## Retained generic routine semantics (not enabled in the native host)

For future forensic comparison, the generic code establishes:

- MENUDOWN `0xa58c`: y starts at 25; x is heading coordinate minus 32;
  column count is `(longest_label_bytes >> 1) - 1`. If
  `x + columns*16 + 96 > 320`, x becomes `224 - columns*16`.
- Its loop at `0xa8e2` calls HANDLEME, increases y by 8, and reveals one item.
  EC96 (sound-active flag) is set only when opening finishes at `0xacea`.
- MENUUP `0xacfe` clears EC96 immediately. For DD56 <= 3000, its loop at
  `0xad1e` calls HANDLEME and decreases y by 8 until y <= 25. For DD56 > 3000,
  the code skips that loop and erases the objects directly.
- HANDLEME `0xb51a` does nothing when ED16 is 255. Otherwise it toggles ED1A
  and alternates shape indices 0/1 on the left and 2/3 on the right. Every
  second active call resets the byte counter ED28. Only if EC96 is nonzero
  does it call shared RNG export194 at `0xb602`, then PLAYSFX with C358,
  count 1 and pitch `(random & 3) - 5`. Muting output would not justify
  skipping that draw if this generic path were actually executed.
- The opening/closing loops contain no explicit clock delay. Generic steady
  updates are event-driven; USEPOINT `0x49d6–0x4a04` queues its periodic
  event only after elapsed ticks > 3. This does not justify assigning a
  fabricated fixed animation duration to each opening step.
- Referenced generic menu shape indices are 0–16, including border pieces
  4–10, heading pieces 11–14, and opening pieces 15/16. DELIGATE `0x116fa`
  initializes the external-board shape cursor to 17 at `0x11798`; existing
  external `standing` shape 0 is therefore original runtime shape 17, not
  generic menu cap 0. No substitution is valid.

CD74 is not evidence of dormancy: MAIN `0x2670–0x2674` assigns it to CD3C,
and board setup switches it at `0x2df6`/`0x3352`. The initial zero pointer in
the A5 image alone cannot establish runtime absence. Likewise, zero C358 or
B032 values in the initial image are only initial-state observations.

## Repeatable check

`python3 tools/recompilation_checks/menu_reachability_check.py` passes. It checks
actual machine bytes in `recovered/recovery_model.json`, the switch/jump-table
mapping, the four direct button-state writers in the disassembly, and all
0/1 button transitions against USEPOINT's subtype calculation. It validates
this source argument; it does not run the original Macintosh executable.

The native host should preserve the Macintosh resource menus and normal
selection/highlight semantics, with no generic rolling-menu sounds or RNG
consumption. A previously listed requirement to implement those animations
for Macintosh was based on function presence rather than input reachability
and should be removed from the Macintosh completion checklist.
