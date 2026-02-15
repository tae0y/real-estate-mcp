"""Utility for extracting plain text from HWP files using olefile."""

import struct
import zlib
from pathlib import Path

import olefile

_HWPTAG_PARA_TEXT = 67


def extract_text(hwp_path: str | Path) -> str:
    """Extract plain text from an HWP file.

    Parses the BodyText/Section0 stream and returns all paragraph text
    joined by newlines, without any further post-processing.

    Args:
        hwp_path: Path to the HWP file.

    Returns:
        Raw extracted text with lines separated by newlines.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is missing the expected HWP streams.
    """
    hwp_path = Path(hwp_path)
    if not hwp_path.exists():
        raise FileNotFoundError(hwp_path)

    with olefile.OleFileIO(str(hwp_path)) as f:
        if not f.exists("BodyText/Section0"):
            raise ValueError(f"BodyText/Section0 stream not found: {hwp_path}")

        compressed = bool(f.openstream("FileHeader").read()[36] & 0x01)
        section_data = f.openstream("BodyText/Section0").read()

    if compressed:
        section_data = zlib.decompress(section_data, -15)

    return _parse_text_records(section_data)


def _parse_text_records(data: bytes) -> str:
    """Parse HWP record stream and collect text from HWPTAG_PARA_TEXT records."""
    lines: list[str] = []
    i = 0

    while i + 4 <= len(data):
        header = struct.unpack_from("<I", data, i)[0]
        tag_id = header & 0x3FF
        size = (header >> 20) & 0xFFF
        i += 4

        if size == 0xFFF:
            if i + 4 > len(data):
                break
            size = struct.unpack_from("<I", data, i)[0]
            i += 4

        if i + size > len(data):
            break

        if tag_id == _HWPTAG_PARA_TEXT:
            text = data[i : i + size].decode("utf-16-le", errors="ignore")
            lines.append(text)

        i += size

    return "\n".join(lines)
