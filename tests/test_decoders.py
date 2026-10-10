"""Unit coverage for binary formats, pixels and recovered stream helpers."""

from pathlib import Path
import base64
import json
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools/scripts"), str(ROOT / "tools/recompilation")]
from fixtures import bitmap_font, macbinary, resource_file
from decode_archive import Decoder, decode
from extract_disk import split_macbinary
from extract_external_graphics import pixels, rgba, xor_frame
from extract_assets import png
from compare_original_frame import read_png
from bitmap_fonts import nfnt, span, generate as generate_fonts
from system_fonts import resources, extract as extract_fonts
from save_interchange import export_save, import_save
from idle_evidence import scan_calls, read_memory
from combat_tables import sound_events, streams
import combat_tables
import extract_external_graphics
from catalog import generate as generate_catalog


class HuffmanTests(unittest.TestCase):
    def block(self):
        # The tree has leaves A/B, followed by the independent literal ABBA bits.
        bits = "01" + "01000001" + "11" + "01000010" + "0110"
        return struct.pack(">II", 4, 0) + int(bits.ljust(24, "0"), 2).to_bytes(3, "big")

    def test_streaming_matches_complete_decode(self):
        self.assertEqual(decode(self.block()), b"ABBA")
        reader = Decoder(self.block())
        self.assertEqual(reader.read(1), b"A")
        self.assertEqual(reader.read(2), b"BB")
        self.assertEqual(reader.read(100), b"A")
        self.assertEqual(reader.read(), b"")

    def test_offset_and_negative_read(self):
        self.assertEqual(decode(b"xx" + self.block(), 2), b"ABBA")
        with self.assertRaises(ValueError):
            Decoder(self.block()).read(-1)

    def test_malformed_header_tree_and_stream_are_rejected(self):
        duplicate = "01" + "01000001" + "11" + "01000001"
        duplicate = int(duplicate.ljust(24, "0"), 2).to_bytes(3, "big")
        for blob in (
            b"",
            self.block()[:10],
            struct.pack(">II", 2**27, 0) + b"xx",
            struct.pack(">II", 4, 0) + duplicate,
            struct.pack(">II", 4, 0) + bytes(10),
        ):
            with self.subTest(blob=blob), self.assertRaises(ValueError):
                decode(blob)


class ResourceTests(unittest.TestCase):
    def test_macbinary_preserves_both_forks_and_mac_roman_name(self):
        self.assertEqual(
            split_macbinary(macbinary("Café", b"data", b"resource")),
            ("Café", b"data", b"resource"),
        )

    def test_macbinary_rejects_bad_headers_and_truncated_forks(self):
        valid = macbinary("Game", b"abc", b"def")
        for blob in (b"", bytes(128), valid[:130], valid[:-1]):
            with self.subTest(blob=blob), self.assertRaises(ValueError):
                split_macbinary(blob)

    def test_resource_map_resolves_names_signed_ids_and_payloads(self):
        blob = resource_file([(b"TEST", -1, "Café", b"abc"), (b"ICON", 0, "", b"def")])
        self.assertEqual(
            resources(blob),
            {(b"TEST", -1): ("Café", b"abc"), (b"ICON", 0): ("", b"def")},
        )

    def test_duplicate_resources_and_truncated_maps_are_rejected(self):
        blob = resource_file([(b"TEST", 1, "", b"a"), (b"TEST", 1, "", b"b")])
        for invalid in (blob, blob[:-1], b""):
            with self.subTest(blob=invalid), self.assertRaises(ValueError):
                resources(invalid)


