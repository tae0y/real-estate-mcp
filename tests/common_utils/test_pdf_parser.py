from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

with patch.dict("sys.modules", {"pdfplumber": MagicMock()}):
    from real_estate.common_utils import pdf_parser
    from real_estate.common_utils.pdf_parser import SupplyPrice, extract_supply_prices


def _pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    path.write_bytes(b"%PDF")
    return path


def _page(
    *,
    text: str | None = None,
    tables: list[list[list[str | None]]] | None = None,
) -> MagicMock:
    page = MagicMock()
    page.extract_text.return_value = text
    page.extract_tables.return_value = tables or []
    return page


def _pdf_context(pages: list[MagicMock]) -> MagicMock:
    pdf = MagicMock()
    pdf.pages = pages
    context = MagicMock()
    context.__enter__.return_value = pdf
    context.__exit__.return_value = None
    return context


def test_extract_supply_prices_from_table(tmp_path: Path) -> None:
    path = _pdf_path(tmp_path)
    tables = [
        [
            ["주택형", "전용면적", "공급금액"],
            ["84A", "84.9123", "45,000"],
            ["59B", "59.1234", "32,000"],
        ]
    ]

    context = _pdf_context([_page(tables=tables)])
    with patch.object(pdf_parser.pdfplumber, "open", return_value=context):
        prices = extract_supply_prices(path)

    assert prices == [
        SupplyPrice("84A", 84.9123, 45000, 1),
        SupplyPrice("59B", 59.1234, 32000, 1),
    ]


def test_extract_supply_prices_regex_fallback(tmp_path: Path) -> None:
    path = _pdf_path(tmp_path)
    text = (
        "분양가 안내\n84A 84.9123 45,000\n59B 59.1234 32,000\n"
        "이 문서는 테스트를 위해 충분한 길이의 본문을 포함합니다. "
        "표 추출이 실패할 때 정규식으로 공급금액을 찾습니다."
    )

    with patch.object(pdf_parser.pdfplumber, "open", return_value=_pdf_context([_page(text=text)])):
        prices = extract_supply_prices(path)

    assert prices == [
        SupplyPrice("84A", 84.9123, 45000, 1),
        SupplyPrice("59B", 59.1234, 32000, 1),
    ]


def test_unit_normalization_won_to_manwon(tmp_path: Path) -> None:
    path = _pdf_path(tmp_path)
    tables = [
        [
            ["주택형", "전용면적", "공급금액"],
            ["84A", "84.9123", "450000000"],
        ]
    ]

    context = _pdf_context([_page(tables=tables)])
    with patch.object(pdf_parser.pdfplumber, "open", return_value=context):
        prices = extract_supply_prices(path)

    assert prices == [SupplyPrice("84A", 84.9123, 45000, 1)]


def test_scanned_pdf_raises_value_error(tmp_path: Path) -> None:
    path = _pdf_path(tmp_path)

    context = _pdf_context([_page(text="짧음")])
    with patch.object(pdf_parser.pdfplumber, "open", return_value=context):
        with pytest.raises(ValueError, match="OCR may be required"):
            extract_supply_prices(path)


def test_page_limit_guard(tmp_path: Path) -> None:
    path = _pdf_path(tmp_path)
    pages = [_page() for _ in range(201)]

    with patch.object(pdf_parser.pdfplumber, "open", return_value=_pdf_context(pages)):
        with pytest.raises(ValueError):
            extract_supply_prices(path)


def test_file_size_guard(tmp_path: Path) -> None:
    path = _pdf_path(tmp_path)

    with (
        patch.object(Path, "stat", return_value=SimpleNamespace(st_size=25 * 1024 * 1024 + 1)),
        patch.object(pdf_parser.pdfplumber, "open") as pdf_open,
    ):
        with pytest.raises(ValueError):
            extract_supply_prices(path)

    pdf_open.assert_not_called()


def test_deduplication(tmp_path: Path) -> None:
    path = _pdf_path(tmp_path)
    tables = [
        [
            ["주택형", "전용면적", "공급금액"],
            ["84A", "84.9123", "45,000"],
            ["84A", "84.9123", "46,000"],
        ]
    ]

    context = _pdf_context([_page(tables=tables)])
    with patch.object(pdf_parser.pdfplumber, "open", return_value=context):
        prices = extract_supply_prices(path)

    assert prices == [SupplyPrice("84A", 84.9123, 45000, 1)]
