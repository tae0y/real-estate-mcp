from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

from real_estate.common_utils.docx_parser import extract_dir_to_txt, extract_text


def _write_minimal_docx(path: Path, document_xml: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document_xml.encode("utf-8"))


def test_extract_text_reads_word_document_xml(tmp_path: Path) -> None:
    docx = tmp_path / "sample.docx"
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hello</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>World</w:t></w:r></w:p>
    <w:p><w:r><w:t>Line1</w:t></w:r><w:r><w:br/></w:r><w:r><w:t>Line2</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    _write_minimal_docx(docx, xml)

    text = extract_text(docx)
    assert text == "Hello\tWorld\nLine1\nLine2"


def test_extract_text_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_text(tmp_path / "missing.docx")


def test_extract_dir_to_txt_writes_side_by_side(tmp_path: Path) -> None:
    input_dir = tmp_path / "in"
    docx1 = input_dir / "a.docx"
    docx2 = input_dir / "nested" / "b.docx"

    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>OK</w:t></w:r></w:p></w:body>
</w:document>
"""
    _write_minimal_docx(docx1, xml)
    _write_minimal_docx(docx2, xml)

    results = extract_dir_to_txt(input_dir)
    out_paths = {r.output_path for r in results}

    assert (input_dir / "a.txt") in out_paths
    assert (input_dir / "nested" / "b.txt") in out_paths
    assert (input_dir / "a.txt").read_text(encoding="utf-8") == "OK"

