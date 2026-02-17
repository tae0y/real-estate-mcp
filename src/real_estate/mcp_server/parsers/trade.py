"""Parsers for real estate sale (trade) XML responses."""

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


def _make_date(item: Any) -> str:
    year = _txt(item, "dealYear")
    month = _txt(item, "dealMonth").zfill(2)
    day = _txt(item, "dealDay").zfill(2)
    return f"{year}-{month}-{day}" if year else ""


def _parse_apt_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse apartment sale XML response.

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
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "apt_name": _txt(item, "aptNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_officetel_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse officetel sale XML response.

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
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "unit_name": _txt(item, "offiNm"),
                "dong": _txt(item, "umdNm"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_villa_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse row-house / multi-family (연립다세대) sale XML response.

    Includes house_type ("연립" or "다세대") for distinguishing subtypes.

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
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "unit_name": _txt(item, "mhouseNm"),
                "dong": _txt(item, "umdNm"),
                "house_type": _txt(item, "houseType"),
                "area_sqm": _parse_float(_txt(item, "excluUseAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_single_house_trades(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse detached / multi-unit house (단독/다가구) sale XML response.

    No unit name in the API response; area is totalFloorAr (gross floor area).
    jibun may be absent — handled as empty string.

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
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "unit_name": "",  # not provided by this API
                "dong": _txt(item, "umdNm"),
                "house_type": _txt(item, "houseType"),
                "area_sqm": _parse_float(_txt(item, "totalFloorAr")),
                "floor": 0,  # not applicable for detached houses
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
            }
        )
    return items, None


def _parse_commercial_trade(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Parse commercial / business building (상업업무용) sale XML response.

    Returns a different structure from residential tools:
    building_type, building_use, land_use, building_ar instead of unit_name/area_sqm.

    Returns:
        (items, None) on success; ([], error_code) on API error.
    """
    root = xml_fromstring(xml_text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code != "000":
        return [], result_code

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        if _txt(item, "cdealtype") == "O":
            continue
        price = _parse_amount(_txt(item, "dealAmount"))
        if price is None:
            continue
        items.append(
            {
                "building_type": _txt(item, "buildingType"),
                "building_use": _txt(item, "buildingUse"),
                "land_use": _txt(item, "landUse"),
                "dong": _txt(item, "umdNm"),
                "building_ar": _parse_float(_txt(item, "buildingAr")),
                "floor": _parse_int(_txt(item, "floor")),
                "price_10k": price,
                "trade_date": _make_date(item),
                "build_year": _parse_int(_txt(item, "buildYear")),
                "deal_type": _txt(item, "dealingGbn"),
                "share_dealing": _txt(item, "shareDealingType"),
            }
        )
    return items, None