class GraphicsTests(unittest.TestCase):
    def test_packed_pixels_handle_padding_and_transparency(self):
        self.assertEqual(pixels(b"\x1b\xe0", 3, 2), bytes([0, 1, 2, 3, 2, 0]))
        self.assertEqual(
            rgba(bytes([0, 1, 2, 3])),
            bytes.fromhex("ffffffff 000000ff ffffffff ffffff00"),
        )
        with self.assertRaises(AssertionError):
            pixels(b"", 3, 1)

    def test_xor_frame_keeps_signed_hotspots_and_reversible_delta(self):
        base = dict(width=2, height=1, hotspot_x=0, hotspot_y=0, values=bytes([1, 3]))
        delta = dict(width=2, height=1, hotspot_x=-1, hotspot_y=0, values=bytes([2, 3]))
        result = xor_frame(base, delta)
        self.assertEqual(
            result,
            dict(width=3, height=1, hotspot_x=0, hotspot_y=0, values=bytes([1, 1, 0])),
        )
        self.assertEqual(xor_frame(result, delta)["values"], bytes([1, 3, 3]))
        self.assertEqual(xor_frame(base, dict(delta, width=0)), base)

    def test_sequences_sharing_a_base_keep_distinct_saved_frame_paths(self):
        self.assertTrue(hasattr(extract_external_graphics, "save_animation_sequences"))
        base = dict(width=1, height=1, hotspot_x=0, hotspot_y=0, values=bytes([1]))
        group = dict(
            name="move_test",
            sequences=[
                dict(base_selector=128, deltas=[]),
                dict(base_selector=128, deltas=[]),
            ],
        )
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)

            def save(name, shape):
                path = output / (name + ".png")
                path.parent.mkdir(parents=True, exist_ok=True)
                png(path, shape["width"], shape["height"], rgba(shape["values"]))
                return dict(png=name + ".png")

            count = extract_external_graphics.save_animation_sequences(
                [([], group, [])], [base], save
            )
            self.assertEqual(count, 2)
            self.assertEqual(
                [seq["frames"][0]["png"] for seq in group["sequences"]],
                ["move_test/sequences/000/000.png", "move_test/sequences/001/000.png"],
            )
            self.assertEqual(len(list(output.rglob("*.png"))), 2)

    def test_saved_rgba_png_round_trips_as_rgb(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "frame.png"
            png(path, 2, 1, bytes.fromhex("102030ff aabbcc00"))
            self.assertEqual(read_png(path), [[b"\x10\x20\x30", b"\xaa\xbb\xcc"]])

    def test_all_five_png_filters_reconstruct_pixels(self):
        filters = [
            ([10, 20, 30, 40, 50, 60], [20, 30, 40, 70, 80, 90]),
            ([10, 20, 30, 30, 30, 30], [20, 30, 40, 50, 50, 50]),
            ([10, 20, 30, 40, 50, 60], [10, 10, 10, 30, 30, 30]),
            ([10, 20, 30, 35, 40, 45], [15, 20, 25, 40, 40, 40]),
            ([10, 20, 30, 30, 30, 30], [10, 10, 10, 30, 30, 30]),
        ]

        def chunk(kind, data):
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", zlib.crc32(kind + data))
            )

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "filters.png"
            for mode, (row0, row1) in enumerate(filters):
                raw = bytes([mode, *row0, mode, *row1])
                path.write_bytes(
                    b"\x89PNG\r\n\x1a\n"
                    + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(raw))
                    + chunk(b"IEND", b"")
                )
                with self.subTest(mode=mode):
                    self.assertEqual(
                        read_png(path),
                        [
                            [bytes([10, 20, 30]), bytes([40, 50, 60])],
                            [bytes([20, 30, 40]), bytes([70, 80, 90])],
                        ],
                    )

    def test_png_checksum_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.png"
            png(path, 1, 1, bytes(4))
            blob = bytearray(path.read_bytes())
            blob[29] ^= 1
            path.write_bytes(blob)
            with self.assertRaises(AssertionError):
                read_png(path)


class FontTests(unittest.TestCase):
    def test_bitmap_metrics_bearings_and_missing_glyph(self):
        glyphs = nfnt(bitmap_font())
        self.assertEqual(glyphs[65], (3, 2, 0, 1, 4, bytes([1, 0, 1, 0, 1, 0])))
        self.assertEqual(glyphs[64], (2, 2, 0, 1, 3, bytes([1, 1, 1, 0])))

    def test_font_bounds_and_corrupt_location_table_are_rejected(self):
        fixture = bitmap_font()
        for invalid in (
            fixture[:25],
            fixture[:-1],
            fixture[:30] + struct.pack(">3H", 0, 20, 5) + fixture[36:],
        ):
            with self.subTest(blob=invalid), self.assertRaises(ValueError):
                nfnt(invalid)
        for offset, size in ((-1, 1), (0, -1), (2, 2)):
            with self.subTest(offset=offset, size=size), self.assertRaises(ValueError):
                span(b"abc", offset, size)

    def test_missing_fonts_generate_unavailable_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "fonts.hpp"
            generate_fonts(output)
            text = output.read_text()
            self.assertIn("geneva_available = false", text)
            self.assertIn("chicago_available = false", text)

    def test_system_font_extraction_preserves_existing_different_resource(self):
        entries = [(b"ICON", 0, "", bytes(128))]
        for ident, name, size in ((0, "Chicago", 12), (3, "Geneva", 9)):
            fond = bytearray(54)
            fond.extend(struct.pack(">HHh", size, 0, 100 + ident))
            entries += [
                (b"FOND", ident, name, bytes(fond)),
                (b"NFNT", 100 + ident, "", bitmap_font()),
            ]
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source, output = folder / "System.bin", folder / "fonts"
            source.write_bytes(resource_file(entries))
            extract_fonts(source, output)
            self.assertEqual((output / "Chicago12.NFNT").read_bytes(), bitmap_font())
            (output / "Chicago12.NFNT").write_bytes(b"keep my font")
            with self.assertRaises(ValueError):
                extract_fonts(source, output)
            self.assertEqual((output / "Chicago12.NFNT").read_bytes(), b"keep my font")


