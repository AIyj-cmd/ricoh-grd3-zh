"""Synthetic unit tests plus optional integration tests using local Ricoh files."""

from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

import patch_grd3 as patch


def synthetic_main(payload: bytes = b"sample payload") -> bytearray:
    data = bytearray(512) + payload
    data[:16] = bytes(x ^ 0x80 for x in b"R_MG3_REFLECTOR\0")
    data[0x1F0:0x200] = bytes(x ^ 0x80 for x in b"R_MG3_UPDATED!!!")
    data[0x10:0x14] = bytes.fromhex("02010250")
    struct.pack_into(">I", data, 0x160, patch.MAIN_BASE)
    struct.pack_into(">I", data, 0x164, len(payload))
    struct.pack_into(">I", data, 0x168, len(data))
    struct.pack_into(">I", data, 0x16C, patch.checksum(data))
    return data


class ChecksumTests(unittest.TestCase):
    def test_matches_independent_bytewise_sum_at_all_phases(self):
        for start in (0, 1, 2, 3, 4, 5, 0x2004B000, 0xFFFFFFFF):
            for size in (0, 1, 5, 6, 7, 257, 1025):
                with self.subTest(start=start, size=size):
                    data = synthetic_main(bytes((i * 17 + 3) % 256 for i in range(size)))
                    struct.pack_into(">I", data, 0x20, start)
                    expected = sum(byte * ((start + index) % 6 + 2)
                                   for index, byte in enumerate(data[512:])) & 0xFFFFFFFF
                    self.assertEqual(patch.checksum(data), expected)

    def test_truncated_header(self):
        with self.assertRaises(patch.ValidationError):
            patch.checksum(b"too short")


class HeaderTests(unittest.TestCase):
    def test_valid_structural_header(self):
        patch.validate_header(synthetic_main())

    def test_corrupt_header_fields_or_payload(self):
        for offset in (0, 16, 18, 0x160, 0x164, 0x168, 0x16C, 0x1F0, 512):
            with self.subTest(offset=offset):
                data = synthetic_main()
                data[offset] ^= 1
                with self.assertRaises(patch.ValidationError):
                    patch.validate_header(data)

    def test_structurally_valid_file_is_not_authorized_firmware(self):
        # Header/checksum validation alone must never authorize a different image.
        data = synthetic_main(bytes(patch.FILE_SPECS["GLAUNCH3"][0] - 512))
        with self.assertRaisesRegex(patch.ValidationError, "SHA-256"):
            patch.patch_main(bytes(data))

    def test_file_too_short(self):
        with self.assertRaises(patch.ValidationError):
            patch.validate_header(bytes(511))


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_existing_output_preserved(self):
        out = self.root / "existing"
        out.mkdir()
        sentinel = out / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(patch.ValidationError):
            patch.build(self.root / "missing.zip", out, "1.18")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_unsupported_extd_does_not_create_output(self):
        out = self.root / "result"
        with self.assertRaises(patch.ValidationError):
            patch.build(self.root, out, "1.17")
        self.assertFalse(out.exists())

    def test_missing_inputs_do_not_create_output(self):
        out = self.root / "result"
        with self.assertRaises(patch.ValidationError):
            patch.build(self.root, out, "1.18")
        self.assertFalse(out.exists())

    def test_case_insensitive_duplicate_folder_files_rejected(self):
        for dirname in ("a", "b"):
            folder = self.root / dirname
            folder.mkdir()
            (folder / "glaunch3").write_bytes(b"")
        with self.assertRaisesRegex(patch.ValidationError, "Duplicate"):
            patch.load_firmware(self.root)

    def test_wrong_sized_zip_member_rejected_without_extraction(self):
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as out:
            out.writestr("../../GLAUNCH3", b"invalid")
        with self.assertRaises(patch.ValidationError):
            patch.load_firmware(archive)
        self.assertEqual(list(self.root.iterdir()), [archive])

    def test_truncated_file_read(self):
        path = self.root / "input"
        path.write_bytes(b"abc")
        with self.assertRaises(patch.ValidationError):
            patch.read_exact_file(path, 4)

    def test_cli_bad_zip_fails_without_output(self):
        source = self.root / "invalid.zip"
        source.write_bytes(b"not a zip")
        output = self.root / "output"
        with redirect_stderr(io.StringIO()) as errors:
            result = patch.main(["build", str(source), str(output), "--extd-version", "1.18"])
        self.assertEqual(result, 1)
        self.assertIn("ERROR:", errors.getvalue())
        self.assertFalse(output.exists())


@unittest.skipUnless(os.environ.get("GRD3_STOCK"), "Set GRD3_STOCK to your official ZIP/folder")
class OfficialFirmwareIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ["GRD3_STOCK"])
        cls.stock = patch.load_firmware(cls.source)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_patch_matches_hardware_tested_hash_and_exact_four_changes(self):
        before = self.stock["GLAUNCH3"]
        after = patch.patch_main(before)
        self.assertEqual(patch.sha256(after), patch.PATCHED_SHA256)
        actual = {i: (a, b) for i, (a, b) in enumerate(zip(before, after)) if a != b}
        self.assertEqual(actual, patch.EXPECTED_CHANGES)
        self.assertEqual(after[0x12:0x16], before[0x12:0x16])

    def test_build_and_verify_both_packages(self):
        out = self.root / "generated"
        patch.build(self.source, out, "1.18")
        patch.verify_package(out)
        self.assertEqual((out / "stock/GLAUNCH3").read_bytes(), self.stock["GLAUNCH3"])
        self.assertEqual((out / "patched/GLAUNCH8").read_bytes(), self.stock["GLAUNCH8"])

    def test_lowercase_extracted_input(self):
        source = self.root / "firmware"
        source.mkdir()
        for name, data in self.stock.items():
            (source / name.lower()).write_bytes(data)
        self.assertEqual(patch.load_firmware(source), self.stock)

    def test_tampered_package_rejected(self):
        out = self.root / "generated"
        patch.build(self.source, out, "1.18")
        firmware = out / "patched/GLAUNCH3"
        data = bytearray(firmware.read_bytes())
        data[1024] ^= 1
        firmware.write_bytes(data)
        with self.assertRaises(patch.ValidationError):
            patch.verify_package(out)

    def test_extra_updater_module_rejected(self):
        out = self.root / "generated"
        patch.build(self.source, out, "1.18")
        (out / "patched/GLAUNCH0").write_bytes(b"unexpected bootloader")
        with self.assertRaisesRegex(patch.ValidationError, "unexpected files"):
            patch.verify_package(out)

    def test_tampered_stock_input_refused_before_output(self):
        source = self.root / "input"
        source.mkdir()
        for name, data in self.stock.items():
            (source / name).write_bytes(data)
        path = source / "GLAUNCH3"
        data = bytearray(path.read_bytes())
        data[1024] ^= 1
        path.write_bytes(data)
        out = self.root / "output"
        with self.assertRaises(patch.ValidationError):
            patch.build(source, out, "1.18")
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
