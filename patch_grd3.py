#!/usr/bin/env python3
"""Reproduce the tested GR DIGITAL III 2.50 Japanese-to-Chinese patch locally.

Only Python's standard library is required. No downloads or camera commands are
performed. Ricoh firmware is supplied by the person running this tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

VERSION = "0.1.0"
HEADER_SIZE = 0x200
MAIN_BASE = 0x2004B000
POINTER_OFFSET = 0x35BAC4
JAPANESE_POINTER = 0x203A68F0
CHINESE_POINTER = 0x203A6956
STOCK_SHA256 = "e8ec9488eab4fcf7664568ad046eca5abc796d965499a5e99a1f6dd5718dbfbd"
PATCHED_SHA256 = "2b71668028999022828ffe36d910df10b1cbbc36d1004feed6f837e4e8875236"
COMPANION_SHA256 = "6515c49f0b43a99af3546801d69290a6c4c947e141a209c2542c2d38481cf843"
FILE_SPECS = {
    "GLAUNCH3": (4_926_008, STOCK_SHA256),
    "GLAUNCH8": (71_814, COMPANION_SHA256),
}
EXPECTED_CHANGES = {
    0x16E: (0x55, 0x53),
    0x16F: (0x92, 0xC6),
    0x35BAC6: (0x68, 0x69),
    0x35BAC7: (0xF0, 0x56),
}


class ValidationError(ValueError):
    """Input or generated package is not the exact supported firmware."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def checksum(data: bytes | bytearray) -> int:
    require(len(data) >= HEADER_SIZE, "Firmware header is truncated.")
    phase = u32(data, 0x20)
    payload = data[HEADER_SIZE:]
    # This is equivalent to summing each byte with its six-position weight.
    return sum(((phase + k) % 6 + 2) * sum(payload[k::6])
               for k in range(6)) & 0xFFFFFFFF


def validate_header(data: bytes | bytearray) -> None:
    require(len(data) >= HEADER_SIZE, "Firmware header is truncated.")
    require(bytes(x ^ 0x80 for x in data[:16]) == b"R_MG3_REFLECTOR\0",
            "Wrong camera model. Only GR DIGITAL III is supported.")
    require(bytes(x ^ 0x80 for x in data[0x1F0:0x200]) == b"R_MG3_UPDATED!!!",
            "Invalid firmware footer marker.")
    require(data[0x10:0x14] == bytes.fromhex("02010250"),
            "Expected binary MAIN module version 2.50.")
    require(u32(data, 0x160) == MAIN_BASE, "Unexpected MAIN load address.")
    require(u32(data, 0x168) == len(data), "Firmware file size mismatch.")
    require(u32(data, 0x164) == len(data) - HEADER_SIZE,
            "Firmware payload size mismatch.")
    require(u32(data, 0x16C) == checksum(data), "Firmware checksum mismatch.")


def validate_main(data: bytes | bytearray, expected_sha256: str) -> None:
    require(len(data) == FILE_SPECS["GLAUNCH3"][0], "Unexpected GLAUNCH3 size.")
    validate_header(data)
    require(sha256(data) == expected_sha256,
            "GLAUNCH3 SHA-256 mismatch. Unknown or modified firmware is refused.")


def patch_main(stock: bytes) -> bytes:
    validate_main(stock, STOCK_SHA256)
    require(u32(stock, POINTER_OFFSET) == JAPANESE_POINTER,
            "Japanese filename pointer mismatch.")
    require(u32(stock, POINTER_OFFSET + 6 * 4) == CHINESE_POINTER,
            "Chinese filename pointer mismatch.")
    for pointer, name in ((JAPANESE_POINTER, b"com_main_jpn.res\0"),
                          (CHINESE_POINTER, b"com_main_chinsimpl.res\0")):
        offset = pointer - MAIN_BASE + HEADER_SIZE
        require(stock[offset:offset + len(name)] == name,
                "Language pointer does not reference the expected filename.")

    result = bytearray(stock)
    struct.pack_into(">I", result, POINTER_OFFSET, CHINESE_POINTER)
    struct.pack_into(">I", result, 0x16C, checksum(result))
    changes = {i: (old, new) for i, (old, new) in enumerate(zip(stock, result))
               if old != new}
    require(changes == EXPECTED_CHANGES, "Unexpected firmware byte changes.")
    validate_main(result, PATCHED_SHA256)

    restored = bytearray(result)
    struct.pack_into(">I", restored, POINTER_OFFSET, JAPANESE_POINTER)
    struct.pack_into(">I", restored, 0x16C, checksum(restored))
    require(restored == stock, "Offline byte reversal failed.")
    return bytes(result)


