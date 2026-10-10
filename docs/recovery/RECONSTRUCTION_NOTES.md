# Reconstruction learning notes

> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

Current inputs and legacy exports live under [source/](SOURCE_INPUTS.md). These notes concern the Macintosh executable; Apple II is a different platform port of the same game. Native C translation proceeds in `cross-port/`; see [provenance guidance](RECOVERY.md#translation-provenance).

This pass improves the reproducible static C reconstruction. It does not recover original source or a playable port. `readable_core.c` was left unchanged.

## Start with provenance, then decode structure

The original `BattleChess.bin` contains 143,488 bytes. The combined text exports contain 143,480 known bytes. `analyze_dump.read_source()` reads the exports through the unchanged `read_dump()` interface, rejects any differing or out-of-range exported byte, and then supplies the complete original memory image. The missing eight bytes were STRS omissions, not missing executable instructions. Their availability repairs the input model but cannot directly cure Macintosh trap failures.

Keep this distinction when recovering another application: missing input and wrong interpretation require different fixes. Preserve the export reader for independent provenance checks, and never silently prefer one conflicting source.

## Recognize dispatch helpers through their callers

The A5 jump table maps `A5+0x2a` to `0x1df2c` (word sparse dispatch), `A5+0x32` to `0x1df40` (long sparse dispatch), and `A5+0x3a` to `0x1df54` (dense dispatch). Their first instruction pops the return address into A0: the bytes following the call are an inline table, not ordinary instructions.

The sparse helpers read a count, then repeat a signed 16-bit relative destination and a word/long selector. DBEQ searches the entries. After the explicit selectors comes a final default destination word. Each target is relative to its own displacement word, not to the start of the table. The default has no selector in the table; treating it as a full pair would incorrectly mark the following instruction as data.

`prepare_recovery.py` recognizes only the two verified A5 displacements, bounds the count and table within its CODE resource, and requires every destination to be even and inside that resource. It records 15 candidates and excludes their table bytes from function-entry seeding. The first table, following the call at `0x280a`, has selectors 162, 161, 169 and destinations `0x281e`, `0x2836`, `0x2872`; default is `0x287c`. Its exclusive data end is `0x281e`, exactly the first branch instruction. A runnable assertion protects this boundary.

`RecoverBattleChess.java` uses Ghidra compiler-spec callfixups for sparse control flow, marks the tables as data before disassembly, and applies jump-table overrides at recognized callers. This follows the existing dense-switch mechanism. The sparse fixups describe dispatch control flow, not a verified general-purpose runtime replacement: selector values are still often printed as target-address cases, helper scratch-register effects and zero-displacement spin behavior are not an equivalence claim. Unattached candidates remain visible in the model.

## Calling conventions apply to discovered functions too

The existing script assigned `think_c_stack2` only to seeded functions. Ghidra later discovered leaf routines without LINK and left them on its default convention. At `0x1b3a2` and `0x1b3c0`, assembly loads a pointer at SP+4, a word at SP+8, and a long at SP+10. Four-byte argument alignment cannot describe that layout and produced “Cannot properly adjust input varnodes.”

Applying the existing two-byte convention to non-thunk CODE functions after analysis fixes both errors. The first now emits a byte-search loop and the second a byte-fill loop. Their semantic resemblance to memchr/memset is useful evidence, but return types and register-based helper conventions elsewhere remain inferred. This is a shared initialization fix rather than handwritten replacements for two failed bodies.

## Measured result

| Measure | Previous reconstruction | This reconstruction |
|---|---:|---:|
| Original bytes available to the model | 143,480 | 143,488 |
| Emitted C bodies | 621 | 625 |
| Bodies with bad-data stops | 140 | 143 |
| Failed bodies | 4 | 3 |
| Resolved A5 call/jump sites | 673 | 673 |
| Attached dense switches / candidates | 27 / 38 | 27 / 38 |
| Attached sparse switches / candidates | 0 / 0 | 12 / 15 |

The remaining failures are native decompiler process errors at `0x46c8`, `0x129a2`, and `0x1bdf8`. The first became a failure with the expanded sparse control flow; it is not hidden or counted as a repaired function. More paths also expose more bad-data bodies. Unsupported A-line traps still stop disassembly; converting every trap into an arbitrary no-op or ordinary C call would invent Pascal stack behavior and produce misleading apparent completeness.

## Reproduce and verify

From the BattleChess project root:

```sh
python3 tools/scripts/analyze_dump.py
python3 tools/scripts/prepare_recovery.py
python3 tools/scripts/rebuild_recovery.py
```

The final command creates a fresh temporary Ghidra project with Ghidra 12.1.3 / Java 21, rebuilds the C, and reopens the saved output. Assertions check MAIN, SEARCH, direct A5 calls, dense movement branches, sparse command branches, and both formerly failing leaf routines. Preparation checks the sparse table boundary and selectors. No original text export or existing Ghidra project is modified.

A fresh rebuild and checks of reopened generated output were performed. Neither is target-app validation: the reconstructed C has not been executed as the Macintosh game, and no equivalence to the full original engine is established. The generated pseudocode still requires platform modeling, verified prototypes, and substantial manual translation before it could become buildable source.
