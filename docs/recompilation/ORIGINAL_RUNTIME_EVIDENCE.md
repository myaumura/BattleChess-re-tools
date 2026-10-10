# Original executable comparison — 2026-09-27

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

The canonical Macintosh game was booted in [Infinite Mac's System 7.0 / Mac IIx configuration](https://infinitemac.org/1991/System%207.0?machine=Mac%20IIx&saved_hd=false), using Mini vMac, a 68030 Mac IIx, 32 MB RAM and a 640×480 display. This is original executable execution, separate from native CTest results.

The macOS update on 2026-10-03 retains these as recorded 2026-09-27 original observations. A fresh native Cocoa capture was compared with the saved original; no new emulator session was run. Stable gameplay comparison still requires investigation of the failures below; next steps and acceptance checks are in [the remaining recovery plan](REMAINING_RECOVERY_PLAN.md).

## Inputs and reproduction

Use a temporary copy of `source/macintosh/BattleChess.img`, load it with the emulator's **More → Load Disk**, open the mounted BattleChess disk, and launch **Battle Chess**. Disable Saved HD to avoid retaining test changes. The canonical image was not mounted for writing or changed.

SHA-256 of the image and the temporary input copy:

`ba1b3758368c032f6f8475e8bebd07db60c8736c12049ee64785f84356d50af5`

SHA-256 of canonical `source/macintosh/BattleChess.bin`:

`091d8088d305fe16ae45b60fd3f83ca36e6650e5a8c0a63b6e876cfe4fc32922`

The online System disk is Infinite Mac's curated System 7.0 image, not a claim of a pristine historical installation. Its downloaded sparse-disk reconstruction had SHA-256 `48b9f967e9665df4e0cf03fb9654de94931806e3b35fdc1f9fd7c7cf462ef856`. System font resource provenance is recorded in [lib/fonts/README.md](../recovery/SYSTEM_FONTS.md). The System disk and ROM are not added to this repository.

Firefox 156.0.1 ran in an isolated temporary profile. WebDriver BiDi drove real pointer events and captured the emulator canvas. Mouse-down was held for 120 ms so the emulator could observe it. The saved PNGs below were reopened for inspection.

## Observed comparisons

- Original initial board (private workspace: `docs/recompilation/evidence/original-initial.png`): original content starts at screen `(64,90)`. All **163,370 checked content pixels** match the native initial frame, including every physical pixel of native 2× scaling. Only the original mouse cursor rectangle `(20..29,18..32)` relative to the content is excluded. The comparison checks RGB, not just brightness.
- Original New Game confirmation (private workspace: `docs/recompilation/evidence/original-new-game.png`): shows the System stop icon, Chicago text, rounded pushbuttons and default-button ring. The native control regression uses the captured left/right button and ring corner pixels; the recovered System `ICON0` matches the original 32×32 icon. See [resource dialogs](RESOURCE_DIALOGS.md).
- Original menus visibly use System MenuSelect tracking. Dragging across another heading changes the active menu. Static reachability and the native implementation are documented in [menu evidence](MENU_REACHABILITY_EVIDENCE.md).

The comparison tool is [`compare_original_frame.py`](../../tools/recompilation/compare_original_frame.py).
It requires a native screenshot and an original capture supplied with `--original`;
the private reference PNG is not bundled. Current build and SDL check commands
are in the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md#checks-and-troubleshooting).

The first screenshot is the initial board. The script validates PNG checksums, decodes RGB/RGBA scanline filters with Python's standard library, and compares all unoccluded pixels at integer scale. `--exact-viewport` also requires the original visible content size plus the native 20-pixel menu; the default retains support for older 512-pixel-wide captures. It does not compare subsequent smoke frames.

The original default WIND400 resource, at file offset 131875, has rectangle `(top=20,left=0,bottom=340,right=511)`, hence a **511×320** content area. WINDOWIN `0xff6c..0xffcc` obtains it through GetNewWindow at 0xffa8, then centers and moves it. Before 2026-10-03, the native host exposed a 512×330 board area. It now derives the visible port dimensions from WIND400 and clips the unchanged 512×330 images at that boundary. The existing native 20-pixel menu yields a 511×340 logical surface and a **1022×680** initial 2× screenshot. Fresh macOS sanitizer and Cocoa runs passed the strict viewport comparison. Native OS window chrome, menu geometry and desktop positioning remain separate adaptations; the pixel-match claim covers original visible game content only.

## Limits and emulator failures

Opening About in this Mini vMac configuration produced an illegal-instruction System error (private workspace: `docs/recompilation/evidence/original-about-failure.png`). That capture is a failure, not a successful About comparison. A second attempt using Infinite Mac's Mac IIfx / Basilisk II with its default 128 MB RAM reached the title but displayed “Setup se Out of memory.” (private workspace: `docs/recompilation/evidence/original-basilisk-startup-failure.png`). The causes were not diagnosed; neither failure is attributed to the native port.

A second Mini vMac run accepted e2–e4 input and entered the walking animation, but did not yield a completed stable turn during this observation. No move-choice or timing parity claim is based on that run.

Initial rendering, the observed menu interaction and the captured confirmation do not establish full parity. Computer move choices, animation and audio timing, long-session RNG/event ordering, save interchange, modem interoperability and remaining Toolbox states still need original execution comparisons. Idle assets remain recovered without a proven trigger; no invented idle timer was added.
