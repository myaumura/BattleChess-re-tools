# Remaining recovery execution log

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

Plan: [REMAINING_RECOVERY_PLAN.md](REMAINING_RECOVERY_PLAN.md). Started 2026-10-02. User authorized continuous implementation and documentation updates without approval pauses.

Ruling: this workspace has no Git repository; work in the existing isolated `recompilation/` directory and use saved fingerprints plus this log instead of Git/worktree-dependent skill scripts. No commits or protected-tree changes are authorized or required.

Original-runtime stability (step 2) is required for runtime, save and original-modem comparisons (steps 3, 5, 7). Linux validation, viewport/control recovery and static idle tracing can proceed independently. Hardware results require actual hardware; never substitute PTY tests.

- Step 1: baseline complete — clean Linux build, 29/29 CTests (15.20 seconds), X11 smoke and 113 animation cases. Saved confirmation/About output reopened. Later host/save changes need a Linux rerun.
- Step 2: pending — diagnose original failures; browser work deferred by the user's current instruction.
- Step 3: pending — original/native trace comparison after stable runtime.
- Step 4: partially complete — original visible viewport and native pushbutton release handling verified on macOS; menu/window appearance and pressed/disabled graphics remain open.
- Step 5: transfer layer complete — Finder identity and exact MacBinary/HFS byte transfer verified; exchange between original/native applications remains pending.
- Step 6: scripts/direct callers audited — twelve bishop entries / 218 frames, duplicate scripts and the null-event clock update recovered; no selection/time gate established.
- Step 7: native boundary checks extended — fourth/fifth-response behavior and 300-baud 8N1 verified; original serial access and physical hardware remain unverified.

## Host readability — completed 2026-10-02

Grouped time/dial/chat input in `TextDialog`, replacing five separate host variables. Extracted text selection/editing while retaining resource limits, completion and modem command bytes. Added `player_for_side` for the repeated controller lookup. Replaced numeric modem job tags with `Operation` and a named worker dispatch method. Related original offsets and native ownership comments remain in the source. No C-core behavior, timing or presentation change was introduced.

Formatted both changed source files with the project configuration. A fresh macOS configure/build with ASan/UBSan passed all 29 CTests (36.19 seconds), including SDL smoke and actual-host PTY checks. The newly rendered initial frame matched all 163,370 compared original pixels at 2× against the saved original capture. Fingerprints of 231 non-document source/reference files showed exactly the two intended host files changed; canonical inputs, Ghidra and `cross-port/` stayed unchanged.

The earlier interruption was caused by shell launches failing with `Too many open files` and automatic approval review failures/timeouts. Local editing and macOS validation resumed through the available runner. A Linux rerun still could not launch through the shell tool, and the local runner could not access Docker's socket. No browser or new original-executable check was performed. See [platform validation](PLATFORM_VALIDATION.md) for logs, source hashes and exact validation scope.

## macOS viewport and dialog input — completed 2026-10-03

Ruling: continue on macOS as requested, without browser checks. Shell execution resumed; no Linux rerun was attempted in this pass. Original-runtime dependencies for steps 2, 3, 5 and 7 remain open. Step 4 is partially complete rather than marked fully recovered.

The generator reads WIND400 at original file offset 131875. Its rectangle `(20,0,340,511)` supplies a 511×320 visible content area; WINDOWIN at 0xff6c obtains it through GetNewWindow at 0xffa8. The SDL host adds its existing 20-pixel menu. Original 512×330 board/title images retain their pixels and clip at the port boundary rather than being squeezed into the smaller area. The new strict viewport CTest requires the matching screenshot dimensions and regenerates its input through the native-smoke fixture.

`ResourceDialogButton` captures an enabled type4 resource pushbutton and returns its item only on release inside the same button in the same dialog. Outside/other-button release, focus loss, replacement and keyboard completion clear the capture. Text fields and promotion pictures retain their existing routing. The original SETTIME (ModalDialog at 0x3894), DIALNUMB (0x39ea) and SENDMESS (0x3cee) delegate mouse tracking to the Dialog Manager; this small class is a native adapter, not a recovered Toolbox implementation. Exact pressed/disabled raster and keyboard highlight timing remain deferred because this pass did not recover the required control code or reference states.

The initial regression failed because mouse-down committed New Game immediately (`bc-macos-ui-red-20261003.log`). The new focus-loss regression was also checked with the handler temporarily removed: it failed at the expected alert-state assertion (`bc-macos-ui-mutation-20261003.log`). The handler was restored before final validation. Queued SDL down/up events exercise the normal dispatcher, including focus cancellation and About completion; they do not prove delivery of physical macOS mouse/focus events.

Final configure/build with ASan/UBSan passed all **30 CTests in 37.35 seconds**, including actual-host PTY checks and 113 animation cases. Cocoa smoke passed and its 1022×680 initial image matched all **163,370** compared original content pixels at 2×. The saved board, Clear Board confirmation and About captures were reopened and inspected. Project formatting passed. The 231 saved source/reference fingerprints show exactly seven intended source/config/test files changed; protected source, recovery, Ghidra and independent-port fingerprints are unchanged. An independent read-only review found no important or critical defect. [Platform validation](PLATFORM_VALIDATION.md) records logs and source hashes.

## Idle scripts and direct callers — completed evidence pass 2026-10-03

Ruling: preserve the original-only scope while extending step6's byte/asset audit; do not enable automatic idle playback without a verified caller, selection rule and time gate. Cost: a hidden original idle path remains unimplemented. Unused Macintosh assets are a hypothesis, not a recovered fact.

