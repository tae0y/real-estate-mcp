"""Parsers for real estate lease/rent XML responses."""

from __future__ import annotations

from typing import Any

from defusedxml.ElementTree import fromstring as xml_fromstring


def _txt(item: Any, tag: str) -> str:
    return (item.findtext(tag) or "").strip()


def _parse_amount(raw: str) -> int | None:
    try:
        return int(raw.replace(",", ""))
    except ValueError:
        return None


def _parse_float(raw: str) -> float:
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _parse_int(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        return 0


def _parse_monthly_rent(item: Any) -> int:
    monthly_rent_raw = _txt(item, "monthlyRent")
    if not monthly_rent_raw:
        return 0
    return _parse_amount(monthly_rent_raw) or 0


def _make_date(item: Any) -> str:
    year = _txt(item, "dealYear")
    month = _txt(item, "dealMonth").zfill(2)
    day = _txt(item, "dealDay").zfill(2)
    return f"{year}-{month}-{day}" if year else ""


def _parse_apt_rent(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse apartment lease/rent XML response.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealType") == "O":
            continue
        deposit = _parse_amount(_txt(item, "deposit"))
        if deposit is None:
            continue
        items.append(
            {
                "unit_name": _txt(item, "aptNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "deposit_10k": deposit,
                "monthly_rent_10k": _parse_monthly_rent(item),
                "contract_type": _txt(item, "contractType"),
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
            }
        )
    return items, None


def _parse_officetel_rent(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse officetel lease/rent XML response.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        deposit = _parse_amount(_txt(item, "deposit"))
        if deposit is None:
            continue
        items.append(
            {
                "unit_name": _txt(item, "offiNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "deposit_10k": deposit,
                "monthly_rent_10k": _parse_monthly_rent(item),
                "contract_type": _txt(item, "contractType"),
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
            }
        )
    return items, None


def _parse_villa_rent(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse row-house / multi-family (연립다세대) lease/rent XML response.

    Includes house_type ("연립" or "다세대") to distinguish subtypes.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        deposit = _parse_amount(_txt(item, "deposit"))
        if deposit is None:
            continue
        items.append(
            {
                "unit_name": _txt(item, "mhouseNm"),
                "dong": _txt(item, "umdNm"),
                "house_type": _txt(item, "houseType"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "deposit_10k": deposit,
                "monthly_rent_10k": _parse_monthly_rent(item),
                "contract_type": _txt(item, "contractType"),
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
            }
        )
    return items, None


def _parse_single_house_rent(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse detached / multi-unit house lease/rent XML response.

    Area is totalFloorAr (gross floor area). No unit name provided.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        deposit = _parse_amount(_txt(item, "deposit"))
        if deposit is None:
            continue
        items.append(
            {
                "unit_name": "",  # not provided by this API
                "dong": _txt(item, "umdNm"),
                "house_type": _txt(item, "houseType"),
                "area_sqm": _parse_float(_txt(item, "totalFloorAr")),
                "deposit_10k": deposit,
                "monthly_rent_10k": _parse_monthly_rent(item),
                "contract_type": _txt(item, "contractType"),
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
            }
        )
    return items, None
