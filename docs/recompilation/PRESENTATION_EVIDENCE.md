# Original presentation evidence

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

Read-only investigation of recovered C, original disassembly `tools/3rd-party/dump.log`, and initialized bytes in `recovered/recovery_model.json`. Addresses below use recovered virtual addresses; A5 is `0x100000`, so e.g. `0xff314` is A5 minus `0xcec`. File offsets name original functions. No runtime execution of the original application was used for this investigation.

## Static board and piece rendering

`LOADBOAR` at file `0x117fe` chooses perspective when word `0xfc3f4` is zero and flat otherwise. It assigns x-anchor pointer `0xfcdb8`, y-anchor pointer `0xfcdbc`, hit-row pointer `0xfcdc0`, hit-column pointer `0xfcdc4`, and shape selector pointer `0xfcdc8`. `LOADSCRE(0)` selects perspective background and `LOADSCRE(1)` flat background. Storage is 512 by 340 at stride128 bytes; `RENDERSH` at `0x9c74` clips visible shape y to 0..329.

`SETUPMSQ` at `0xfc2e` fills display bytes `0xfcd78[64]` from engine records `0xf93ac + engineSquare*4` (piece byte0, color byte1):

```text
engineSquare = (displaySquare & 7) | (((displaySquare*2)&0x70)^0x70)
type = [0,2,5,6,1,3,4,0][enginePiece]
if type == 6: orientation = file<4 ? 3 : 7
else if type == 1:
    orientation = file<4 ? (color==0 ? 1 : 3) : (color==0 ? 7 : 5)
else: orientation = color==0 ? 0 : 4
displayByte = type==0 ? 0 : type | (orientation<<3) | ((color==0)<<6)
```

`PLACE` at `0x12fee` visits displaySquare0..63, selects global shape `shapeLUT[displayByte&0x3f]`, and calls `ANIMSHAP` at `0x9bc4` using xAnchor[displaySquare], yAnchor[displaySquare>>3], displayByte&0x40. Global static shape base is17 (`DELIGATE` at `0x116fa`), so standing/flat archive local index is global index minus17. Shape values99 are sentinel entries for impossible display combinations, not real standing indices.

`RENDERSH` at `0x9c74` places upper-left at anchor minus signed byte hotspots (metadata bytes2,3). `INSERTFO` at `0x9b50` sorts ascending anchor y and inserts before an equal y; since PLACE inserts ascending displaySquare, the resulting static draw order is ranks top-to-bottom and files h-to-a within each rank. `SHAPES2D` at `0xa072` composites in that linked-list order.

## Original 2-bit pixels and opposing side

Packed pixels are high pair first. Monochrome LUT at file `0x855c`: state1 is black; states0,2,3 are white at final screen conversion. Blitter masking LUT at `0x8048` preserves destination only for source state3. Source state3 is transparent for sprite composition, not a third gray.

SHAPES2D calls `CHANGECO` at `0xa450` only when sprite color flag is zero (engine color1). It uses `sub_814a`, whose byte conversion table is at `0x8170`. Exhaustive inspection of its256 entries proves independent per-pixel mapping `0->0, 1->1, 2->1, 3->3`. Thus engine color0 uses state1 black, states0/2 white; engine color1 uses states1/2 black, state0 white. Both retain state3 transparency. No badges, tinting, or guessed inversion are required.

## Exact anchors and selectors

All arrays below were decoded as big-endian initialized model data. Rows in 64-element arrays follow display rank/file order. Shape LUT rows are orientation0..7, columns display type0..7.

### Perspective shape LUT at `0xff314`

```text
99, 99, 21, 29, 33, 41, 49, 99
99, 17, 22, 99, 34, 42, 49, 99
99, 99, 23, 30, 35, 43, 50, 99
99, 18, 24, 99, 36, 44, 54, 99
99, 99, 25, 31, 37, 45, 51, 99
99, 19, 26, 99, 38, 46, 51, 99
99, 99, 27, 32, 39, 47, 52, 99
99, 20, 28, 99, 40, 48, 53, 99
```

### Flat shape LUT at `0xff354`

```text
99, 99, 18, 19, 20, 21, 22, 99
99, 17, 18, 99, 20, 21, 22, 99
99, 99, 18, 19, 20, 21, 22, 99
99, 17, 18, 99, 20, 21, 22, 99
99, 99, 18, 19, 20, 21, 22, 99
99, 17, 18, 99, 20, 21, 22, 99
99, 99, 18, 19, 20, 21, 22, 99
99, 17, 18, 99, 20, 21, 22, 99
```

### Perspective x anchors at `0xff4fc`

```text
93, 138, 186, 231, 277, 323, 368, 416
88, 135, 182, 230, 279, 325, 373, 420
83, 131, 180, 230, 280, 329, 376, 427
77, 127, 178, 230, 282, 331, 383, 433
69, 123, 175, 230, 283, 334, 387, 440
63, 118, 173, 228, 284, 337, 393, 448
56, 113, 170, 228, 285, 341, 399, 456
48, 107, 166, 226, 287, 345, 406, 464
```

