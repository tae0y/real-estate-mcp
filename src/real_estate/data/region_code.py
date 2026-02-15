"""Legal district code lookup module.

Finds the 5-digit legal district code (LAWD_CD) used as the API parameter
for the MOLIT apartment trade API from free-form user input.

Codes in the file are 10 digits (e.g. 1144000000).
The API uses only the first 5 digits (e.g. 11440).
Rows representing a gu/gun district have "00000" in the last 5 digits.
"""

from pathlib import Path
from typing import Any, TypedDict

REGION_FILE = Path(__file__).parent.parent / "resources" / "region_codes.txt"


class RegionMatch(TypedDict):
    """A single match result."""

    code: str  # Original 10-digit code
    name: str


class RegionResult(TypedDict, total=False):
    """Return type of search_region_code."""

    region_code: str  # 5-digit code for the API parameter
    full_name: str
    matches: list[RegionMatch]
    error: str
    message: str


def _load_region_rows() -> list[tuple[str, str]]:
    """Load (code, name) rows from the region code file.

    Returns:
        List of (10-digit code, name) tuples for active districts.
    """
    rows: list[tuple[str, str]] = []
    with REGION_FILE.open(encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            code, name, status = parts[0], parts[1], parts[2]
            if status == "존재":
                rows.append((code, name))
    return rows


def _to_api_code(ten_digit: str) -> str:
    """Extract the 5-digit API code from a 10-digit legal district code.

    Parameters:
        ten_digit: 10-digit legal district code (e.g. "1144000000")

    Returns:
        First 5 digits as a string (e.g. "11440")
    """
    return ten_digit[:5]


def _is_gu_gun(ten_digit: str) -> bool:
    """Return True if the code represents a gu/gun-level district (last 5 digits are "00000").

    Parameters:
        ten_digit: 10-digit legal district code
    """
    return ten_digit[5:] == "00000"


def search_region_code(query: str) -> dict[str, Any]:
    """Convert a free-form region name to a legal district code.

    Parameters:
        query: Free-form user input (e.g. "마포구", "서울 마포구 공덕동")

    Returns:
        region_code: 5-digit API parameter code (e.g. "11440")
        full_name: Name of the best-matched district
        matches: All matching results with original 10-digit codes and names
        error/message: Present when no match is found or the file is missing

    Notes:
        - If a gu/gun-level row (last 5 digits "00000") exists among matches,
          it is selected as the representative result.
        - On multiple matches, the matches array should be shown to the user
          for confirmation before selecting a region_code.
    """
    query = query.strip()
    if not query:
        return {"error": "invalid_input", "message": "Region name must not be empty."}

    try:
        rows = _load_region_rows()
    except FileNotFoundError:
        return {"error": "file_not_found", "message": "Region code file not found."}

    # Split query into tokens: "서울 마포구" → ["서울", "마포구"], keep rows matching all tokens
    tokens = query.split()
    matched = [(code, name) for code, name in rows if all(tok in name for tok in tokens)]

    if not matched:
        return {
            "error": "no_match",
            "message": f"No region found for: {query}",
        }

    # Gu/gun-level rows first, then ascending by code
    matched.sort(key=lambda x: (not _is_gu_gun(x[0]), x[0]))

    matches: list[RegionMatch] = [{"code": c, "name": n} for c, n in matched]

    # Prefer gu/gun-level row; fall back to first match
    gu_gun = [(c, n) for c, n in matched if _is_gu_gun(c)]
    best_code, best_name = gu_gun[0] if gu_gun else matched[0]

    return {
        "region_code": _to_api_code(best_code),
        "full_name": best_name,
        "matches": matches,
    }
