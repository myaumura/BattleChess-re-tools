"""Recover original sound blocks and neutral-pitch PCM WAVs (standard library)."""

import base64
import hashlib
import json
import struct
import wave
from pathlib import Path
from decode_archive import Decoder, self_check

ROOT = Path(__file__).resolve().parents[2]


def extract():
    self_check()
    model = json.loads((ROOT / "recovered/recovery_model.json").read_text())
    block = next(
        block_entry
        for block_entry in model["blocks"]
        if block_entry["name"] == "A5_globals"
    )
    globals_data = base64.b64decode(block["data"])
    archives = {
        archive_name: (
            ROOT / f"source/macintosh/extracted/{archive_name}.data"
        ).read_bytes()
        for archive_name in ("ALLCANM1", "ALLCANM2")
    }
    # Pointer assignments 0x117B8 / 0x117C0; LOADSFX chooses disk by index.
    offsets1 = struct.unpack_from(">15I", globals_data, 0xFD7BA - block["address"])
    offsets2 = struct.unpack_from(">5I", globals_data, 0xFD94E - block["address"])
    folder = ROOT / "assets/audio"
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for index in range(15):
        archive = "ALLCANM2" if index <= 4 else "ALLCANM1"
        offset = (offsets2 if index <= 4 else offsets1)[index]
        decoder = Decoder(archives[archive], offset)
        decoded = decoder.read()
        encoded_size = (decoder.bit + 7) // 8 - offset
        assert encoded_size == 8 + (decoder.header_word >> 3)
        assert decoder.bit - offset * 8 == decoder.header_word + 57
        if index < 4:
            assert offset + encoded_size == offsets2[index + 1]
        elif 5 <= index < 14:
            assert offset + encoded_size == offsets1[index + 1]
        if index <= 4:
            other = Decoder(archives["ALLCANM1"], offsets1[index]).read()
            assert (
                decoded == other
            )  # Duplicate disk-copy evidence, not guessed content.
        period, length_words = struct.unpack_from(">HH", decoded)
        # MACPLAYS supplies the driver 2*length_words bytes beginning at +4.
        # The six-byte FFSynthRec header is overwritten; samples begin at +10.
        end = 4 + 2 * length_words
        assert period >= 20 and 10 <= end <= len(decoded)
        samples = decoded[10:end]
        # Inside Macintosh II-229: count samples per 44.93 microseconds.
        ideal_hz = (1_000_000 / 44.93) * 180 / period
        rate = round(ideal_hz)
        stem = f"sfx_{index:02d}"
        raw = folder / f"{stem}.decoded.bin"
        raw.write_bytes(decoded)
        assert raw.read_bytes() == decoded
        path = folder / f"{stem}.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 1, rate, len(samples), "NONE", "not compressed"))
            wav.writeframes(samples)
        with wave.open(str(path), "rb") as wav:
            assert wav.getparams()[:4] == (1, 1, rate, len(samples))
            assert wav.readframes(len(samples) + 1) == samples
        records.append(
            dict(
                index=index,
                archive=archive,
                offset=offset,
                compressed_bytes=encoded_size,
                decoded_bytes=len(decoded),
                decoded_sha256=hashlib.sha256(decoded).hexdigest(),
                period=period,
                driver_length_words=length_words,
                pcm_offset=10,
                pcm_bytes=len(samples),
                trailing_decoded_bytes=len(decoded) - end,
                pitch=0,
                sample_rate_hz=rate,
                ideal_rate_hz=ideal_hz,
                duration_seconds=len(samples) / rate,
                wav=path.name,
                raw=raw.name,
            )
        )
    manifest = dict(
        archive_sha256={
            archive_name: hashlib.sha256(d).hexdigest()
            for archive_name, d in archives.items()
        },
        rate_basis="round((1000000/44.93)*180/period), neutral pitch; ignores sub-Hz 16.16 quantization",
        source="MACPLAYS 0x115fc; LOADSFX 0x128cc; Inside Macintosh II-228/229",
        sounds=records,
    )
    target = folder / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    assert json.loads(target.read_text()) == manifest
    rows = "".join(
        f'<li><b>Effect {r["index"]:02d}</b> · {r["sample_rate_hz"]} Hz · {r["duration_seconds"]:.2f} s'
        f'<br><audio controls preload="none" src="{r["wav"]}"></audio> '
        f'<a href="{r["wav"]}">WAV</a></li>'
        for r in records
    )
    (folder / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Battle Chess sound effects</title>'
        "<style>body{max-width:850px;margin:40px auto;font:16px system-ui;padding:0 20px}"
        "li{margin:20px 0}audio{vertical-align:middle}</style><h1>15 original Battle Chess sound effects</h1>"
        "<p>Decoded from ALLCANM1/2. Unsigned 8-bit mono PCM; neutral game pitch. "
        'Numeric names preserve sound-table indices. These are effects, not an identified music soundtrack.</p><ol start="0">'
        + rows
        + '</ol><p><a href="manifest.json">Provenance and playback metadata</a></p>'
    )
    print(
        f"Recovered and reopened {len(records)} WAVs; {sum(r['pcm_bytes'] for r in records)} original PCM bytes"
    )


if __name__ == "__main__":
    extract()