### Perspective y anchors at `0xff57c`

```text
75, 100, 125, 155, 184, 216, 251, 290
```

### Flat x anchors at `0xff58c`

```text
102, 147, 192, 237, 280, 325, 367, 412
102, 147, 192, 236, 280, 325, 367, 412
102, 147, 192, 236, 280, 325, 367, 412
102, 147, 192, 236, 280, 325, 367, 412
102, 147, 192, 236, 280, 325, 367, 412
102, 147, 192, 236, 280, 325, 367, 412
102, 147, 192, 236, 280, 325, 367, 412
102, 147, 192, 236, 280, 325, 367, 412
```

### Flat y anchors at `0xff60c`

```text
52, 87, 122, 157, 192, 227, 262, 297
```

### Perspective y boundaries at `0xff394`

```text
75, 97, 122, 149, 178, 210, 243, 281, 322
```

### Perspective x boundaries at `0xff3a6`

```text
74, 119, 164, 209, 256, 300, 345, 390, 437
68, 115, 161, 208, 256, 302, 348, 394, 442
62, 110, 158, 205, 256, 302, 351, 398, 448
55, 105, 154, 204, 256, 305, 354, 403, 455
47, 99, 151, 202, 256, 306, 358, 409, 462
39, 94, 147, 200, 256, 309, 362, 416, 470
31, 87, 143, 197, 256, 311, 367, 421, 479
21, 81, 137, 195, 256, 313, 370, 429, 488
10, 72, 132, 194, 256, 317, 375, 438, 500
```

### Flat y boundaries at `0xff448`

```text
32, 67, 102, 137, 172, 207, 242, 277, 312
```

### Flat x boundaries at `0xff45a`

```text
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
80, 125, 170, 214, 258, 303, 345, 390, 435
```

## Hit testing and selection outlines

`HANDLESQ` at `0x33ea` counts y boundaries less than or equal to mouseY. Counts outside1..8 mean outside; otherwise rank=count-1. It then counts x boundaries less than or equal to mouseX using the nine boundaries for that rank; counts outside1..8 mean outside; file=count-1. This is a stepped hit map, not a point-in-trapezoid algorithm. Left/top boundaries are included; right/bottom boundaries excluded. Result displaySquare=rank*8+file; engine mapping is above.

`DRAWSQUA` at `0xb62e` draws the selection onto a temporary copy of the background and then calls SHAPES2D, so pieces cover the outline. For rank r,file f, vertices are `(x[r,f]-1,y[r])`, `(x[r,f+1],y[r])`, `(x[r+1,f+1],y[r+1]+1)`, `(x[r+1,f]-1,y[r+1]+1)`. Exact outer path plus inner/connecting path are in recovered C lines6942..6960. `DRAW` at `0xbf0e` uses integer Bresenham with error>=0 tie handling. `SETAPEN` at `0xbec4` repeats the low nibble; pens0x0c and0x1c both write packed0xcc. `DRAWBUFD` at `0xbe32` replaces the addressed two-bit pixel, so both states3/0 in this pattern convert to white in final monochrome output; do not treat the outline as a transparent sprite. DRAWSQUA also repairs shared neighboring edges when pen<0x1c and a source square exists. Port the function to reproduce those edge details, rather than drawing a modern stroked polygon.

## Animation: recovered facts and remaining boundary

The original chain is `DOWALK(0xd3bc)` -> `STARTANI(0x133c4)`/`WAITANIM(0x131f2)` -> `ACTIVATE(0x134cc)` -> `HANDLEAL(0x14048)` -> the specific handlers. These are script nodes, not simply catalog sequence indices. Node records at `0xff636` have stride8: type+0,status+1,successor+2,parallel link+3,source square+4,target/argument+5,extra argument+6. Active records point to sprite at+10, store type at+14, source node index+15, active next pointer+16.

Although HANDLEAL failed C decompilation, disassembly at0x14048 proves the timebase: TickCount is copied to0xff62c, subtract previous0xff630, return if difference<6; otherwise previous=current (no catchup loop). CHECKTIM at0x15956 operates on active-record delay byte+4 and stream pointer+6. Nonzero delay decrements and blocks that pass. At zero delay, stream bytes0x80..0xfe dispatch sound (index low nibble, next byte minus0x40), then advance two bytes. Byte0xff means no new delay; another byte is consumed into delay. The handler may then advance its shape. Six Macintosh ticks is the scheduler quantum; uniform catalog preview speed is not the original frame timing.

For an already-selected ordinary walking node, ACTIVATE selects group displayType-1 and local sequence orientation, except display types1,3,6 use orientation>>1. It selects a timing stream pointer from `0xfc97c + (displayType-1)*0x60 + orientation*4`. HANDLEWA at0x14244 counts initial static entry plus delta entries up to0xffff; first display uses initial shape at source anchor, subsequent displays apply cumulative MAKESHAP XOR and LINECCFW interpolation. LINECCFW at0x130ce uses signed quotient/remainder and half-denominator rounding separately on each coordinate: for delta>=0, start+(delta/n)*k+((n/2+(delta%n)*k)/n); for negative delta, start+(delta/n)*k+(((delta%n)*k-n/2)/n), all divisions truncate toward zero. k starts1; n is the sequence entry count. Completion updates target coordinates and the following stand node restores the standing shape.

