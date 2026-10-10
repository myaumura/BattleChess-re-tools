# Reading and extending the native recovery

> Text-only research record. Original files, captures and generated outputs are omitted.
> Recorded checks apply to the dated source versions below. For current use, follow
> [data preparation and launch](../PREPARE_DATA.md), the [native build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
> and the [native roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md).
> Historical filenames identify private evidence; they are not bundled downloads.

Native code belongs in [BattleChess](https://github.com/myaumura/BattleChess).
Extraction scripts and pack generators belong in this tools repository; edit their
Python sources rather than generated catalogs. Original binaries, analysis models,
media and generated packs stay in a private workbench outside both checkouts.
`cross-port/` and the Swift remake are independent projects and do not establish
original behavior. See [source and data boundaries](PUBLICATION.md).

Every function comment describes why the routine exists and identifies its evidence:

- **Original file offset:** an offset in the canonical Macintosh executable, with the original label where known. It is not a native address.
- **A5/data/resource reference:** an original global, table, or resource used by the translation. Synthetic Ghidra addresses never become native pointers.
- **Native adapter/check:** host integration or validation with no one-to-one original routine. Cite related original behavior without inventing an address.

Use descriptive domain names for boards, moves, search frames and animation state. Keep original arithmetic widths, move ordering, list holes and documented quirks even when they look unnecessary. Assembly is authoritative when decompiler types or control flow disagree. Separate observations from hypotheses in the evidence documents.

The core builds as standard C11 and the SDL host as standard C++17, with compiler extensions disabled. For readability:

- Group state that belongs to one operation; `TextDialog` owns text, selection and its resource identity. Keep dialog completion and game mutations in the host.
- Keep mouse capture lifetime explicit; `ResourceDialogButton` retains only an immutable resource pointer and item, clears them on completion/cancellation and never owns dialog data.
- Name native operation kinds with scoped enums; `ModemHost::Operation` replaces numeric job tags. Original wire bytes, resource IDs and arithmetic widths stay explicit.
- Use standard containers and the existing RAII handles for owned resources. Keep SDL on the UI thread and transfer owned results through `std::future`.
- Extract a helper when repeated domain logic obscures callers; `player_for_side` preserves the original Human/Mac/Modem control codes and load-order behavior.
- Retain purpose/provenance comments for extracted functions. A native helper cites related evidence without claiming to be an original routine.

Follow the native [code style](https://github.com/myaumura/BattleChess/blob/main/docs/CODE_STYLE.md)
and [build/check commands](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md).
Prepare data separately with the [final guide](../PREPARE_DATA.md); app builds
consume the matching external pack. Test assertions remain enabled in Release.
Native tests, saved-artifact comparison, visual inspection and original-machine
execution are separate evidence levels; describe each only within its checked scope.

The feature examples and test counts below describe the 2026-10-03 recovery.
Native source names and registered tests may differ in current source.

Keep bitmap storage and the visible window port distinct. WIND400 supplies the 511×320 content area; original board/title images remain 512×330 and clip at the port edge. The SDL host adds its existing 20-pixel menu. Do not resize the source pixels to fit. `original_frame_viewport` checks the resulting dimensions and original visible pixels; its CTest fixture automatically runs native smoke to create a fresh input capture.

The recovered computer consists of opening traversal, specialized move generation, root evaluation tables, incremental evaluation, selective search, and the asynchronous host. See `EVALUATION_EVIDENCE.md` and `SEARCH_EVIDENCE.md` before changing it. Search scratch state and RNG live across calls. SDL remains on the UI thread; the worker owns a copied position and publishes a complete result.

The original game was booted under Mini vMac's Macintosh IIx configuration with System7. Its initial 511×320 scene matches the native scene apart from the cursor; [the runtime record](ORIGINAL_RUNTIME_EVIDENCE.md) defines the input and comparison boundary, including the About failure and unfinished turn observation. Stable gameplay, broader animation/audio timing, event behavior and computer decisions remain unverified. Keep native tests, captured-scene comparisons and physical-device checks distinct.

System7 Chicago12/Geneva9 resources are packaged and reproducibly extracted; see [resource dialogs](RESOURCE_DIALOGS.md) and [font provenance](../recovery/SYSTEM_FONTS.md). The recovered CDEF0/QuickDraw button corners and default ring match 448 compared System7 confirmation pixels; StopAlert ICON0 matches all 1,024 icon pixels. These scoped comparisons do not imply complete Toolbox window, disabled-control or pressed-state parity. Normal Macintosh menus use MenuSelect/MenuKey, so adding the retained generic rolling-menu animation or its RNG draws would change the recovered path. See [menu reachability](MENU_REACHABILITY_EVIDENCE.md).

The modem codec, original session/retry behavior, POSIX device adapter and SDL integration are implemented and tested through pseudo-terminals. Preserve the documented wire quirks and explicit native input guards. Physical modem operation and original-to-native interoperability remain open; see [modem evidence](IDLE_MODEM_EVIDENCE.md).

Save bytes and transfer metadata are separate layers. `bc_save_write` writes the original 78-byte data fork and, on macOS, installs DOSAVE's `Game`/`IPBC` Finder identity before rename. [`save_interchange.py`](../../tools/recompilation/save_interchange.py) preserves those data bytes inside a MacBinary transfer container; it does not decode or reinterpret opaque fields. Its [transfer check](../../tools/recompilation_checks/save_interchange_check.py) covers malformed input, overwrite and partial-output behavior. The optional real HFS check requires installed hfsutils, writes only a new disk copy and temporarily updates/restores `~/.hcwd`; reproduction is in [save evidence](FILE_SETUP_EVIDENCE.md). Neither round trip proves a save was opened by the original application.

Follow the [remaining recovery checklist](REMAINING_RECOVERY_PLAN.md) for priorities and acceptance checks. The 29-test Linux baseline is validated; later changes still need a Linux rerun. The recorded macOS suite passed all 32 CTests with sanitizers enabled, including native smoke and strict saved initial-frame comparison; Cocoa and HFS validation belong to the preceding 31-test pass. No further original gameplay comparison was performed in that pass. Runtime comparisons, window/menu appearance, pressed/disabled graphics, application-level save exchange, idle callers and physical/original serial interoperability remain open. The [idle byte/caller audit](IDLE_MODEM_EVIDENCE.md#script-and-caller-recovery--2026-10-03) establishes twelve bishop scripts / 218 frames and a null-event clock update, but no selection/time gate. Stored sequences alone do not establish a caller; keep these evidence limits explicit.

The earlier documentation-only review on 2026-10-02 did not rebuild or rerun tests. Subsequent execution completed the Linux baseline, the host readability refactor, then the macOS viewport/dialog pass. [Platform validation](PLATFORM_VALIDATION.md) distinguishes those source versions, records hashes and logs, and tracks the pending Linux rerun. No original-emulator session was refreshed.
