# Dependencies

Install the preparation commands before following the
[preparation and launch guide](PREPARE_DATA.md). Every required executable must
be available on `PATH`. The tools use Python's standard library and do not install
packages or download original inputs.

## Data preparation

| Dependency | Requirement and source |
|---|---|
| Python | Version 3.12 or newer; [official downloads](https://www.python.org/downloads/). |
| Git | Clone the two public repositories; [official downloads](https://git-scm.com/downloads). |
| m68kdasm | The disassembler from [resource_dasm releases](https://github.com/fuzziqersoftware/resource_dasm/releases). Choose a build for your operating system and architecture, or follow the [upstream source-build instructions](https://github.com/fuzziqersoftware/resource_dasm#building). |
| hfsutils | Provides `hmount`, `hcopy` and `humount`; [upstream project](https://www.mars.org/home/rob/proj/hfs/). On macOS with Homebrew use [the hfsutils formula](https://formulae.brew.sh/formula/hfsutils). On Linux use your distribution's package or upstream build instructions. |

For hfsutils on macOS with Homebrew:

```sh
brew install hfsutils
```

For `m68kdasm`, place the executable from the matching release in a directory on
`PATH`. When building from source, upstream requires CMake, zlib and
[phosg](https://github.com/fuzziqersoftware/phosg); follow that project's current
instructions. A Macintosh emulator, Ghidra, Java and the full `resource_dasm`
resource-extraction executable are not needed by this preparation command.

## Native game

The [BattleChess build guide](https://github.com/myaumura/BattleChess/blob/main/docs/BUILD.md)
provides macOS and Linux installation commands for a C11/C++17 compiler,
CMake 3.20+ and SDL3 3.4+ development files. Those dependencies are needed to
build and launch the game, not to prepare its data.

Original game disks, System files and generated packs are supplied separately.
The [input table](PREPARE_DATA.md#3-supply-the-original-files) identifies the two
required files and their permanent locations.
