# Original resource dialogs

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

`original_tables.py` reads the resource inventory and slices the verified Macintosh binary. It validates each resource span, DITL item count, record/payload alignment, rectangles, and DLOG title bounds. Generated `OriginalDialog` retains DLOG/ALRT identity, absolute bounds, DITL reference and item indices. `OriginalDialogItem` retains type/disabled bit, original text, picture ID and item-relative rectangle.

Important original mappings:

| Resource | DITL | Role |
|---|---|---|
| ALRT402 | 29019 | OK/Cancel with parameter0/1 |
| ALRT406 | 406 | OK with parameter0/1 |
| ALRT400 | 400 | About: PICT10001 plus version1.0.2 |
| DLOG408 | 409 | Promotion: pictures400,401,402,403 |

ALRT401 references absent DITL1; generation preserves zero items rather than fabricating controls. About's picture is disabled type0xc0; promotion pictures are enabled type0x40. Promotion picture rectangles overlap at absolute x184..185; item-list order selects item3 there. Rectangles use left/top inclusive, right/bottom exclusive.

Original Pascal messages are extracted and length-checked at original file offsets: clear board0x1f4, game over0x20e, new game0x3f0; checkmate and stalemate are located in the original message block by exact encoded contents, with generated offset constants. No modern confirmation wording is substituted.

PICT10001 is decoded reproducibly from the binary. Supported original opcodes are explicitly checked: v1 version, short/long comment, rectangular clip, font/size/fontname/glyph state, white pen pattern, PaintRect, positioned/delta text, PackBitsRect and end. Its single bitmap has24-byte rows, bounds(161,204,261,396), source(161,206,261,394), destination(0,26,100,214), srcOr mode1. Every PackBits row is checked for exactly24 decoded bytes. The188x100 MacPlay artwork is original pixels; sixteen nonempty text runs retain original positions and clipping rectangles. The picture frame(-1,-1,252,240) maps directly into the241x253 DITL destination.

`resource_dialog.cpp` draws original geometry and bitmap, substitutes ^0..^3, and provides item hit testing. Dialog text uses recovered Chicago12; About text uses recovered Geneva9. Fonts remain separate System resources because the application embeds no FONT/NFNT/FOND. Pushbuttons use the recovered System7 corner diameter and QuickDraw circular raster; alert default rings and the System stop icon are drawn from the evidence below.

## Bitmap typography recovery, 2026-09-27

PICT10001 extraction preserves every run's `TxFont`, `TxSize` and `FontName` state: all sixteen nonempty runs use font3, Geneva, size9. Baselines and clip rectangles are unchanged. The two original bitmap resources now live in `lib/fonts/`; their System7 provenance, hashes, FOND associations, and reproducible extraction command are recorded in [the font input manifest](../recovery/SYSTEM_FONTS.md).

`tools/system_fonts.py` resolves the named FOND families and plain point-size associations inside a supplied System MacBinary. Chicago family0/plain12 selects NFNT5478 with ascent/descent/leading12/3/1. Geneva family3/plain9 selects NFNT4372 with metrics10/2/0. `tools/bitmap_fonts.py` validates FontRec bitmap dimensions, bit locations and offset/width records, preserving source pixels and advances. UTF-8 resource text maps back to Mac Roman, including copyright and registered symbols.

The optional installed `/System/Library/Fonts/Geneva.ttf` path is also supported through Apple's [bitmap location](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6bloc.html) and [bitmap data](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6bdat.html) formats; no outline rasterization occurs. Investigation found identical relevant text advances but different i/l/y bitmap pixels between the installed modern strike and System7. Therefore the recovered System7 resources are the default inputs. Generated `bitmap_fonts.hpp` records input hashes and is reproducible from those bytes. Explicit raw FONT/NFNT overrides must already be the requested face/size: FontRec alone has no family/size identity.

All sixteen About runs' actual set pixels fit their original clip rectangles. The first line's advance ends at x225, exactly the original clip edge; the five right-aligned labels end at x134, also exactly their original edge. `resource_dialog_check` asserts every set pixel is within its original clip, checks font metadata, malformed UTF-8 rejection and clip restoration. `bitmap_fonts_check.py` checks raw NFNT row packing/bearings, malformed bounds, recovered input hashes/metrics, and unavailable-input behavior. Fresh System extraction compared byte-for-byte with both saved font files. Strict C++17 `-Wall -Wextra -Werror` plus ASan/UBSan passed with recovered fonts and with a separately generated unavailable-input fallback. The software-rendered System7-font About image was reopened and inspected: all credits and both copyright symbols are legible.

The exact recovered System7 font pixels are now used; this establishes the font-input provenance and removes the observed clipping defect. It does not establish full Toolbox control/window raster parity. If explicit build font inputs are disabled, SDL remains an honestly identified fallback.

## Recovered controls and stop icon

