# Research documentation

For installation, permanent input/output locations and launch commands, start
with [the preparation and launch guide](PREPARE_DATA.md).
[The reverse-engineering reference](WORKFLOW.md), [script inventory](TOOLS.md) and
[dependencies](DEPENDENCIES.md) explain the supporting tools. The documents below are text-only records adapted
from the private recovery workspace. They retain observed offsets, format
descriptions, uncertainty and historical checks; private captures and generated
files are named explicitly instead of linked as bundled evidence. Historical
Ghidra commands refer to the private recovery workspace; the public tools prepare
data directly from the Python analysis model and do not include a C exporter.

The notes below retain historical evidence; they do not describe a fresh run of
the current tools. Start with the [reverse-engineering diagram](WORKFLOW.md#reverse-engineering-process)
or the [preparation diagram](PREPARE_DATA.md#preparation-flow) for the current flow.

The playable native project is [BattleChess](https://github.com/myaumura/BattleChess);
its [build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md),
[data contract](https://github.com/myaumura/BattleChess/blob/main/docs/DATA.md) and
[roadmap](https://github.com/myaumura/BattleChess/blob/main/docs/ROADMAP.md) describe
the source project that consumes the prepared pack.

## Containers, code and media

- [Original input layers](recovery/SOURCE_INPUTS.md)
- [68k resource/A5 analysis](recovery/ANALYSIS.md)
- [Ghidra reconstruction and translated-code boundaries](recovery/RECOVERY.md)
- [Reconstruction notes](recovery/RECONSTRUCTION_NOTES.md)
- [Embedded media recovery](recovery/ASSETS.md)
- [Huffman and sound-driver format](recovery/AUDIO_FORMAT.md)
- [Two-bit graphics and XOR animation format](recovery/GRAPHICS_FORMAT.md)
- [System bitmap-font provenance](recovery/SYSTEM_FONTS.md)

## Original-behavior investigation

- [Native recovery evidence](recompilation/README.md)
- [Presentation mapping](recompilation/PRESENTATION_EVIDENCE.md)
- [Animation call sites](recompilation/ANIMATION_CALLS.md), [runtime graph](recompilation/ANIMATION_RUNTIME.md), [combat scripts](recompilation/ANIMATION_COMBAT.md)
- [Menu reachability](recompilation/MENU_REACHABILITY_EVIDENCE.md)
- [Dialogs and controls](recompilation/RESOURCE_DIALOGS.md)
- [Search](recompilation/SEARCH_EVIDENCE.md), [evaluation](recompilation/EVALUATION_EVIDENCE.md), [time controls](recompilation/TIME_CONTROL_EVIDENCE.md), [endings](recompilation/ENDINGS_EVIDENCE.md)
- [Save files and board setup](recompilation/FILE_SETUP_EVIDENCE.md)
- [Idle and modem investigation](recompilation/IDLE_MODEM_EVIDENCE.md)
- [Original-runtime observations](recompilation/ORIGINAL_RUNTIME_EVIDENCE.md)
- [Recorded platform checks](recompilation/PLATFORM_VALIDATION.md)
- [Remaining work](recompilation/REMAINING_RECOVERY_PLAN.md), [progress record](recompilation/RECOVERY_PROGRESS.md)
- [Source repositories and private data](recompilation/PUBLICATION.md)
- [Development and evidence discipline](recompilation/DEVELOPMENT.md)

Historical native-source paths describe the compatible private/native workbench.
This repository distributes recovery tools and authored documentation, not the
native game or the original executable. Successful artifact recovery and builds
remain separate from original-game behavior and platform/hardware validation.
