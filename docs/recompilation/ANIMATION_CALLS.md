# Original animation entry points and graph

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

Evidence: `recovered/BattleChess_recovered.c`, original instruction addresses in `tools/3rd-party/dump.log`, initialized `recovered/recovery_model.json`. This is static recovery, not an original-game execution trace. Addresses are original file offsets; globals use recovered A5=0x100000. C prototypes with split long arguments are unreliable; original stack pushes establish the move record.

## Move entry and special moves

`DOWALK 0xd3bc` receives five words: **destination engine square**, **source engine square**, special flag, `(movingEngineType<<8)|capturedEngineType`, suppress-network flag. Engine types 1 king,2 queen,3 rook,4 bishop,5 knight,6 pawn. Display types use `[0,2,5,6,1,3,4]`; inverse table at0xfed68 is `[0,4,1,5,6,2,3,0]`. Engine squares use 0x88 coordinates. Display square is `(e&7)|(((e>>1)&0x38)^0x38)`.

All five cross-segment DOWALK call instructions are 0x5a9c,0x5db6,0x5dec,0x71ee,0x7608 (A5+0x392 / export110). `animation_calls.json` preserves every disassembled DOWALK/STARTANI/WAITANIM call and its preceding stack instructions. The STARTANI/WAITANIM export calls occur only within DOWALK.

Game-level callers in recovered C:

| Caller | Condition / arguments |
|---|---|
| Menu handler case0x5a52 | After STOREMOV and WALKIFPR; move globals0xf9910/14, normal network flag. Apparent two-argument decompilation is packed longs. |
| RETURNAN0x5c38, first DOWALK branch | Computer result from0xf9918/1c; passes draw/repetition/score gates and WALKIFPR says no promotion. flag0. |
| RETURNAN0x5c38, second DOWALK branch | Other player-control configuration; same result record and promotion gate, flag0. |
| DOCHECKM0x716a | After BUILDCHE0x739e and side swap: artificial king-capture record0xfad50/54; only if moving type nonzero; flag1 suppresses network. Stalemate branch has no animation. |
| WALKIFPR0x75c4 | For special moves whose moving type is neither king nor pawn: animate copied record as pawn (special0, piece6, original capture), flag1; then FUN0x7630 performs promotion replacement. |
| DOWALK self-call0xd484 | Special pawn/en-passant: first animate source to source-rank/destination-file, capture pawn, special0; then animate that intermediate square to final destination without capture. |
| DOWALK self-call0xd4dc | Special king/castling: animate king normally first; then rook source h/a to f/d on corresponding ranks. |

`FUN0x7630` calls PAWNPROM0x15f3a then PERFORMC0x5062. PAWNPROM calls PUTPIECE0x15f9c directly, replacing the standing sprite. It does not queue an invented transformation sequence. Undo menu case0x5958 calls TAKEBACK then QUICKBAC0x15c9c; redo case0x59b4 calls MAKEMOVE then QUICKMOV0x15a3a. These directly erase/place pieces and handle rook/pawn restoration; **they do not play reversed combat or walking**.

## Exact graph format and construction

32 nodes at0xff636, stride8: `type,status,next,parallel,source,dest,arg,reserved`. 0xff means no link. `source` remains the original display square until final stand bookkeeping, even after several walking steps. The sprite's own square advances separately. Node status2=pending,1=active,0=complete. Original allocator increments0xff736 modulo32; the port starts a fresh zero-indexed graph and rejects overflow instead of overwriting nodes.

```text
start(type,source,dest,arg):
    n=allocate(); initialize(n); root=n; return n
after(parent,type,source,dest,arg):
    n=allocate(); initialize(n)
    if parent.next==255: parent.next=n
    else: append n to parallel chain beginning at parent.next
    return n
activate(n):
    n.status=1; allocate active record; initialize by n.type
    activate(n.parallel) if present
on handler complete(n):
    n.status=0; delete active record
    activate(n.next) if present
```

Thus two `after` calls using the same parent are concurrent siblings, not consecutive actions. This is essential for defender preparation and knight obstacle reactions. WAITANIM0x131f2 queues required movement resources; type5 additionally records defender/attacker display type at0xfc3be/bf. Appending type3 with unequal source/destination triggers CRUNCHAN0x129a2, loading setup, and activation of the root. STARTANI alone does not start playback.

## Dispatch verified from embedded jump-table words

Do not read the disassembler's apparent `ori` instructions as code: these are relative switch offsets. ACTIVATE perspective table0x13842 and scheduler table0x140ba give:

| Type | ACTIVATE target | Handler | Parameters |
|---|---|---|---|
|1|0x13858|HANDLEWA0x14244|source sprite to dest display square; ordinary per-square walk|
|2|0x13d42|HANDLETU0x151bc|dest=orientation0..7; updates display orientation|
|3|0x13dc8|HANDLEST0x1553c|dest=standing square; moves board/sprite index ownership if unequal|
|4|0x139d2|HANDLEHW0x14576|dest=direction; half walking sequence, direction offset tables|
|5|0x13932|HANDLECO0x155f2|dest=0 defender /1 attacker; paired combat descriptor and timing stream|
|6|0x13ea2|HANDLETR0x1508c|dest=rook transformation variant0..3; movement sequence base+14+variant|
|7|0x13b78|HANDLECP0x14e4a|dest=board square, arg0 defender combat position(-25,+13), arg1 attacker(+15,-1), arg2 exact square anchor|
|8|0x13aba|HANDLESL0x147a2|source=obstructing sprite, dest=direction; avoidance shift|

