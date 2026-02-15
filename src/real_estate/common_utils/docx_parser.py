"""Utilities for extracting plain text from .docx files.

.docx is a ZIP container; the main body text lives in `word/document.xml`.
This module extracts text without any styling information.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from defusedxml import ElementTree as DefusedET

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_TAG_P = f"{_W_NS}p"
_TAG_T = f"{_W_NS}t"
_TAG_TAB = f"{_W_NS}tab"
_TAG_BR = f"{_W_NS}br"
_TAG_CR = f"{_W_NS}cr"


@dataclass(frozen=True)
class DocxToTxtResult:
    """Result for a single converted file."""

    input_path: Path
    output_path: Path
    written: bool


def extract_text(docx_path: str | Path, *, keep_empty_paragraphs: bool = False) -> str:
    """Extract plain text from a .docx file.

    Args:
        docx_path: Path to the .docx file.
        keep_empty_paragraphs: If True, preserve empty paragraphs as blank lines.

    Returns:
        Extracted text with paragraphs separated by newlines.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file isn't a readable .docx container or is missing document.xml.
    """
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise FileNotFoundError(docx_path)

    try:
        with ZipFile(docx_path) as zf:
            try:
                info = zf.getinfo("word/document.xml")
            except KeyError as e:
                raise ValueError(f"word/document.xml not found: {docx_path}") from e

            # Basic guardrail; this should be plenty for typical docs.
            if info.file_size > 25 * 1024 * 1024:
                raise ValueError(f"word/document.xml too large ({info.file_size} bytes): {docx_path}")

            xml_bytes = zf.read(info)
    except BadZipFile as e:
        raise ValueError(f"Not a valid .docx (bad zip): {docx_path}") from e

    root = DefusedET.fromstring(xml_bytes)
    paras: list[str] = []
    for p in root.iter(_TAG_P):
        text = _paragraph_text(p)
        if text or keep_empty_paragraphs:
            paras.append(text)

    return "\n".join(paras)


def extract_dir_to_txt(
    input_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    pattern: str = "**/*.docx",
    encoding: str = "utf-8",
    overwrite: bool = False,
    keep_empty_paragraphs: bool = False,
) -> list[DocxToTxtResult]:
    """Convert all .docx files under input_dir into .txt files.

    If output_dir is None, each output .txt is written next to its input .docx.
    If output_dir is provided, the relative directory structure is preserved.

    Args:
        input_dir: Directory containing .docx files.
        output_dir: Optional output root directory.
        pattern: Glob pattern, relative to input_dir, to match docx files.
        encoding: Text encoding for output .txt files.
        overwrite: If False, skip writing when output already exists.
        keep_empty_paragraphs: Passed through to extract_text().

    Returns:
        A list of conversion results.
    """
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(input_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(input_dir)

    out_root = Path(output_dir) if output_dir is not None else None
    results: list[DocxToTxtResult] = []

    for docx_path in sorted(input_dir.glob(pattern)):
        if not docx_path.is_file():
            continue

        if out_root is None:
            out_path = docx_path.with_suffix(".txt")
        else:
            rel = docx_path.relative_to(input_dir)
            out_path = (out_root / rel).with_suffix(".txt")
            out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and not overwrite:
            results.append(DocxToTxtResult(docx_path, out_path, written=False))
            continue

        text = extract_text(docx_path, keep_empty_paragraphs=keep_empty_paragraphs)
        out_path.write_text(text, encoding=encoding)
        results.append(DocxToTxtResult(docx_path, out_path, written=True))

    return results


def _paragraph_text(p_elem: DefusedET.Element) -> str:
    parts: list[str] = []
    for node in p_elem.iter():
        if node.tag == _TAG_T and node.text:
            parts.append(node.text)
            continue
        if node.tag == _TAG_TAB:
            parts.append("\t")
            continue
        if node.tag in (_TAG_BR, _TAG_CR):
            parts.append("\n")
            continue

    return "".join(parts).strip()