class EvidenceAndSaveTests(unittest.TestCase):
    def test_save_round_trip_preserves_opaque_bytes_and_crc(self):
        data = bytes(range(78))
        blob = export_save(data, "Café game")
        self.assertEqual(blob[65:73], b"GameIPBC")
        self.assertEqual(import_save(blob), data)
        corrupted = bytearray(blob)
        corrupted[115] ^= 1
        with self.assertRaises(ValueError):
            import_save(corrupted)
        for name in ("", "x:y", "x\0y", "x" * 64):
            with self.subTest(name=name), self.assertRaises(ValueError):
                export_save(data, name)

    def test_sound_event_parameters_and_missing_argument(self):
        self.assertEqual(
            sound_events([0, 0x83, 63, 0, 0x87, 75, 255]),
            [
                dict(offset=1, bank=3, parameter=-1),
                dict(offset=4, bank=7, parameter=11),
            ],
        )
        with self.assertRaises(AssertionError):
            sound_events([0x83, 255])

    def test_terminated_streams_keep_original_addresses(self):
        with patch.object(
            combat_tables,
            "globals_data",
            return_value=(100, bytes([9, 1, 255, 2, 3, 255])),
        ):
            self.assertEqual(
                streams(101, 2),
                [
                    dict(address=101, bytes=[1, 255]),
                    dict(address=103, bytes=[2, 3, 255]),
                ],
            )

    def test_call_scanner_resolves_signed_transfers_and_truncation(self):
        model = dict(
            blocks=[
                dict(
                    name="CODE_probe",
                    address=0xD3AC,
                    data=base64.b64encode(
                        bytes.fromhex(
                            "4ead0022 4ead0022 4eba0006 4eb9000133c4 61fc 6100fffa 4eba"
                        )
                    ).decode(),
                )
            ],
            jump_table=[dict(a5_offset=0x22, file_offset=0xD3BC)],
        )
        calls = scan_calls(model)
        self.assertEqual(
            calls["DOWALK"],
            [
                dict(address=0xD3B0, kind="JSR A5"),
                dict(address=0xD3B4, kind="JSR PC"),
                dict(address=0xD3BE, kind="BSR"),
                dict(address=0xD3C0, kind="BSR"),
            ],
        )
        self.assertEqual(calls["STARTANI"], [dict(address=0xD3B8, kind="JSR absolute")])
        self.assertEqual(read_memory(model, 0xD3AC, 4), bytes.fromhex("4ead0022"))
        with self.assertRaises(ValueError):
            read_memory(model, 0xD3AB, 1)


class CatalogTests(unittest.TestCase):
    def test_bad_manifest_keeps_existing_header(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "frame.png").write_bytes(b"synthetic marker")
            manifest, output = folder / "manifest.json", folder / "assets.hpp"
            frame = dict(
                png="frame.png", width=10, height=12, hotspot_x=-2, hotspot_y=4
            )

            def save(value):
                manifest.write_text(
                    json.dumps(
                        dict(
                            groups=[
                                dict(name="example", sequences=[dict(frames=[value])])
                            ]
                        )
                    )
                )

            save(frame)
            generate_catalog(manifest, output)
            original = output.read_bytes()
            for change in (
                {"png": "../outside.png"},
                {"png": "/absolute.png"},
                {"png": "missing.png"},
                {"width": 0},
                {"height": True},
            ):
                save(frame | change)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    generate_catalog(manifest, output)
                self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