This does NOT establish the entire walking flow from only source/destination: DOWALK also queues orientation changes, per-square travel, obstacle reactions, knight/rook-specific behavior and special moves. Exact direction encoding in DOWALK is N0,NE1,E2,SE3,S4,SW5,W6,NW7 in display coordinates; pawn engine type6 remaps horizontal2->1 and6->7. Combat adds paired active scripts, memory loaders and sound events. Full faithful movement/combat requires porting that dispatch and its timing streams, not guessing one sequence or linearly moving every piece. No claim of working full choreography is made here.

## Menus and startup scope

Original MENU resources were investigated separately by the parent task; labels and item order should be taken directly from those resources. This investigation did not validate a replacement startup/new-game event loop, so it supplies no invented menu behavior or AI settings. `LOADBOAR` only loads graphics and does not itself establish the original new-game control flow. Static original board/pieces, exact hit maps, and legal human moves must be reported separately from complete original menu, computer-opponent and animation behavior.

## Subsequent animation recovery

The separate animation investigation now translates the dispatch and graph described above. See [ANIMATION_CALLS.md](ANIMATION_CALLS.md), [ANIMATION_RUNTIME.md](ANIMATION_RUNTIME.md), and [ANIMATION_COMBAT.md](ANIMATION_COMBAT.md). The earlier static-presentation scope does not describe the current animation implementation.

## DLOG/DITL/ALRT and About resource recovery

`tools/recompilation/original_tables.py` now emits the original DLOG/ALRT bounds, DITL records, enabled/disabled item types, picture references, and Pascal message text with original file offsets. New Game confirmation is `OK to start New Game?` at file0x3f0; Clear Board is `OK to Clear Board?` at file0x1f4. ALRT402 uses DITL29019 (OK/Cancel), ALRT406 uses DITL406 (OK), ALRT400 uses DITL400 (About), DLOG408 uses DITL409 (promotion). Missing DITL1 referenced by ALRT401 remains explicitly absent. Promotion picture items are enabled0x40; About picture is disabled0xc0.

PICT10001 is now decoded from original bytes rather than omitted: its one PackBitsRect yields the original MacPlay artwork, with bounds/source/destination and row lengths verified. Sixteen text runs retain original positioned/delta-text coordinates and clipping rectangles. `resource_dialog.cpp` renders the original bitmap directly and uses SDL debug text for the original text contents. This adds no substituted illustration. Details and decoder acceptance checks are recorded in `RESOURCE_DIALOGS.md`.

The resource geometry and bitmap are recovered; typography and control chrome remain a partial UI port. PICT10001 requests Geneva9, but SDL debug text has different glyph advances. Visual inspection of the saved software render confirms that several About credit lines are clipped inside the original rectangles. No arbitrary horizontal scale, modern font, or altered text placement is represented as original behavior. The application contains no FONT/NFNT/FOND resource supplying Geneva. Native Macintosh system-font recovery or an explicitly accepted platform typography adaptation is still needed for faithful, fully legible About text. Buttons currently use rectangular fallback borders rather than exact Dialog Manager rounded control rendering.

`resource_dialog_check` exercises original hit bounds, promotion overlaps, disabled items, original message text, About bitmap/text counts and dummy-SDL software rendering. C++17 strict compile and ASan/UBSan passed; these checks establish decoding/integration, not original-Mac pixel equivalence.


## Subsequent bitmap typography recovery

The About typography limitation above is resolved using actual System7 Geneva9 NFNT pixels. System7 Chicago12 now supplies dialog text as well. Reproducible FOND-based extraction, resource hashes, original font metrics, optional alternate inputs, and recovered `RINGBUTT` geometry are documented in [RESOURCE_DIALOGS.md](RESOURCE_DIALOGS.md#bitmap-typography-recovery-2026-09-27). Every set pixel of all sixteen About runs fits its untouched original clip rectangle. System7 pushbutton corners, alert default rings and the stop-hand icon are also recovered and checked against original screenshot pixels. Window frames and pressed/disabled control feedback remain separate boundaries; these checks do not establish complete Toolbox visual parity.

## Visible window port — 2026-10-03

Bitmap storage and RENDERSH clipping above remain unchanged. WIND400's rectangle `(20,0,340,511)` instead defines the **511×320 visible content area**, obtained by WINDOWIN through GetNewWindow at file0xffa8. The native host now generates this size from the resource and clips its unchanged 512×330 board/title images at the window edge. Its 20-pixel menu remains a native adapter. The new strict viewport test and fresh Cocoa capture match all 163,370 compared original content pixels at 2×, excluding the cursor. OS window chrome, desktop placement, menu geometry and pressed/disabled graphics remain outside this comparison; see [runtime evidence](ORIGINAL_RUNTIME_EVIDENCE.md) and [validation records](PLATFORM_VALIDATION.md).
