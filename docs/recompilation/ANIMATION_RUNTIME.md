# Original animation runtime

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

Sources: recovered C file offsets 0x12f88–0x15956, checked against original disassembly in `tools/3rd-party/dump.log`. This is static recovery, not an original-game execution comparison.

## Dispatch and graph

The inline table at 0x140ba is data, despite dump.log decoding it as instructions. Its eight relative targets give:

| Node | Handler | Activation target (perspective) |
|---|---|---|
|1|HANDLEWA 0x14244|0x13858|
|2|HANDLETU 0x151bc|0x13d42|
|3|HANDLEST 0x1553c|0x13dc8|
|4|HANDLEHW 0x14576|0x139d2|
|5|HANDLECO 0x155f2|0x13932|
|6|HANDLETR 0x1508c|0x13ea2|
|7|HANDLECP 0x14e4a|0x13b78|
|8|HANDLESL 0x147a2|0x13aba|

Nodes are 32 records of eight bytes at 0xff636: type,status,next,parallel,source,destination/argument,extra,pad. Status2 means queued; activation writes1; completion writes0. Activation appends its active record then recursively activates parallel. Completion removes/frees its record and activates next. Original allocation is a four-record stack pool (0x12fc2/0x12f88), not an unbounded heap.

HANDLEAL consumes TickCount only if signed 32-bit difference from previous is at least6, then sets previous=current. It does not catch up missed passes. An empty-list pass returns1; a pass that completes the final active record still returns0. It reads current record's next field AFTER completion, freeing and successor activation (0x141cc). Reuse of the just-freed pool slot can therefore change traversal; preserving a pre-completion next pointer or processing an initial snapshot is observably different. `animation.c` retains the original pool/list ordering.

The [idle byte audit](IDLE_MODEM_EVIDENCE.md#script-and-caller-recovery--2026-10-03) follows the eight switch branches to their handler-call wrappers directly from bytes. It finds no additional idle handler. The 218 stored idle frames contain no scheduling policy; HANDLEAL's six-tick gate advances an existing graph and must not be repurposed as an idle trigger.

## Timing, coordinates and rendering

CHECKTIM 0x15956 decrements a nonzero delay and blocks the handler. On zero delay it processes any bytes0x80..0xfe as sound commands (low nibble index, following byte minus64 as signed-word parameter, sprite color flag), then consumes one delay byte. 0xff remains at the cursor and gives zero delay forever. The current frame proceeds immediately after reading its delay; that delay blocks subsequent passes. Flat mode always gives zero delay. Sound commands are not sequence terminators.

LINECCFW 0x130ce uses signed16-bit delta, signed quotient/remainder, half-denominator bias, and truncation toward zero. `bc_animation_coordinate` preserves the intermediate word cast before final division. All handlers use integer anchors, not floating-point tweens.

RENDERSH 0x9c74 writes both current (+0,+2) and persistent (+4,+6) coordinates on every render. ANIMSHAP removes and reinserts at ascending anchor y, BEFORE equal-y sprites. Runtime updates sprite order on every position/frame operation; renderer sorts equal y by decreasing order. Geometry hotspots remain per-frame metadata. Decoded cumulative frames can replace MAKESHAP's base-copy/XOR buffers because every sequence start resets to its own base and every subsequent word applies exactly one delta.

## Handler details

- WALK: movement sequence chosen by displayType-1/orientation (types1,3,6 halve orientation). Timing index is unhalved orientation. Count all base/delta entries up to0xffff. First frame appears at source anchor, k=1. Each subsequent pass applies frame k at LINECCFW(k,count) and increments k. When k>=count, write exact destination persistent coordinates and complete without rendering another shape. Flat mode uses standing type+16 and count16.
- HALF_WALK: capture persistent source coordinates; destination adds signed byte offsets from 0xff73d/0xff74d. n=floor(sequenceEntryCount/2). Base at source; deltas interpolate k=1..n. Complete after k increments to n+1; set exact destination persistent coordinates.
- SLIDE: same relative endpoints; retain existing frame. Seven renders with k=0..6 and n=6. It only decrements its local delay; it does not call CHECKTIM.
- APPROACH: destination is square anchor, or arg0 offset(-25,+13), or arg1 offset(+15,-1). Arg1 uses full entry count only for orientation4..6; otherwise n=floor(count/2). Renders base at k0, then deltas through k=n-1; then sets exact persistent destination and completes. This intentionally differs from HALF_WALK.
- TRANSFORM: sequence argument+14, one frame per scheduler pass, base at persistent coordinates and deltas at current coordinates. Completes on last frame. Activation changes display orientation: arguments0/1 map0/4; other arguments choose3/7 from current x<161.
- TURN: activation updates board orientation immediately. Determine signed step from bit2 of (target-current); types1,3,6 double step. Sequence index current+8 for positive, current+16 for negative, halved for types1,3,6. Timing index8+current*2+(step>=0). On each sequence base reset timing and call CHECKTIM immediately. After sequence end, the next timed pass advances orientation or completes if next equals target. No extra standing frame is fabricated.
- STAND: select original standing lookup with board[target]&0x3f and render at persistent coordinates. Activation transfers board/sprite mapping source->target. If combat bookkeeping recorded a displaced sprite, synchronous FADESHAP is invoked, then node completes. Fade callback must implement original scanline masks, not opacity interpolation.
- COMBAT: both active roles must exist before either progresses (combat_state1 blocks). Each role has a byte sequence list mapped to BCAnimClip records and a single timing stream spanning all its sequences. Every sequence restarts from a fresh base; role0 base y is square anchor+1, role1 anchor. Each role encountering sequence-list terminator increments combat_state and waits. Both complete only at state4. Role1 sets persistent coordinates to square anchor(+15,-1). Asset compaction/loading has no visual substitute in runtime because all decoded frames are already resident.

Flat ACTIVATE skips TURN, HALF_WALK, TRANSFORM and COMBAT (combat still marks bookkeeping). APPROACH is skipped for same-square/arg<2, otherwise converted to WALK. SLIDE remains seven-position translation. STAND hides captured sprite immediately in flat mode.

## API and verification

`lib/animation.h` exposes caller-owned BCAnimation, assets callbacks, original node bytes, sprite state, activation and TickCount step. Caller supplies exact timing buffers, all selected clips, original anchor/offset tables, and combat lists. Missing required assets set error; the runtime does not invent a speed or clip. Sound and fade callbacks integrate external presentation; silent omission of sound is permitted at the host's sound-enable boundary.

The native check is [`tests/animation_check.c`](https://github.com/myaumura/BattleChess/blob/main/tests/animation_check.c), run through the [native build and sanitizer guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md#checks-and-troubleshooting). It covers all eight handlers, flat walk, six-tick gating, signed interpolation, delay and sound parsing, both-role combat completion. Synthetic clips verify state semantics, not decoded resource identity or live visual equivalence.
