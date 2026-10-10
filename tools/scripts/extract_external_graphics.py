"""Decode original disk graphics and cumulative XOR animation frames (stdlib only)."""

import base64
import hashlib
import json
import struct
from pathlib import Path
from decode_archive import Decoder
from extract_assets import png

ROOT = Path(__file__).resolve().parents[2]


def pixels(raw, width, height):
    stride = (width + 3) // 4
    assert len(raw) == stride * height
    return bytes(
        (raw[y * stride + x // 4] >> (6 - 2 * (x % 4))) & 3
        for y in range(height)
        for x in range(width)
    )


def rgba(values):
    # Original monochrome LUT at file 0x855c: only state 01 sets an ink bit.
    # Mask LUT at 0x8048 preserves destination only for state 11.
    return b"".join(
        (
            b"\0\0\0\xff"
            if value == 1
            else b"\xff\xff\xff\0" if value == 3 else b"\xff\xff\xff\xff"
        )
        for value in values
    )


def xor_frame(base, patch):
    """MAKESHAP 0x95bc: union at signed hotspots; copy old; XOR delta."""
    if not patch["width"] or not patch["height"]:
        return dict(base)
    left = min(-base["hotspot_x"], -patch["hotspot_x"])
    top = min(-base["hotspot_y"], -patch["hotspot_y"])
    right = max(base["width"] - base["hotspot_x"], patch["width"] - patch["hotspot_x"])
    bottom = max(
        base["height"] - base["hotspot_y"], patch["height"] - patch["hotspot_y"]
    )
    width, height = right - left, bottom - top
    result = bytearray([3]) * (width * height)
    for shape, xor in [(base, False), (patch, True)]:
        for y in range(shape["height"]):
            for x in range(shape["width"]):
                index = (
                    (y - shape["hotspot_y"] - top) * width
                    + x
                    - shape["hotspot_x"]
                    - left
                )
                value = shape["values"][y * shape["width"] + x]
                result[index] = result[index] ^ value if xor else value
    return dict(
        width=width,
        height=height,
        hotspot_x=-left,
        hotspot_y=-top,
        values=bytes(result),
    )


def save_animation_sequences(animation, stand, save_shape):
    """Rebuild each sequence; keep its number separate from the selected base."""
    frame_count = 0
    for deltas, info, bases in animation:
        for sequence_index, seq in enumerate(info["sequences"]):
            selector = seq["base_selector"]
            base_index = selector & 0x7F if selector & 0x80 else selector
            source_bases = stand if selector & 0x80 else bases
            assert base_index < len(source_bases)
            seq["base_source"] = (
                "standing" if selector & 0x80 else "companion combat bases"
            )
            current = source_bases[base_index]
            frames = [current]
            for delta in seq["deltas"]:
                current = xor_frame(current, deltas[delta])
                frames.append(current)
            seq["frames"] = [
                save_shape(info["name"] + f"/sequences/{sequence_index:03}/{j:03}", s)
                for j, s in enumerate(frames)
            ]
            frame_count += len(frames)
    return frame_count


def extract():
    output = ROOT / "assets/external_graphics"
    output.mkdir(parents=True, exist_ok=True)
    model = json.loads((ROOT / "recovered/recovery_model.json").read_text())
    block = next(b for b in model["blocks"] if b["name"] == "A5_globals")
    globals_data = base64.b64decode(block["data"])

    def table(address, count):
        return struct.unpack_from(
            ">" + str(count) + "I", globals_data, address - block["address"]
        )

    archives = {
        index: (ROOT / f"source/macintosh/extracted/ALLCANM{index}.data").read_bytes()
        for index in (1, 2)
    }
    manifest = dict(
        sources={
            str(index): dict(bytes=len(value), sha256=hashlib.sha256(value).hexdigest())
            for index, value in archives.items()
        },
        screens=[],
        groups=[],
        placeholders=[],
    )

    def save_raw(name, data):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        assert path.read_bytes() == data

    def save_shape(name, shape):
        info = {k: value for k, value in shape.items() if k != "values"}
        if shape["width"] and shape["height"]:
            path = output / (name + ".png")
            path.parent.mkdir(parents=True, exist_ok=True)
            png(path, shape["width"], shape["height"], rgba(shape["values"]))
            info["png"] = str(path.relative_to(output))
        return info

    def group(file, meta_offset, compressed_offset, kind, name):
        data = archives[file]
        meta = data[meta_offset:compressed_offset]
        decoder = Decoder(data, compressed_offset)
        decoded = decoder.read()
        check_decoder = Decoder(data, compressed_offset)
        save_raw(name + "/metadata.bin", meta)
        save_raw(name + "/decoded.2bpp", decoded)
        unit = 6 if kind == "delta" else 4
        position, consumed, shapes = 0, 0, []
        bit_count = 0
        while position + unit <= len(meta) and meta[position : position + 4] != bytes(
            4
        ):
            width, height, hotspot_x, hotspot_y = struct.unpack_from(
                ">BBbb", meta, position
            )
            pixel_count = ((width + 3) // 4) * height
            shape = dict(
                width=width,
                height=height,
                hotspot_x=hotspot_x,
                hotspot_y=hotspot_y,
                values=pixels(
                    decoded[consumed : consumed + pixel_count], width, height
                ),
            )
            if kind == "delta":
                # 0x12162 sums these bit lengths to seek to skipped delta frames.
                bits = struct.unpack_from(">H", meta, position + 4)[0]
                shape["compressed_bit_length"] = bits
                bit_count += bits
                check_decoder.read(pixel_count)
                assert check_decoder.bit - (compressed_offset + 8) * 8 == bit_count, (
                    name,
                    len(shapes),
                )
            shape["decoded_offset"] = consumed
            shapes.append(shape)
            consumed += pixel_count
            position += unit
        assert consumed == len(decoded), (name, consumed, len(decoded))
        sequences = []
        if kind == "delta":
            assert meta[position : position + 6] == bytes(6)
            position += 6
            count = meta[position]
            position += 1
            for _ in range(count):
                length, base = meta[position : position + 2]
                indices = list(meta[position + 2 : position + 2 + length])
                assert len(indices) == length and all(
                    index < len(shapes) for index in indices
                )
                sequences.append(dict(base_selector=base, deltas=indices))
                position += 2 + length
            assert position == len(meta)
            assert bit_count == decoder.bit - (compressed_offset + 8) * 8, name
        else:
            assert position == len(meta) or meta[position:] == bytes(4)
        info = dict(
            name=name,
            archive=file,
            metadata_offset=meta_offset,
            compressed_offset=compressed_offset,
            compressed_end=(decoder.bit + 7) // 8,
            decoded_bytes=len(decoded),
            kind=kind,
            shapes=[
                save_shape(name + f"/shapes/{index:03}", s)
                for index, s in enumerate(shapes)
            ],
            sequences=sequences,
        )
        manifest["groups"].append(info)
        return shapes, info

    screen_offsets = table(0xFD7F6, 6)
    for index, label in [(0, "perspective_board"), (1, "flat_board"), (3, "title")]:
        decoder = Decoder(archives[1], screen_offsets[index])
        data = decoder.read()
        assert len(data) == 128 * 340
        save_raw(f"screens/{label}.2bpp", data)
        shape = dict(
            width=512,
            height=340,
            hotspot_x=0,
            hotspot_y=0,
            values=pixels(data, 512, 340),
        )
        manifest["screens"].append(
            dict(
                archive=1,
                offset=screen_offsets[index],
                decoded_bytes=len(data),
                **save_shape("screens/" + label, shape),
            )
        )

    offsets = table(0xFD7A2, 6)
    stand, _ = group(1, offsets[0], offsets[1], "static", "standing")
    idle, idle_info = group(1, offsets[2], offsets[3], "delta", "idle")
    group(1, offsets[4], offsets[5], "static", "flat_pieces")
    animation = [(idle, idle_info, stand)]
    pairs = list(zip(*[iter(table(0xFD85E, 60))] * 2))
    for index, (meta, compressed) in enumerate(pairs):
        if archives[2][meta:compressed].startswith(b"this is just a space holder."):
            manifest["placeholders"].append(
                dict(group=index, metadata_offset=meta, compressed_offset=compressed)
            )
            continue
        if index < 6:
            shapes, info = group(2, meta, compressed, "delta", f"move_{index:02}")
            animation.append((shapes, info, stand))
        elif index % 2 == 0:
            shapes, info = group(
                2, meta, compressed, "delta", f"combat_{(index-6)//4:02}_{index:02}"
            )
            a, b = pairs[index + 1]
            bases, _ = group(2, a, b, "static", f"combat_bases_{index+1:02}")
            animation.append((shapes, info, bases))
    frame_count = save_animation_sequences(animation, stand, save_shape)
    manifest["counts"] = dict(
        screens=len(manifest["screens"]),
        stored_shapes=sum(len(g["shapes"]) for g in manifest["groups"]),
        sequences=sum(len(g["sequences"]) for g in manifest["groups"]),
        sequence_frames=frame_count,
    )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    assert json.loads((output / "manifest.json").read_text()) == manifest
    gallery(output, manifest)
    print(json.dumps(manifest["counts"]))


def gallery(output, manifest):
    # Embed the local manifest so the gallery works from file:// without a server.
    template = r"""<!doctype html><meta charset="utf-8"><title>Battle Chess disk graphics</title>
<style>
body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;background:#ddd;color:#111}
img{image-rendering:pixelated}select,button{font:inherit;margin:.4rem;padding:.3rem}
#stage{position:relative;margin:1rem;background:repeating-conic-gradient(#fff 0 25%,#ccc 0 50%) 0/16px 16px}
#stage img{position:absolute}#shapes{display:flex;flex-wrap:wrap;gap:1rem}figure{margin:0;max-width:520px}
#shapes figure{padding:.5rem;background:#fff}figcaption{font-size:12px}#screens{display:flex;flex-wrap:wrap;gap:1rem}
</style><h1>Battle Chess disk graphics</h1>
<p>Original decoded artwork; no synthesized frames. Clips use a fixed 100 ms preview interval.
Game timing, travel across the board, opponent colors, and fight choreography are not reproduced.</p>
<div id="screens"></div><h2>Shapes and local animation clips</h2>
<label>Asset group <select id="group"></select></label>
<label>Sequence <select id="sequence"></select></label><button id="play">Play</button>
<button id="step">Next frame</button><p id="status"></p><div id="stage"><img id="frame" alt="Selected animation frame"></div>
<details><summary>Stored shapes (delta groups show XOR patches, not standalone drawings)</summary><div id="shapes"></div></details>
<script>
const manifest=MANIFEST;
const group=document.querySelector('#group'),sequence=document.querySelector('#sequence');
const frame=document.querySelector('#frame'),stage=document.querySelector('#stage'),status=document.querySelector('#status');
let frames=[],index=0,timer=null,left=0,top=0;
function stop(){clearInterval(timer);timer=null;document.querySelector('#play').textContent='Play'}
function show(){if(!frames.length)return;const f=frames[index];frame.src=f.png;frame.style.left=(-f.hotspot_x-left)+'px';frame.style.top=(-f.hotspot_y-top)+'px';status.textContent=`Frame ${index+1}/${frames.length}; hotspot (${f.hotspot_x}, ${f.hotspot_y}); ${f.width} × ${f.height}`}
function chooseSequence(){stop();index=0;frames=manifest.groups[group.value].sequences[sequence.value]?.frames||[];frame.hidden=!frames.length;if(!frames.length){stage.style.height='0';status.textContent='Static artwork group';return}left=Math.min(...frames.map(f=>-f.hotspot_x));top=Math.min(...frames.map(f=>-f.hotspot_y));stage.style.width=(Math.max(...frames.map(f=>f.width-f.hotspot_x))-left)+'px';stage.style.height=(Math.max(...frames.map(f=>f.height-f.hotspot_y))-top)+'px';show()}
function chooseGroup(){const g=manifest.groups[group.value];sequence.replaceChildren(...g.sequences.map((s,i)=>new Option(String(i),i)));document.querySelector('#shapes').replaceChildren(...g.shapes.filter(s=>s.png).map((s,i)=>{const fig=document.createElement('figure'),img=document.createElement('img'),cap=document.createElement('figcaption');img.src=s.png;img.alt=`Stored shape ${i}`;img.loading='lazy';cap.textContent=`${i}: ${s.width} × ${s.height}, anchor ${s.hotspot_x},${s.hotspot_y}`;fig.append(img,cap);return fig}));chooseSequence()}
group.replaceChildren(...manifest.groups.map((g,i)=>new Option(g.name,i)));group.onchange=chooseGroup;sequence.onchange=chooseSequence;
document.querySelector('#play').onclick=()=>{if(timer){stop();return}if(!frames.length)return;document.querySelector('#play').textContent='Pause';timer=setInterval(()=>{index=(index+1)%frames.length;show()},100)};
document.querySelector('#step').onclick=()=>{stop();if(frames.length){index=(index+1)%frames.length;show()}};
for(const s of manifest.screens){const fig=document.createElement('figure'),img=document.createElement('img'),cap=document.createElement('figcaption');img.src=s.png;img.alt=s.png;cap.textContent=s.png;fig.append(img,cap);document.querySelector('#screens').append(fig)}
chooseGroup();
</script>"""
    (output / "index.html").write_text(
        template.replace("MANIFEST", json.dumps(manifest))
    )


def self_check():
    assert pixels(b"\x1b", 4, 1) == bytes([0, 1, 2, 3])
    base = dict(width=2, height=1, hotspot_x=0, hotspot_y=0, values=bytes([1, 3]))
    patch = dict(width=2, height=1, hotspot_x=-1, hotspot_y=0, values=bytes([2, 3]))
    frame = xor_frame(base, patch)
    assert frame["width"] == 3 and frame["values"] == bytes([1, 1, 0])
    assert xor_frame(frame, patch)["values"] == bytes([1, 3, 3])


if __name__ == "__main__":
    self_check()
    extract()
