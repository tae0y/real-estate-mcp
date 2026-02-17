"""Unit tests for the legal district code search function and get_current_year_month tool."""

import re

from real_estate.mcp_server._region import search_region_code
from real_estate.mcp_server.server import get_current_year_month


class TestGetCurrentYearMonth:
    """Tests for get_current_year_month tool."""

    def test_returns_year_month_key(self) -> None:
        result = get_current_year_month()
        assert "year_month" in result

    def test_format_is_yyyymm(self) -> None:
        result = get_current_year_month()
        assert re.fullmatch(r"\d{6}", result["year_month"])


class TestSearchRegionCode:
    """Normal cases for search_region_code."""

    def test_gu_name_returns_five_digit_api_code(self) -> None:
        """A gu name input returns the 5-digit API code.

        Codes in the file are 10 digits (1144000000);
        region_code must return only the first 5 digits (11440).
        """
        result = search_region_code("마포구")
        assert "region_code" in result
        assert result["region_code"] == "11440"
        assert "full_name" in result
        assert "마포구" in result["full_name"]

    def test_full_path_returns_gu_code(self) -> None:
        """City + gu input returns the 5-digit gu-level code."""
        result = search_region_code("서울 마포구")
        assert "region_code" in result
        assert result["region_code"] == "11440"

    def test_dong_name_returns_matches(self) -> None:
        """A dong name input includes dong-level rows in matches."""
        result = search_region_code("공덕동")
        assert "matches" in result
        assert any("공덕동" in m["name"] for m in result["matches"])

    def test_multiple_tokens_all_must_match(self) -> None:
        """Multiple tokens return only rows that contain all tokens in the district name."""
        result = search_region_code("마포구 공덕동")
        assert "matches" in result
        for m in result["matches"]:
            assert "마포구" in m["name"]
            assert "공덕동" in m["name"]

    def test_gu_gun_row_is_first_in_matches(self) -> None:
        """The gu/gun-level row (last 5 digits 00000) is placed first in matches."""
        result = search_region_code("마포구")
        assert "matches" in result
        first = result["matches"][0]
        assert first["code"][5:] == "00000"


class TestSearchRegionCodeEdgeCases:
    """Edge cases for search_region_code."""

    def test_empty_string_returns_error(self) -> None:
        """An empty string input returns an error."""
        result = search_region_code("")
        assert "error" in result
        assert result["error"] == "invalid_input"

    def test_whitespace_only_returns_error(self) -> None:
        """Whitespace-only input returns an error."""
        result = search_region_code("   ")
        assert "error" in result
        assert result["error"] == "invalid_input"

    def test_unknown_region_returns_no_match(self) -> None:
        """An unknown region name returns a no_match error."""
        result = search_region_code("없는지역XYZ")
        assert "error" in result
        assert result["error"] == "no_match"
        assert "message" in result
        assert "없는지역XYZ" in result["message"]
