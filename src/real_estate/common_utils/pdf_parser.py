from __future__ import annotations

import importlib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, cast

_MAX_PDF_BYTES = 25 * 1024 * 1024
_MAX_PAGES = 200
_PRICE_KEYWORDS = ("공급금액", "공급가격", "분양가")
_MIN_TEXT_LENGTH = 100

_TYPE_KEYWORDS = ("주택형", "타입", "모델", "평형")
_AREA_KEYWORD = "전용면적"
_SUPPLY_PRICE_PATTERN = re.compile(r"(\d{2,3}[A-Z]?T?)\s+(\d{2,3}\.\d{2,4})\s+([\d,]+)")
_NUMBER_PATTERN = re.compile(r"\d[\d,]*")

type _Cell = str | None
type _Row = Sequence[_Cell]
type _Table = Sequence[_Row]
type _PageTexts = Sequence[tuple[int, str]]
type _SupplyPriceKey = tuple[str, float]


class _PdfPage(Protocol):
    def extract_text(self) -> str | None: ...

    def extract_tables(self) -> list[list[list[str | None]]]: ...


class _PdfDocument(Protocol):
    pages: Sequence[_PdfPage]

    def __enter__(self) -> _PdfDocument: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


class _PdfPlumberModule(Protocol):
    def open(self, path: str | Path) -> _PdfDocument: ...


pdfplumber = cast(_PdfPlumberModule, importlib.import_module("pdfplumber"))


@dataclass(frozen=True)
class SupplyPrice:
    """PDF에서 추출한 주택형별 공급금액."""

    unit_type: str
    exclusive_area_sqm: float
    supply_amount_10k: int
    source_page: int


