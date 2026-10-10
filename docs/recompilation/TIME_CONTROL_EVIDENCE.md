# Original thinking-time controls

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

`lib/time_control.c` translates the budget portion of SETLEVEL (`0x6838`) and SETTIME (`0x381e`), using executable file offsets from `tools/3rd-party/dump.log`.

Novice selects six seconds and depth two. Fixed levels 1–9 select `5 << (level - 1)` seconds. Custom level 10 opens DLOG/DITL 403, raises a sub-minute current budget to one minute before displaying whole minutes, clamps accepted input to 1–10,000 minutes, and stores seconds. The working search budget has a three-second floor (`0x68f0..0x6910`); the rest of that helper's search-state initialization belongs to the search coordinator.

The original save format records only the level byte. Loading custom level 10 therefore opens the time dialog again, following GETSETTI (`0x74b4`). Native text editing and SDL focus handling replace Toolbox edit controls. The original dialog has an OK button and no Cancel button.

`tests/time_control_check.c` checks every fixed level, clamps, minute conversion and the search floor. The SDL smoke check exercises menu selection, text editing, acceptance and reopening the custom-time dialog after save/load. These checks do not establish original Toolbox typography or original executable timing parity.