def read_exact_file(path: Path, size: int) -> bytes:
    require(not path.is_symlink(), f"Symlink input is refused: {path.name}")
    require(path.is_file(), f"Missing regular file: {path}")
    require(path.stat().st_size == size, f"Unexpected file size: {path.name}")
    with path.open("rb") as stream:
        data = stream.read(size + 1)
    require(len(data) == size, f"File changed while reading: {path.name}")
    return data


def load_firmware(source: Path) -> dict[str, bytes]:
    """Read the official ZIP or extracted directory, without extracting a ZIP."""
    data: dict[str, bytes] = {}
    if source.is_dir():
        matches: dict[str, Path] = {}
        for count, path in enumerate(source.rglob("*"), start=1):
            require(count <= 4096, "Too many entries; select the firmware folder.")
            name = path.name.upper()
            if name in FILE_SPECS:
                require(name not in matches, f"Duplicate firmware file: {name}")
                matches[name] = path
        require(set(matches) == set(FILE_SPECS),
                "The folder must contain both official GLAUNCH3 and GLAUNCH8.")
        data = {name: read_exact_file(matches[name], size)
                for name, (size, _) in FILE_SPECS.items()}
    else:
        require(source.is_file() and not source.is_symlink(),
                "Supply the official gr3-250.zip or its extracted folder.")
        require(source.stat().st_size <= 32 * 1024 * 1024,
                "Archive is too large to be the supported firmware package.")
        with zipfile.ZipFile(source) as archive:
            members = archive.infolist()
            require(len(members) <= 4096, "Too many ZIP entries.")
            for member in members:
                name = member.filename.replace("\\", "/").rsplit("/", 1)[-1].upper()
                if name not in FILE_SPECS:
                    continue
                require(name not in data, f"Duplicate firmware file in ZIP: {name}")
                size, _ = FILE_SPECS[name]
                require(not member.is_dir() and member.file_size == size,
                        f"Unexpected ZIP member size: {name}")
                with archive.open(member) as stream:
                    data[name] = stream.read(size + 1)
                require(len(data[name]) == size, f"Truncated ZIP member: {name}")
        require(set(data) == set(FILE_SPECS),
                "The ZIP must contain both official GLAUNCH3 and GLAUNCH8.")

    for name, (_, digest) in FILE_SPECS.items():
        require(sha256(data[name]) == digest,
                f"{name} SHA-256 mismatch. Use the unmodified official 2.50 package.")
    validate_main(data["GLAUNCH3"], STOCK_SHA256)
    return data


def manifest() -> dict:
    return {
        "tool_version": VERSION,
        "model": "Ricoh GR DIGITAL III (2009), not GR III (2019)",
        "main_version": "2.50",
        "extd_version_manually_confirmed_by_user": "1.18",
        "camera_resource_contents_verified_by_this_tool": False,
        "patch": "Japanese filename pointer redirected to built-in Simplified Chinese",
        "language_id_unchanged": True,
        "english_pointer_unchanged": True,
        "writes_to_extd": False,
        "stock_sha256": STOCK_SHA256,
        "patched_sha256": PATCHED_SHA256,
        "companion_sha256": COMPANION_SHA256,
        "changes": [{"offset": f"0x{offset:X}", "before": f"{old:02X}",
                     "after": f"{new:02X}"}
                    for offset, (old, new) in EXPECTED_CHANGES.items()],
        "hardware_evidence": "One Japanese-market camera passed basic checks on 2026-10-31.",
        "hardware_recovery_verified": False,
        "stock_package_note": "Original update files, not a verified unbrick image.",
    }