def extract_text(pdf_path: str | Path, *, max_pages: int = _MAX_PAGES) -> str:
    """Extract plain text from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        max_pages: Maximum allowed page count.

    Returns:
        Extracted text with page text separated by blank lines.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is too large or exceeds max_pages.
    """
    pdf_path = _validate_pdf_file(pdf_path)
    text_parts: list[str] = []

    with _open_pdf(pdf_path) as pdf:
        _validate_page_count(pdf.pages, max_pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text is not None:
                text_parts.append(text)

    return "\n\n".join(text_parts)


def extract_supply_prices(pdf_path: str | Path) -> list[SupplyPrice]:
    """Extract supply prices from PDF tables or text.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A list of supply prices deduplicated by unit type and exclusive area.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is too large, has too many pages, or appears scanned.
    """
    pdf_path = _validate_pdf_file(pdf_path)
    prices: list[SupplyPrice] = []
    seen: set[_SupplyPriceKey] = set()
    page_texts: list[tuple[int, str]] = []
    has_tables = False

    with _open_pdf(pdf_path) as pdf:
        _validate_page_count(pdf.pages, _MAX_PAGES)
        for page_number, page in enumerate(pdf.pages, start=1):
            table_prices, page_has_tables = _extract_table_prices(page, page_number)
            has_tables = has_tables or page_has_tables
            _append_unique(prices, seen, table_prices)

            text = page.extract_text()
            if text:
                page_texts.append((page_number, text))

    if prices:
        return prices
    if _total_text_length(page_texts) < _MIN_TEXT_LENGTH and not has_tables:
        raise ValueError("OCR may be required: scanned PDF detected")

    _append_unique(prices, seen, _extract_regex_prices(page_texts))
    return prices


def _open_pdf(pdf_path: Path) -> _PdfDocument:
    return pdfplumber.open(pdf_path)


def _validate_pdf_file(pdf_path: str | Path) -> Path:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(path)

    size = path.stat().st_size
    if size > _MAX_PDF_BYTES:
        raise ValueError(f"PDF file too large ({size} bytes): {path}")
    return path


def _validate_page_count(pages: Sequence[_PdfPage], max_pages: int) -> None:
    page_count = len(pages)
    if page_count > max_pages:
        raise ValueError(f"PDF has too many pages ({page_count} > {max_pages})")


def _extract_table_prices(page: _PdfPage, page_number: int) -> tuple[list[SupplyPrice], bool]:
    tables = page.extract_tables() or []
    prices: list[SupplyPrice] = []

    for table in tables:
        header = _find_header(table)
        if header is None:
            continue
        header_index, price_col, type_col, area_col = header
        for row in table[header_index + 1 :]:
            price = _row_to_supply_price(row, price_col, type_col, area_col, page_number)
            if price is not None:
                prices.append(price)

    return prices, bool(tables)


def _find_header(table: _Table) -> tuple[int, int, int | None, int | None] | None:
    for row_index, row in enumerate(table):
        price_col = _find_col(row, _PRICE_KEYWORDS)
        type_col = _find_col(row, _TYPE_KEYWORDS)
        area_col = _find_col(row, (_AREA_KEYWORD,))
        if price_col is not None and (type_col is not None or area_col is not None):
            return row_index, price_col, type_col, area_col
    return None


def _find_col(row: _Row, keywords: Iterable[str]) -> int | None:
    for index, value in enumerate(row):
        cell = _normalize_cell(value)
        if any(keyword in cell for keyword in keywords):
            return index
    return None


def _row_to_supply_price(
    row: _Row,
    price_col: int,
    type_col: int | None,
    area_col: int | None,
    page_number: int,
) -> SupplyPrice | None:
    row_text = " ".join(_normalize_cell(cell) for cell in row)
    unit_text = _cell(row, type_col) if type_col is not None else row_text
    area_text = _cell(row, area_col) if area_col is not None else row_text

    unit_type = _extract_unit_type(unit_text) or _extract_unit_type(row_text)
    area = _extract_area(area_text) or _extract_area(row_text)
    amount = _parse_amount_10k(_cell(row, price_col))

    if unit_type is None or area is None or amount is None:
        return None
    return SupplyPrice(unit_type, area, amount, page_number)


def _extract_regex_prices(page_texts: _PageTexts) -> list[SupplyPrice]:
    prices: list[SupplyPrice] = []
    for page_number, text in _candidate_page_texts(page_texts):
        for match in _SUPPLY_PRICE_PATTERN.finditer(text):
            amount = _normalize_amount_10k(int(match.group(3).replace(",", "")))
            prices.append(SupplyPrice(match.group(1), float(match.group(2)), amount, page_number))
    return prices


def _candidate_page_texts(page_texts: _PageTexts) -> _PageTexts:
    keyword_pages = [
        (page_number, text)
        for page_number, text in page_texts
        if any(keyword in text for keyword in _PRICE_KEYWORDS)
    ]
    return keyword_pages or page_texts


def _append_unique(
    prices: list[SupplyPrice],
    seen: set[_SupplyPriceKey],
    candidates: Iterable[SupplyPrice],
) -> None:
    for price in candidates:
        key = (price.unit_type, price.exclusive_area_sqm)
        if key not in seen:
            seen.add(key)
            prices.append(price)


def _normalize_cell(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def _cell(row: _Row, index: int) -> str:
    if index >= len(row):
        return ""
    return _normalize_cell(row[index])


def _extract_unit_type(text: str) -> str | None:
    match = re.search(r"\d{2,3}[A-Z]?T?", text)
    if match is None:
        return None
    return match.group(0)


def _extract_area(text: str) -> float | None:
    match = re.search(r"\d{2,3}\.\d{2,4}", text)
    if match is None:
        return None
    return float(match.group(0))


def _parse_amount_10k(text: str) -> int | None:
    match = _NUMBER_PATTERN.search(text.replace(" ", ""))
    if match is None:
        return None
    return _normalize_amount_10k(int(match.group(0).replace(",", "")))


def _normalize_amount_10k(raw_value: int) -> int:
    if raw_value >= 100_000_000:
        return raw_value // 10_000
    return raw_value


def _total_text_length(page_texts: _PageTexts) -> int:
    return sum(len(text) for _, text in page_texts)