`RINGBUTT` at original file0x10e0e reads the dialog default item from offset0xa8, returns when zero or when its exact DITL type is not4, calls `PenNormal`, sets a3x3 pen, expands the item rectangle four pixels on every side, calls `FrameRoundRect` with ovalWidth16 and ovalHeight16, then restores `PenNormal`. `STANDARD` at0x10d42 calls it for the dialog update event. This ring is distinct from the standard button body.

All recovered ALRT resources have stage word0x5555. Each nibble's bit3 selects default item minus1, bit2 requests visibility and bits1..0 select sound, per Apple's [original Dialog Manager resource format](https://ftpmirror.your.org/pub/misc/bitsavers/pdf/apple/mac/developer/Prerelease/Programming_Macintosh_Applications_in_Assembly_Language_Feb84.pdf). Thus402/406/407 use item1 in every stage. The generator preserves this word and rejects varying stage defaults rather than inventing stage tracking. Ring selection uses the recorded default, with exact type4 gating; it does not scan for an arbitrary enabled button.

System7 CDEF0 is compressed with dcmp2. `system_fonts.py --control-code` decodes it reproducibly using the dictionary inside the same System's dcmp2 resource. Compressed CDEF0 SHA-256 is `27fcc23be9d09e6ef5aeb05155c949e0e7c7fc7c9911b43770a7b222989bb26f`; decoded1350-byte SHA-256 is `b647566a3fe540ae1e2477e6c3ced3d3a33cfffc131fcd8fbfa22c5774cc0dde`. At decoded offset0x3da, pushbutton corner width and height are both half the control rectangle's height;0x31a calls `FrameRoundRect`. Text positioning at0x202..0x270 measures GetFontInfo/TextWidth and centers using the recorded font metrics.

The [Apple-authorized QuickDraw source release](https://computerhistory.org/blog/macpaint-and-quickdraw-source-code/) was inspected in a temporary download: archive SHA-256 `fd609319e4a530995673440dadf0a6b75fc8322f2b96fec1d37ed890c2275b46`. `RRects.a` routes framing to `DrawArc`; its `InitOval`/`BumpOval` equal-axis recurrence gives the integer extent `floor(sqrt(d*d - ovalY*ovalY))`. `quickdraw_control.h` implements that circular case and subtracts the pen-inset inner shape. It does not approximate arcs with floating-point polygons or claim general oval support.

The saved booted original New Game confirmation (private workspace: `docs/recompilation/evidence/original-new-game.png`) (SHA-256 `bf0f132d3c546a72dfa0e6202ae4767981e064cc08daaaff859ee36c5249e459`) independently validates the raster: the stored28-row,8-column left-corner sample at screenshot x216..223/y246..273 and its reflected right side match all448 tested pixels of the native ring plus button. These samples cover both upper/lower corner transitions, pen thickness and the one-pixel gap. Separately, all1024 pixels of System ICON0 match the screenshot at content-relative(20,10). The port draws that32x32 hand for ALRT402/406, whose StopAlert calls are at file0x3b10/0x3b22, and407, whose modem StopAlert calls are at0x7990/0x7a60. About400 uses its own recovered PICT and receives no stop hand.

`resource_dialog_check` verifies the corner samples, font bounds, ALRT stage words and rendering. Full original window-frame chrome, pressed/disabled control feedback and general Toolbox rendering remain outside these narrowly validated components. The application uses native dialog layout and hit routing, not an emulated Dialog Manager.

## Native pushbutton capture and release — 2026-10-03

The original SETTIME calls ModalDialog at file0x3894, DIALNUMB at0x39ea and SENDMESS at0x3cee. STANDARD at0x10d42 supplies update/default-ring and keyboard filtering while the Dialog Manager handles mouse tracking. `ResourceDialogButton` adapts that boundary for SDL: press captures only an enabled exact-type4 item; release returns the item only inside the same button of the same active dialog, then clears capture. Leaving and returning before release is allowed. An outside release or another button does not complete the dialog. Focus loss, dialog replacement and keyboard completion cancel pending input. Editable fields and enabled promotion pictures keep their existing independent handling; disabled About picture items cannot capture a button.

The resource check covers same-button release, repeated release, replacement, explicit cancellation and disabled pictures. Native smoke covers outside/other-button cancellation, re-entry, custom-time completion and queued SDL down/up/focus-loss events through the normal dispatcher. Removing focus-loss cancellation makes the queued-event regression fail at the expected confirmation-state assertion. All 30 macOS sanitizer CTests and the Cocoa smoke passed after restoring the handler. These establish native routing, not physical OS event delivery or original-runtime equivalence.

The adapter adds no pressed/disabled raster. STANDARD's Return-key path separately invokes HiliteControl at0x10eb8, waits eight ticks and clears the highlight; that timed feedback is not implemented in this pass. The current static control-pixel comparisons do not validate those states. Source identity and captures are recorded in [platform validation](PLATFORM_VALIDATION.md).