def package_files(stock: dict[str, bytes]) -> dict[str, bytes]:
    patched = patch_main(stock["GLAUNCH3"])
    require(sha256(stock["GLAUNCH8"]) == COMPANION_SHA256,
            "Companion firmware hash mismatch.")
    files = {
        "patched/GLAUNCH3": patched,
        "patched/GLAUNCH8": stock["GLAUNCH8"],
        "stock/GLAUNCH3": stock["GLAUNCH3"],
        "stock/GLAUNCH8": stock["GLAUNCH8"],
        "manifest.json": (json.dumps(manifest(), ensure_ascii=False, indent=2) + "\n").encode(),
    }
    files["SHA256SUMS.txt"] = "".join(
        f"{sha256(data)}  {name}\n" for name, data in sorted(files.items())
    ).encode()
    return files


def build(source: Path, output: Path, extd_version: str) -> None:
    require(extd_version == "1.18", "Only an EXTD 1.18 camera has been tested.")
    require(not output.exists() and not output.is_symlink(),
            "Output path already exists; select a new directory. Nothing overwritten.")
    files = package_files(load_firmware(source))
    # Validate all inputs and outputs before creating any output firmware files.
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in files.items():
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
        verify_package(output)
    except (OSError, ValidationError):
        print(f"Build incomplete; do not use files in {output}.", file=sys.stderr)
        raise


def verify_package(package: Path) -> None:
    expected = {
        "patched/GLAUNCH3": (4_926_008, PATCHED_SHA256),
        "patched/GLAUNCH8": FILE_SPECS["GLAUNCH8"],
        "stock/GLAUNCH3": FILE_SPECS["GLAUNCH3"],
        "stock/GLAUNCH8": FILE_SPECS["GLAUNCH8"],
    }
    allowed = set(expected) | {"manifest.json", "SHA256SUMS.txt"}
    actual = {path.relative_to(package).as_posix()
              for path in package.rglob("*") if path.is_file() or path.is_symlink()}
    require(actual == allowed, "Package has missing or unexpected files; do not mix firmware sets.")
    files: dict[str, bytes] = {}
    for name, (size, digest) in expected.items():
        data = read_exact_file(package / name, size)
        require(sha256(data) == digest, f"Package file hash mismatch: {name}")
        if name.endswith("GLAUNCH3"):
            validate_main(data, digest)
        files[name] = data
    canonical_manifest = (json.dumps(manifest(), ensure_ascii=False, indent=2) + "\n").encode()
    files["manifest.json"] = read_exact_file(package / "manifest.json", len(canonical_manifest))
    require(files["manifest.json"] == canonical_manifest, "Package manifest mismatch.")
    expected_sums = "".join(f"{sha256(data)}  {name}\n"
                            for name, data in sorted(files.items())).encode()
    require(read_exact_file(package / "SHA256SUMS.txt", len(expected_sums)) == expected_sums,
            "Package checksum list mismatch.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("build", help="Build patched and stock files on your computer")
    create.add_argument("source", type=Path, help="Official gr3-250.zip or extracted folder")
    create.add_argument("output", type=Path, help="A NEW local output directory")
    create.add_argument("--extd-version", required=True, choices=["1.18"],
                        help="EXTD version you read on the camera; not detected automatically")
    verify = commands.add_parser("verify", help="Verify a generated package against fixed hashes")
    verify.add_argument("package", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            build(args.source, args.output, args.extd_version)
            print(f"Built and verified: {args.output}")
            print("For the Chinese patch use only the two files inside patched/.")
            print("stock/ contains the original files; it is NOT a verified unbrick method.")
            print("Read README.md before flashing. No camera operation was performed.")
        else:
            verify_package(args.package)
            print("PASS: package matches the fixed, single-camera-tested firmware hashes.")
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
