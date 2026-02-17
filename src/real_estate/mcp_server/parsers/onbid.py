"""Parsers for Onbid XML/JSON responses."""

from __future__ import annotations

from typing import Any

from defusedxml.ElementTree import fromstring as xml_fromstring


def _get_total_count_onbid(root: Any) -> int:
    """Extract total count from an Onbid ThingInfoInquireSvc XML response."""
    for tag in ("TotalCount", "totalCount", "totalcount"):
        raw = root.findtext(f".//{tag}")
        if raw:
            try:
                return int(raw)
            except ValueError:
                return 0
    return 0


def _onbid_extract_items(
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """Extract (result_code, body, items) from an Onbid JSON response."""
    if "response" in payload and isinstance(payload["response"], dict):
        response = payload["response"]
        header = response.get("header") or {}
        body = response.get("body") or {}
    else:
        header = payload
        body = payload

    result_code = str(header.get("resultCode") or "")

    items_obj = body.get("items")
    items: Any = None
    if isinstance(items_obj, dict):
        items = items_obj.get("item")
    elif isinstance(items_obj, list):
        items = items_obj
    else:
        items = body.get("item")

    if items is None:
        return result_code, body, []
    if isinstance(items, dict):
        return result_code, body, [items]
    if isinstance(items, list):
        out: list[dict[str, Any]] = []
        for it in items:
            if isinstance(it, dict):
                out.append(it)
        return result_code, body, out
    return result_code, body, []


def _parse_onbid_xml_items(
    xml_text: str,
) -> tuple[list[dict[str, Any]], int, str | None, str | None]:
    """Parse Onbid XML response into items and common metadata."""
    root = xml_fromstring(xml_text)
    result_code = (root.findtext(".//resultCode") or "").strip()
    result_msg = (root.findtext(".//resultMsg") or "").strip()
    if result_code != "00":
        return [], 0, result_code or None, result_msg or None

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        record: dict[str, Any] = {}
        for child in list(item):
            record[child.tag] = (child.text or "").strip()
        items.append(record)

    return items, _get_total_count_onbid(root), None, None


def _parse_onbid_thing_info_list_xml(
    xml_text: str,
) -> tuple[list[dict[str, Any]], int, str | None, str | None]:
    """Parse Onbid ThingInfoInquireSvc list XML response.

    Returns:
        items: list of dicts (tag -> text) per item
        total_count: total count parsed from the XML
        error_code: resultCode when not successful, else None
        error_message: resultMsg when not successful, else None
    """
    return _parse_onbid_xml_items(xml_text)


def _parse_onbid_code_info_xml(
    xml_text: str,
) -> tuple[list[dict[str, Any]], int, str | None, str | None]:
    """Parse OnbidCodeInfoInquireSvc XML response into a list of dict records."""
    return _parse_onbid_xml_items(xml_text)