`tools/idle_evidence.py` freshly decodes archive1's idle block, checks the saved two-bit pixels and original compressed bit lengths, maps the four standing bases through the original perspective table, and saves/reopens idle_evidence.json (private workspace: `docs/recompilation/idle_evidence.json`). The twelve scripts contain 218 frames for display type1 (bishop), orientations1/3/5/7; scripts4..7 repeat as8..11. Metadata supplies frame order but no elapsed delay or sound schedule. Calls and A5 addresses are recorded separately from archive offsets.

The audit scans nine original CODE payloads, excluding their headers and the synthetic A5 jump table. It adds local PC-relative calls missing from the model's cross-segment call list: five STARTANI and 59 WAITANIM candidates all lie in DOWALK; ACTIVATE has five direct callers and SETUPSEQ three. The original eight switch branches and their wrapper calls are checked from bytes. HANDLEEV's null-event branch at0x102ee calls0x103b2, then helper0x1d6da copies low-memory Time0x20c to0xff198; it does not start an idle graph. Direct table-word and initialized-alias results remain unchanged. No browser or original-game session was run.

The new runnable check failed before report generation was implemented, then passed against the original bytes. Disabling PC-relative detection in an in-memory mutant made the literal ACTIVATE caller assertion fail; the working source was never changed by that experiment. The check also generates/reopens JSON from an unrelated working directory and exercises backward PC/BSR transfers, CODE-header exclusion and truncated instructions. Fresh configure/build with ASan/UBSan enabled passed **32/32 CTests in 37.34 seconds**, including the 4,424-frame asset comparison, 113 native animation cases, native smoke and strict saved initial-frame comparison. Cocoa/HFS checks retain their preceding milestone results and were not rerun for this evidence-only change. Logs and final source identity are in [platform validation](PLATFORM_VALIDATION.md).

An independent read-only review found no critical or important issue and confirmed the current saved report matches fresh generation. Documentation now explicitly records relocation provenance; a separate canonical-byte comparison confirmed identical direct-call candidates and audited word hits in the executable and relocated model. Native src/lib and all protected source/recovery/Ghidra/cross-port fingerprints remain unchanged. Only CMake test registration, the two new Python files, the generated JSON and evidence/status documents changed.

Final: minor (deferred): compare the repository JSON with fresh output inside CTest; a stale/deleted saved report currently needs manual detection.

Final: minor (deferred): clarify CREL relocation in the tool's CODE docstring; current documentation and the canonical-byte check already record that provenance.

An additional pointer-cell neighborhood word scan saved/reopened `bc-idle-pointer-cells-20261003.json`. The half-word interiors between0xfc38a and0xfc3b2 produced no hits; direct C396/C392 uses remain the initializer and the two LOADBOAR branches. This still cannot exclude a computed A5 alias or an indirect caller.

Final: Ruling: the reviewer set aside live idle reachability, scheduling and original-game parity because no original runtime was exercised. Retain step6 as incomplete and automatic playback absent; cost: any hidden original idle behavior is still missing.

## Save transfer, idle audit and modem boundaries — completed native pass 2026-10-03

Ruling: the user has no original save, and browser checks remain outside the authorized workflow. Complete native/container/HFS transfer while leaving step 5's application-level acceptance open. Cost: the original application has not loaded a generated save, and no original-written save has been opened natively.

DOLOAD filters for `Game` at 0x9100, while DOSAVE creates `Game`/`IPBC` at 0x929c..0x92a8. The native writer omitted that identity. A new macOS xattr assertion failed before the fix; the writer now sets FinderInfo on its temporary file before rename. The MacBinary transfer command preserves all 78 bytes and refuses existing output paths. A real size-limited write exposed a leftover partial CLI output; the cleanup regression went red→green, and input reads are bounded. The final real hfsutils round trip preserved all bytes and Finder identity through a copied HFS disk, restored `~/.hcwd` and verified the canonical disk hash. [Save evidence](FILE_SETUP_EVIDENCE.md) includes commands and exact limits.

Ruling: direct-word and initialized-alias scans cannot prove complete idle reachability, so retain no automatic idle behavior without a caller/selection/time gate. Cost: any original idle path hidden by computed aliases remains unimplemented. The audit covers all recovered executable CODE blocks, including failed decompiler regions. C396/C392 appear only in the table initializer at0x117ac and two LOADBOAR branches, whose actual reads are indices 4 (flat) and 0 (perspective); the earlier evidence note had reversed those labels. No idle index 2 entry or initialized alias was found. [Idle evidence](IDLE_MODEM_EVIDENCE.md) records reproducible scans and archive offsets.

Ruling: preserve SENDBLOC's original shared-buffer retry and fifth-response failure rather than correcting the wire behavior. Cost: the original retry quirk remains observable on errors. Literal PTY checks now verify 300-baud 8N1, fourth-response success and fifth-response failure. An early test closed its PTY immediately after ACK; holding the peer open until response consumption fixed that test lifetime error. Temporarily accepting the fifth ACK then made the regression fail. `modem_session.c` was restored and matches its baseline hash; no production protocol change was needed. No physical modem was identified among the current callout devices, and no original serial session was run.

Final configure/build with ASan/UBSan passed **31/31 CTests in 36.17 seconds**. Cocoa smoke and the strict 163,370-pixel initial-frame comparison passed. Separate final-source HFS import/export passed; its saved JSON report was reopened. Four existing source/config/test files and two new transfer files changed; the 231 baseline fingerprints preserve protected source/recovery/Ghidra/independent-port files. An independent review found no critical or important issue. Deferred minor: injecting Finder-metadata failure to verify existing-save rollback; that branch is correct by inspection but not exercised. [Platform validation](PLATFORM_VALIDATION.md) records logs, source identity and the remaining reference-execution boundary.
