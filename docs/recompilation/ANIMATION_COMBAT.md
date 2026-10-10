# Original combat data and loader contract

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

Evidence: `tools/3rd-party/dump.log`, original A5 initialized bytes in
`recovered/recovery_model.json`, and the two original `ALLCANM*.data` archives.
This is static reconstruction and byte-level extraction, not an original-app
runtime comparison. No replacement choreography is inferred.

Run `python3 tools/recompilation/combat_tables.py` to regenerate
`build/extra_animation/manifest.json` and raw assets. It verifies decoded shape
sizes, compressed per-shape bit lengths, metadata termination, every selected
sequence index for all 36 pairs, and reopened saved files. The output supplies
the five combat delta groups and five companion base groups missing from the
older graphics manifest. It uses the existing standard-library Huffman decoder.

## Types and dispatch

Combat role0 is the captured defender and role1 is the moving attacker.
DOWALK queues `WAITANIM(...,5,defenderSquare,0)` and
`WAITANIM(...,5,sourceSquare,1)` inside DOWALK0xd3bc. WAITANIM0x131f2 copies role0 type to0xfc3be
and role1 type to0xfc3bf. The API `combat(role0_type, role1_type)` and generated
JSON use role0/role1 throughout, preserving original numeric table order.

Display types are 1 knight, 2 king, 3 queen, 4 bishop, 5 rook, 6 pawn.
`CRUNCHAN` at `0x129a2` reads role0 defender type from `0xfc3be`, role1 attacker from
`0xfc3bf`, subtracts one to obtain `d,a` and uses:

- role0 defender selection: pointer at `0xfc73c + (6*d+a)*4`;
- role1 attacker selection: pointer at `0xfc7cc + (6*a+d)*4`;
- role0 defender timing: pointer at `0xfc85c + (6*d+a)*4`, copied to `0xfc246`;
- role1 attacker timing: pointer at `0xfc8ec + (6*a+d)*4`, copied to `0xfc24a`.

`GOOD` at `0x148fc` builds 72 selection pointers by scanning FF-terminated
lists beginning `0xfc405`, then 72 timing pointers from the heap buffer pointed to by `0xfcdd2`, then 144
walking/turning timing pointers from `0xfd372`. Initialization at `0x542a`
allocates 10,000 bytes and calls `EXPANDDA(0x5382)` on compressed source
`0xfcdd6` for 72 streams. A source byte below60 emits byte+1 zeros; FF emits
FF and ends a stream; every other byte emits byte-1 followed by the next
source byte unchanged. Therefore compressed 8F is expanded 8E (sound14),
not a missing sound15. This expansion is mandatory for correct frame timing.
**Selection lists are not timing
scripts.** Their repeated values are intentional repeated sequences.

Dense switch tables at `0x12cf8` and `0x12d54` select the argument `p` to
`SETUPSEQ` and disk selector. `SETUPSEQ` subtracts 3, then indexes offset table
`0xfd85e` at `(p-3)*8`; negative indices deliberately reach archive-1 entries.
The companion static group is the immediately following offset pair.

| Role/type | Archive | p | Delta group | Metadata / compressed |
|---|---:|---:|---|---|
| role0 defender knight | 2 | 9 | combat_00_06 | 226133 / 227848 |
| role0 defender king | 1 | -5 | combat_archive1_02 | 268475 / 270268 |
| role0 defender queen | 2 | 13 | combat_01_10 | 311519 / 312988 |
| role0 defender bishop | 2 | 15 | combat_01_12 | 394656 / 396169 |
| role0 defender rook | 1 | -1 | combat_archive1_06 | 434622 / 436329 |
| role0 defender pawn | 2 | 19 | combat_02_16 | 464545 / 466090 |
| role1 attacker knight | 1 | -7 | combat_archive1_00 | 206878 / 208326 |
| role1 attacker king | 1 | -3 | combat_archive1_04 | 377744 / 379132 |
| role1 attacker queen | 2 | 25 | combat_04_22 | 570343 / 571768 |
| role1 attacker bishop | 2 | 27 | combat_04_24 | 646975 / 648577 |
| role1 attacker rook | 1 | 1 | combat_archive1_08 | 520360 / 521807 |
| role1 attacker pawn | 2 | 31 | combat_05_28 | 707136 / 708264 |

## Runtime contract

`SETUPSEQ(0x11e9c)` selectively loads unique archive sequences, but writes their
assigned global sequence IDs back to the output list at every original list
position. Thus the output lists `0xfcbbc` and `0xfcbe4` retain order and
repetitions. A sequence is one initial base shape, followed by each delta index,
then word FFFF. A base selector with bit7 set selects standing shape
`17 + (selector & 127)`; otherwise it selects the companion combat base.
Each sequence starts afresh from its base; XOR state does not cross sequences.