Flat ACTIVATE table0x135be: types1->0x13600 (static shape walking16steps),2->0x1378e (immediate completion),3->0x136b6 (stand),4->0x1378e (skip),5->0x13788 (capture bookkeeping then skip),6->0x1378e (skip),7->0x135d4 (skip unless source!=dest and arg>=2, then rewrite to walk),8->0x13652 (shift). Flat mode still uses graph semantics.

Active records: +0 sequence cursor32bit, +4 delay8bit, +6 timing pointer32bit, +10 sprite pointer32bit, +14 type8bit, +15 node8bit, +16 next active pointer32bit, +20 onward handler-specific state. Sprite storage0xfb550 has stride32; display-square->sprite index0xfc1d4; display state0xfcd78.

## DOWALK construction order

The line-by-line native translation is `lib/animation_plan.c`; its variable names intentionally retain recovered C correspondence. `bc_animation_split_move` implements recursive special prelude. Build the second plan only after the first executes, with the resulting display board.

1. Rook queues transformation0/1 according to travel rank and side. Knight chooses its first orthogonal square, turns, queues obstacle shift as a sibling if occupied, walks there, then turns onto the remaining diagonal path.
2. Determine direction N0,NE1,E2,SE3,S4,SW5,W6,NW7; pawn horizontal directions2/6 remap1/7.
3. Capture distance is Chebyshev distance (knight subtracts1); no-capture distance sentinel200. When distance<2, queue defender preparation branch from current attacker node. NE approach has a separate turn/half-walk choreography. Defender then positions at combat offset, turns0 for rook/knight else1, stands in place, starts combat role0.
4. Step rank and file one square toward target each iteration. Knight queues shifts for occupied next non-target and previous square using opposing directions. An occupied final destination approached in directions4..6 suppresses final ordinary walk. Otherwise queue type1. Decrement distance and queue defender branch when threshold reached.
5. Capture attacker: optional turn0 for rook/knight else1 when final walk was retained; type7 argument1 to combat position; turn4 for rook/knight else5; stand at original source; combat role1; type7 argument2 to destination anchor.
6. Restore facing: rook transforms2/3, with side-sensitive horizontal turn; bishop selects diagonal facing by direction and side; others face4 for flag0 or0 for flag0x40. Final type3 transfers source to destination and starts graph.

No generic interpolation or generic capture effect replaces these branches.

## Validation and limits

`tests/animation_plan_test.c` exercises 27,832 geometry-valid piece/source/destination/captured-type combinations and validates complete acyclic graph reachability, node bounds and terminal stand; checks castle, en-passant and promotion splitting. Compile/run with:

The historical standalone sanitizer run exercised the animation planner.
The native check is now [`tests/animation_plan_test.c`](https://github.com/myaumura/BattleChess/blob/main/tests/animation_plan_test.c);
run it through the native [build and sanitizer guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md#checks-and-troubleshooting).

This checks native graph safety/structure, not visual timing equivalence to the original executable. Original event polling/menu servicing/network side effects remain outside this pure builder. Native caller must provide a valid original move and a display board matching its pre-move position.

Idle archive presence alone does not establish an idle caller. No `idle`, absolute0xfd7aa/0xfd7ae, or A5 displacements0x2856/0x2852 references were found in recovered C or dump. The indirect static-archive pointer0xfc396 is only initialized at0x117b0 and read in LOADBOAR at0x1187a (index4, flat) and0x1190a (index0, standing); the corresponding length pointer0xfc392 has the same two uses. No index2 idle loader was found through those pointers. This absence is a search result, not proof that indirect archive accesses cannot reach it. No idle trigger has been invented.

The [idle byte/caller audit](IDLE_MODEM_EVIDENCE.md#script-and-caller-recovery--2026-10-03) adds PC-relative calls omitted from the model's cross-segment list. All five STARTANI and 59 WAITANIM direct calls remain within DOWALK; five ACTIVATE and three SETUPSEQ callers cover graph/move/combat processing. The twelve stored idle entries contain 218 frames using four bishop standing views, with four duplicated scripts. HANDLEEV's null-event branch only copies low-memory Time to0xff198. Computed/indirect callers and a live idle gate remain unresolved.

## Checkmate capture selection

`bc_animation_checkmate_move` translates BUILDCHE0x739e. Caller first establishes no legal moves and check (DOCHECKM condition). It targets the losing king at piece-list slot0; tries the last move's destination/piece first; if that piece does not attack the king, scans winning-side slots1 through last_piece in ascending original list order, using PIECEATT geometry. It returns a normal capture record with captured engine type1. This record is presentation-only and must not be applied to the legal chess position. The existing DOWALK graph provides the actual king combat.

Disassembly0x739e..0x74a8 confirms the fallback copies initialized record0xf99d8; its original bytes are `0008 0008 0000 0000` (destination8,source8,special0,piece0,capture0). DOCHECKM skips DOWALK when piece0. Native helper likewise returns0 with that sentinel; it does not invent a different attacker. A game without a last move follows that sentinel path.

`tests/animation_mate_test.c` executes Fool's Mate through legal original move generation, confirms mate, selects queen h4 capturing king e1, constructs paired attacker/defender combat nodes, and checks the alternate ascending-list path with a nonchecking last mover. ASan/UBSan passed. The helper shares the existing PIECEATT translation through `bc_game_piece_attacks`, avoiding a second attack algorithm.

Combat node role0 is the **defender** (queued on destination sprite); role1 is the **attacker** (queued on original source sprite). Names attached to archive pair members must not override these call arguments.
