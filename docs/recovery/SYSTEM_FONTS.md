# Recovered System 7 bitmap fonts and stop icon

> Text-only research record. Original files, captures and generated outputs are omitted.
> Results below describe historical runs; follow [the current workflow](../WORKFLOW.md) in a private workspace.

These original Apple bitmap resources supply the port's Chicago12 interface and Geneva9 About text. They were extracted from the System file in the System7.0 disk used by [Infinite Mac's Macintosh IIx configuration](https://infinitemac.org/1991/System%207.0?machine=Mac%20IIx&saved_hd=false). Font resource associations, rather than names inferred from glyph appearance, establish the faces and sizes.

| Input | SHA-256 |
|---|---|
| System7.0 disk image | `48b9f967e9665df4e0cf03fb9654de94931806e3b35fdc1f9fd7c7cf462ef856` |
| Exported System MacBinary | `21184e30e95a4e5b87a4cdcc44b02202c1fc4784ad04fcb4b5dc3be4156bbcb1` |
| Chicago12.NFNT | `36157cec9b4fc731994ca93a7b3749dc9a8e2c24e6460f9b296cf98b45405852` |
| Stop.ICON (System ICON0) | `207876ed7e1ca612bd8e457f3f071acc245d684cb89952f540b9c19f5e3ab4c4` |
| Geneva9.NFNT | `b2bbba4a4cd1e78320c6a4256bd5d08e01326349804905a1e5d577521f03c754` |

`FOND0` is named Chicago and associates plain12 with `NFNT5478`. Its ascent/descent/leading are12/3/1. `FOND3` is named Geneva and associates plain9 with `NFNT4372`; its metrics are10/2/0. No scalable outline or synthetic glyph is substituted.

Reproduce from a supplied System MacBinary:

```sh
python3 tools/recompilation/system_fonts.py /path/to/System.bin /tmp/recovered-system-fonts
cmp /tmp/recovered-system-fonts/Chicago12.NFNT source/system7/fonts/Chicago12.NFNT
cmp /tmp/recovered-system-fonts/Geneva9.NFNT source/system7/fonts/Geneva9.NFNT
```

The original source bytes belong to Apple; these are recovered inputs for this personal port, not a statement that the fonts have an open-source redistribution license. The System disk and full System file are not included here.

System `ICON0` supplies the32x32 StopAlert hand. All1024 pixels match the booted reference New Game confirmation at content-relative (20,10). The same extraction command also writes `Stop.ICON`. For reproducible control-code investigation, add `--control-code /tmp/CDEF0.code`: the script decodes CDEF0 using the dcmp2 dictionary from that same System file. No full System image, decompressor binary or control code is included here.