`ACTIVATE(0x134cc)` selects output list/timing by combat node argument 0 or 1.
The paired activation counter `0xff75c` must reach 2 before either advances.
`HANDLECO(0x155f2)` applies `CHECKTIM` before every shape update. On each
sequence start, role0 uses the piece's current square x anchor and rank y+1;
role1 uses that square x and y without the +1. Subsequent deltas preserve the
current anchor. Sprite side/color flag is preserved. Reaching list FF sets
active delay byte to FF and increments the paired counter; both wait for
counter4 before completion. Role1 then performs combat asset cleanup and
adjusts its stored target anchor to square x+15,y-1. This pairing matters:
independent looping previews are not the original fight.

`HANDLEAL(0x14048)` only advances when TickCount minus previous >=6; it sets
previous=current and does not catch up skipped quanta. `CHECKTIM(0x15956)`:
nonzero delay decrements and returns false; zero delay consumes all successive
sound pairs, consumes one delay byte (or leaves FF in place with delay0), and
returns true for one shape update. HANDLECO performs one more successful
CHECKTIM before noticing the final sequence-list FF. Some timing streams
contain unused trailing bytes; stop with the handler, rather than draining
all events from a stream. A delay value N therefore blocks the next N
scheduler passes. FF means no further delays, not end of the sequence list.

Sound byte 80..FE selects bank `byte & 15`; following byte minus 64 is passed
to `PLAYSFX` with the sprite's side flag. CRUNCHAN scans both timing streams to
mark required sound banks at `0xfc3d0`, skipping sound parameter bytes, and
loads required banks0..4 if absent. Banks5..14 use archive1; banks0..4 use
archive2 (their duplicate archive1 data is separately byte-verified by the
existing audio extractor). `assets/audio/manifest.json` preserves decoded raw
sound headers, PCM, and neutral-pitch WAVs; neutral-pitch WAV playback alone
does not implement each event's pitch parameter.

CRUNCHAN also budgets memory: sum required missing movement groups plus pair
estimate `0xff284[(6*d+a)*4]`, evict unneeded loaded movement blocks, and if no
such block is available defer combat loading using `0xfc3f6`. The second combat
ACTIVATE releases the two movement requirements and retries. A host with all
assets resident can preserve choreography without reproducing this allocator.

## All 36 pair selections

Rows use the role-specific groups above. D/A lists are local sequence indices;
D/A source addresses identify compressed timing streams; the JSON stores both
compressed source bytes and fully expanded timing bytes, plus each stream's
heap-relative expanded offset. Actual timing pointers depend on allocation. King/king has two empty
selection lists in original data; there is no clip to invent for this illegal
chess capture.

