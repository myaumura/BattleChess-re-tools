"""Emit native tables from original bytes; no fitted coordinates or recoloring."""

import base64
import json
from pathlib import Path
import struct
import sys


# Native generation/validation (no original entrypoint): Extract original geometry, color and
# MENU/DLOG/DITL/ALRT/PICT resource data into C++ tables.
def generate(root, output):
    model = json.loads((root / "recovered/recovery_model.json").read_text())
    block = next(b for b in model["blocks"] if b["name"] == "A5_globals")
    data = base64.b64decode(block["data"])
    binary = (root / "source/macintosh/BattleChess.bin").read_bytes()
    manifest = json.loads((root / "assets/external_graphics/manifest.json").read_text())
    inventory = json.loads((root / "dump_analysis.json").read_text())["resources"]
    lines = [
        "// Generated from original Macintosh data; do not edit.",
        "#pragma once",
        "struct OriginalShape { int width, height, hx, hy; unsigned offset; };",
        "struct OriginalItem { const char *label; int shortcut; };",
        "struct OriginalMenu { int id; const char *title; const OriginalItem *items; int count; };",
        "struct OriginalDialogItem { int top,left,bottom,right,type,resource_id; const char *text; };",
        "struct OriginalDialog { int id,alert,top,left,bottom,right,ditl,first,count,stages; const char *title; };",
    ]

    # Native generation/validation (no original entrypoint): Append one C++ array to the
    # generated header.
    def append_array(name, element_type, values):
        lines.append(
            f"inline constexpr {element_type} {name}[] = {{"
            + ",".join(map(str, values))
            + "};"
        )

    # Native generation/validation (no original entrypoint): Read a typed table from the
    # recovered A5 global block.
    def append_global_table(name, address, count, format_code="h"):
        offset = address - block["address"]
        values = struct.unpack_from(">" + str(count) + format_code, data, offset)
        append_array(name, "int", values)

    for name, address, count, format_code in [
        ("perspective_x", 0xFF4FC, 64, "h"),
        ("perspective_y", 0xFF57C, 8, "h"),
        ("flat_x", 0xFF58C, 64, "h"),
        ("flat_y", 0xFF60C, 8, "h"),
        ("perspective_shapes", 0xFF314, 64, "B"),
        ("flat_shapes", 0xFF354, 64, "B"),
        ("perspective_hit_y", 0xFF394, 9, "h"),
        ("perspective_hit_x", 0xFF3A6, 81, "h"),
        ("flat_hit_y", 0xFF448, 9, "h"),
        ("flat_hit_x", 0xFF45A, 81, "h"),
    ]:
        append_global_table(name, address, count, format_code)
    # Actual remapping table used by CHANGECO 0xa450 / helper 0x814a.
    append_array("opponent_pixel_bytes", "unsigned char", binary[0x8170:0x8270])
    for group_name, array_name in [
        ("standing", "standing_shapes"),
        ("flat_pieces", "flat_piece_shapes"),
    ]:
        group = next(g for g in manifest["groups"] if g["name"] == group_name)
        blob = (
            root / "assets/external_graphics" / group_name / "decoded.2bpp"
        ).read_bytes()
        entries = []
        for shape in group["shapes"]:
            width, height, hotspot_x, hotspot_y, offset = (
                shape[k]
                for k in ("width", "height", "hotspot_x", "hotspot_y", "decoded_offset")
            )
            if (
                width <= 0
                or height <= 0
                or offset < 0
                or offset + ((width + 3) // 4) * height > len(blob)
            ):
                raise ValueError("Invalid original shape span")
            entries.append(
                "{"
                + ",".join(map(str, (width, height, hotspot_x, hotspot_y, offset)))
                + "}"
            )
        append_array(array_name, "OriginalShape", entries)
    menus = []
    for resource in inventory:
        if resource["type"] != "MENU":
            continue
        resource_data = binary[
            resource["offset"] : resource["offset"] + resource["size"]
        ]
        ident = struct.unpack_from(">H", resource_data)[0]
        length = resource_data[14]
        title = resource_data[15 : 15 + length].decode("mac_roman")
        position = 15 + length
        items = []
        while position < len(resource_data) and resource_data[position]:
            length = resource_data[position]
            label = resource_data[position + 1 : position + 1 + length].decode(
                "mac_roman"
            )
            if position + length + 5 > len(resource_data):
                raise ValueError("Truncated MENU")
            items.append(
                "{"
                + json.dumps(label)
                + ","
                + str(resource_data[position + length + 2])
                + "}"
            )
            position += length + 5
        append_array("menu_" + str(ident), "OriginalItem", items)
        menus.append(
            "{"
            + str(ident)
            + ","
            + json.dumps(title)
            + ",menu_"
            + str(ident)
            + ","
            + str(len(items))
            + "}"
        )
    append_array("original_menus", "OriginalMenu", menus)
    # Dialog Manager DITL: count-minus-one followed by aligned handle/rect/type/data.
    item_lists = {}
    items = []

    # Native generation/validation (no original entrypoint): Validate a resource span
    # before slicing original file bytes.
    def resource_bytes(resource):
        offset, size = resource["offset"], resource["size"]
        if offset < 0 or size < 0 or offset + size > len(binary):
            raise ValueError("Invalid resource span")
        return binary[offset : offset + size]

    # Native generation/validation (no original entrypoint): Decode and validate an
    # original QuickDraw resource rectangle.
    def rect(resource_data, position):
        if position + 8 > len(resource_data):
            raise ValueError("Truncated resource rectangle")
        t, l, b, r = struct.unpack_from(">hhhh", resource_data, position)
        if b < t or r < l:
            raise ValueError("Inverted resource rectangle")
        return t, l, b, r

    # WINDOWIN 0xff6c obtains WIND400 with GetNewWindow at file0xffa8.
    # Keep the original visible port size separate from the 512x330 bitmap storage.
    window = next(r for r in inventory if r["type"] == "WIND" and r["id"] == 400)
    top, left, bottom, right = rect(resource_bytes(window), 0)
    if bottom == top or right == left:
        raise ValueError("Empty original game window")
    lines.append(f"inline constexpr int original_content_width = {right-left};")
    lines.append(f"inline constexpr int original_content_height = {bottom-top};")
    for resource in inventory:
        if resource["type"] != "DITL":
            continue
        resource_data = resource_bytes(resource)
        if len(resource_data) < 2:
            raise ValueError("Truncated DITL")
        count = struct.unpack_from(">h", resource_data)[0] + 1
        position = 2
        first = len(items)
        if count < 0:
            raise ValueError("Invalid DITL item count")
        for _ in range(count):
            if position + 14 > len(resource_data):
                raise ValueError("Truncated DITL item")
            bounds = rect(resource_data, position + 4)
            kind, length = resource_data[position + 12 : position + 14]
            position += 14
            if position + length > len(resource_data):
                raise ValueError("Truncated DITL payload")
            payload = resource_data[position : position + length]
            position += length
            position += position & 1
            rid = (
                struct.unpack(">h", payload)[0]
                if kind & 127 in (32, 64) and length == 2
                else -1
            )
            label = (
                payload.decode("mac_roman") if kind & 127 in (4, 5, 6, 8, 16) else ""
            )
            items.append(
                "{"
                + ",".join(map(str, (*bounds, kind, rid)))
                + ","
                + json.dumps(label)
                + "}"
            )
        if position != len(resource_data):
            raise ValueError("Unexpected DITL trailing bytes")
        item_lists[resource["id"]] = (first, count)
    append_array("original_dialog_items", "OriginalDialogItem", items)
    dialogs = []
    for resource in inventory:
        kind = resource["type"]
        if kind not in ("DLOG", "ALRT"):
            continue
        resource_data = resource_bytes(resource)
        bounds = rect(resource_data, 0)
        title = ""
        if len(resource_data) < (12 if kind == "ALRT" else 21):
            raise ValueError("Truncated dialog header")
        offset = 8 if kind == "ALRT" else 18
        if offset + 2 > len(resource_data):
            raise ValueError("Truncated dialog resource")
        ditl = struct.unpack_from(">h", resource_data, offset)[0]
        stages = struct.unpack_from(">H", resource_data, 10)[0] if kind == "ALRT" else 0
        if kind == "ALRT" and any(
            ((stages >> (i * 4)) & 15) != (stages & 15) for i in range(4)
        ):
            raise ValueError("Alert requires per-stage default state")
        if kind == "DLOG":
            if len(resource_data) < 21 or 21 + resource_data[20] > len(resource_data):
                raise ValueError("Truncated DLOG title")
            title = resource_data[21 : 21 + resource_data[20]].decode("mac_roman")
        # ALRT401 references unavailable DITL1; preserve that fact, not guessed controls.
        first, count = item_lists.get(ditl, (0, 0))
        dialogs.append(
            "{"
            + ",".join(
                map(
                    str,
                    (
                        resource["id"],
                        int(kind == "ALRT"),
                        *bounds,
                        ditl,
                        first,
                        count,
                        stages,
                    ),
                )
            )
            + ","
            + json.dumps(title)
            + "}"
        )
    append_array("original_dialogs", "OriginalDialog", dialogs)
    stop_icon = (root / "source/system7/fonts/Stop.ICON").read_bytes()
    if len(stop_icon) != 128:
        raise ValueError("Invalid System stop icon")
    append_array("system_stop_icon", "unsigned char", stop_icon)
    for name, raw in [
        ("new_game", "OK to start New Game?"),
        ("clear_board", "OK to Clear Board?"),
        ("game_over", "Game over!"),
        ("checkmate", "Check and mate."),
        ("stalemate", "Stalemate. How boring!"),
    ]:
        encoded = raw.encode("mac_roman")
        offset = binary.index(encoded) - 1
        length = binary[offset]
        if length not in (len(encoded), len(encoded) + 1):
            raise ValueError("Invalid original Pascal message")
        value = (
            binary[offset + 1 : offset + 1 + length].rstrip(b"\0").decode("mac_roman")
        )
        lines.append(
            f"inline constexpr const char *original_message_{name} = "
            + json.dumps(value)
            + ";"
        )
        lines.append(
            f"inline constexpr unsigned original_message_{name}_offset = {offset};"
        )
    # PICT10001 uses only these original v1 opcodes; reject any unhandled drawing.
    about = next(r for r in inventory if r["type"] == "PICT" and r["id"] == 10001)
    pict = resource_bytes(about)
    position = 10
    x = y = 0
    font = font_size = 0
    font_name = ""
    clip = rect(pict, 2)
    texts = []
    bitmap = None
    if struct.unpack_from(">H", pict)[0] != len(pict):
        raise ValueError("Invalid About PICT size")
    frame = clip
    while position < len(pict):
        op = pict[position]
        position += 1
        if op == 255:
            if position != len(pict):
                raise ValueError("Trailing About PICT bytes")
            break
        if op == 0x11:
            if pict[position] != 1:
                raise ValueError("Unsupported PICT version")
            position += 1
        elif op == 0xA0:
            position += 2
        elif op == 0xA1:
            length = struct.unpack_from(">H", pict, position + 2)[0]
            position += 4 + length
        elif op == 1:
            length = struct.unpack_from(">H", pict, position)[0]
            if length != 10:
                raise ValueError("Nonrectangular About clip")
            clip = rect(pict, position + 2)
            position += length
        elif op in (3, 0x0D):
            value = struct.unpack_from(">h", pict, position)[0]
            if op == 3:
                font = value
            else:
                font_size = value
            position += 2
        elif op in (0x2C, 0x2E):
            length = struct.unpack_from(">H", pict, position)[0]
            if position + 2 + length > len(pict):
                raise ValueError("Truncated About font state")
            if op == 0x2C:
                if length < 3 or pict[position + 4] + 3 != length:
                    raise ValueError("Invalid About font name")
                font = struct.unpack_from(">h", pict, position + 2)[0]
                font_name = pict[position + 5 : position + 2 + length].decode(
                    "mac_roman"
                )
            position += 2 + length
        elif op == 9:
            if pict[position : position + 8] != bytes(8):
                raise ValueError("Unexpected About pen pattern")
            position += 8
        elif op == 0x31:
            rect(pict, position)
            position += 8  # White PaintRect behind the bitmap.
        elif op in (0x28, 0x29, 0x2A, 0x2B):
            if op == 0x28:
                y, x = struct.unpack_from(">hh", pict, position)
                position += 4
            if op in (0x29, 0x2B):
                x += pict[position]
                position += 1
            if op in (0x2A, 0x2B):
                y += pict[position]
                position += 1
            length = pict[position]
            position += 1
            if position + length > len(pict):
                raise ValueError("Truncated About text")
            label = pict[position : position + length].decode("mac_roman").rstrip("\r")
            position += length
            if label:
                texts.append(
                    "{"
                    + ",".join(map(str, (x, y, *clip, font, font_size)))
                    + ","
                    + json.dumps(font_name)
                    + ","
                    + json.dumps(label)
                    + "}"
                )
        elif op == 0x98:
            stride = struct.unpack_from(">H", pict, position)[0]
            bounds = rect(pict, position + 2)
            src = rect(pict, position + 10)
            dst = rect(pict, position + 18)
            mode = struct.unpack_from(">H", pict, position + 26)[0]
            position += 28
            if (
                stride != 24
                or bounds != (161, 204, 261, 396)
                or src != (161, 206, 261, 394)
                or dst != (0, 26, 100, 214)
                or mode != 1
            ):
                raise ValueError("Unexpected About bitmap")
            decoded = bytearray()
            for _ in range(bounds[2] - bounds[0]):
                length = pict[position]
                position += 1
                end = position + length
                row = bytearray()
                if end > len(pict):
                    raise ValueError("Truncated About PackBits")
                while position < end:
                    control = pict[position]
                    position += 1
                    if control < 128:
                        count = control + 1
                        if position + count > end:
                            raise ValueError("Invalid About literal")
                        row.extend(pict[position : position + count])
                        position += count
                    elif control > 128:
                        if position >= end:
                            raise ValueError("Invalid About repeat")
                        row.extend([pict[position]] * (257 - control))
                        position += 1
                if len(row) != stride:
                    raise ValueError("Invalid About row size")
                decoded.extend(row)
            bitmap = decoded
        else:
            raise ValueError(f"Unhandled About PICT opcode {op:02x}")
        if position > len(pict):
            raise ValueError("Truncated About opcode")
    if bitmap is None:
        raise ValueError("Missing About bitmap")
    lines.append(
        "struct OriginalAboutText {int x,y,top,left,bottom,right,font,size;const char *font_name;const char *text;};"
    )
    append_array("original_about_text", "OriginalAboutText", texts)
    append_array("original_about_bitmap", "unsigned char", bitmap)
    append_array("original_about_frame", "int", frame)
    # Native extraction; no original entry point. FINDOPEN (0x5e46) consumes
    # this tree from the original ALLCANM1 archive at byte offset 0x24fad.
    archive = (root / "source/macintosh/extracted/ALLCANM1.data").read_bytes()
    book = archive[0x24FAD : 0x24FAD + 32000]
    if len(book) != 32000 or book[0] != 0xFF:
        raise ValueError("Invalid original opening book span")
    append_array("original_opening_book", "unsigned char", book)
    text = "\n".join(lines) + "\n"
    output.write_text(text)
    assert output.read_text() == text
    print(
        "Original placement, shape, color, MENU/DLOG/DITL/ALRT and message tables regenerated"
    )


if __name__ == "__main__":
    generate(Path(sys.argv[1]).resolve(), Path(sys.argv[2]))