| D,A | Role0 defender sequences | Role1 attacker sequences | D/A compressed timing source | Sound banks |
|---|---|---|---|---|
| 1,1 | 0,30,31,32,34,34,33,35,36,37,38 | 0,14,15,15,16,17,17,17,18,41 | fcdd6 / fd0ad | 3,7,11 |
| 1,2 | 0,24,44,20,21,22,23 | 0,2,3,35,4,5,6,7,8,9,10,1 | fcde2 / fd0fb | 0,3,4,14 |
| 1,3 | 39,42,31,32,33,11,12,13,14 | 0,27,28,29,26,52 | fcded / fd137 | 10,11,14 |
| 1,4 | 40,43,1,2,3,4,5,6,3,4,5,6,7,8,7,8,9,10 | 0,21,22,41,46,42,22,41,46,42,22,43,22,20,33 | fcdfd / fd1ee | 10,11,14 |
| 1,5 | 0,25,26,27,28,29 | 44,2,3,4,5,4,6,7,7,7,7,8,9,1 | fce4e / fd251 | 3,5,10,14 |
| 1,6 | 41,24,15,16,17,18,19 | 0,27,12,13,23 | fce67 / fd2da | 6,9,12 |
| 2,1 | 0,20,21,21,21,21,21,22,23,32 | 49,1,42,43,4,4,5,6,7,7,8,9,36 | fce6f / fd0b4 | 3,10,11,13,14 |
| 2,2 |  |  | fce78 / fd10f |  |
| 2,3 | 34,6,7,8,9,10,11,12,13,14,15 | 0,43,31,32,1,33,34,1,11,12,41,35,36 | fce79 / fd142 | 7,10,11,12,14 |
| 2,4 | 35,37,21,1,2,3,4,5 | 0,34,35 | fce85 / fd1f9 | 4,10 |
| 2,5 | 0,37,21,21,24,25,26,27,28,29,31,31,30,33 | 0,17,18,46,19,20,21,21,22,45,23,24,1 | fce91 / fd25a | 3,4,6,7 |
| 2,6 | 36,38,39,16,17,18,19 | 0,26,12,16,17,18,1 | fcea7 / fd2ef | 9,12 |
| 3,1 | 0,21,22,23,24,25,26,23,27,28,36 | 39,28,22,22,2,3,29,30,31,31,32,33,35,34,27,36 | fceac / fd0c6 | 5,8,10,13 |
| 3,2 | 0,29,25,30,31,32,35 | 33,31,18,19,26,27,25,1 | fcebf / fd110 | 3,6,10,14 |
| 3,3 | 0,1,2,43,4,42,2,43,8,9,10,39,10,39,11,12,44,13,15,15,14,16,17 | 37,53,2,47,4,44,2,46,9,10,25,48,53,11,12,49,50,13,14,42,16,17,15,18,19,36 | fced1 / fd15a | 0,10,13,14 |
| 3,4 | 0,45,2,43,4,2,2,43,4,5,6,7 | 36,1,2,39,4,38,2,39,4,9,10,11,12,33 | fcf06 / fd1ff | 4,10,13,14 |
| 3,5 | 0,41,23,33,34,37 | 43,2,3,4,5,4,6,7,7,7,7,41,1 | fcf1a / fd267 | 3,5,10 |
| 3,6 | 40,3,4,43,4,18,38,19,19,20 | 0,25,3,22 | fcf26 / fd307 | 9,10,12,13 |
| 4,1 | 0,19,20,21,22,23,24,25,35 | 40,1,19,20,21,42,20,21,45,23,48,23,24,36 | fcf35 / fd0da | 9,10,13 |
| 4,2 | 0,26,27,37 | 32,31,18,19,26,21,22,23,24,25,1 | fcf40 / fd116 | 3,10,13,14 |
| 4,3 | 0,1,2,3,4,39,2,3,4,40,10,42,13,11,12 | 0,45,2,3,4,45,2,3,4,53,5,8,51,6,7,36 | fcf58 / fd16d | 7,10,13,14 |
| 4,4 | 0,44,2,3,4,5,6,6,6,7,8,9 | 0,1,2,3,4,5,6,7,8,33 | fcf6c / fd20f | 1,4,10,13,14 |
| 4,5 | 0,28,29,30,31,32,33,34,36 | 42,30,31,40,32,33,34,35,36,37,38,39,1 | fcf8b / fd278 | 9,10,13,14 |
| 4,6 | 38,41,14,43,14,40,15,16,17,18 | 0,28,3,24,1 | fcfa3 / fd31b | 0,7,9,13 |
| 5,1 | 0,16,25,26,27 | 0,10,11,37,37,12,13,36 | fcfb8 / fd0ea | 6,8 |
| 5,2 | 0,21,22,23,24 | 0,11,12,13,13,14,15,16,17,1 | fcfbb / fd121 | 10,14 |
| 5,3 | 30,16,8,9,10 | 0,30,7,40 | fcfc8 / fd187 | 3,5,10 |
| 5,4 | 0,16,17,17,18,1,2,2,2,2,2,3,4,4,4,4,4,4,5,6,7 | 36,40,23,24,25,26,27,28,29,30,31,31,31,31,31,32,44,47 | fcfd3 / fd220 | 1,3,4,6,7,10,14 |
| 5,5 | 0,32,17,17,18,19,20 | 44,2,3,4,10,11,12,12,13,14,14,14,15,15,15,16,1 | fcfef / fd279 | 0,1,3,13,14 |
| 5,6 | 31,16,28,11,12,12,13,14,15 | 0,14,15,19,20,23 | fcff0 / fd32c | 2,4,7,9 |
| 6,1 | 0,30,31,31,32,33,34,35,38 | 38,10,11,46,25,1,26,27,36 | fcff8 / fd0f5 | 6,9 |
| 6,2 | 0,26,27,28,28,28,28,28,28,28,29,37 | 34,2,28,29,30,1 | fd00d / fd136 | 3,9 |
| 6,3 | 0,1,2,39,2,43,5,6,7 | 38,53,2,23,24,44,2,23,24,20,21,21,21,21,22,39 | fd01b / fd195 | 4,6,9,10,13 |
| 6,4 | 0,1,45,40,45,3,8,9,4 | 37,1,2,18,19,38,2,18,19,13,14,15,16,17,33 | fd02c / fd236 | 4,6,9,10,14 |
| 6,5 | 0,17,18,19,20,21,22,23,24,25,36 | 43,25,18,26,27,28,29,1 | fd040 / fd2d4 | 3,9,10,14 |
| 6,6 | 0,42,12,13,14,41,45,44,12,13,14,41,45,15,16,46,10,11 | 21,4,5,8,9,4,5,8,9,6,7,10,11,2,3,1 | fd093 / fd346 | 4,6,9 |
