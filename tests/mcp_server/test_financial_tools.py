"""Unit tests for financial calculation MCP tools."""

import pytest

from real_estate.mcp_server.server import (
    calculate_compound_growth,
    calculate_loan_payment,
    calculate_monthly_cashflow,
)


class TestCalculateLoanPayment:
    """Tests for calculate_loan_payment."""

    def test_normal_case(self) -> None:
        result = calculate_loan_payment(principal_10k=30000, annual_rate_pct=3.5, years=30)
        assert result["monthly_payment_10k"] == pytest.approx(134.67, abs=0.1)

    def test_zero_interest(self) -> None:
        principal_10k = 24000
        years = 20
        result = calculate_loan_payment(principal_10k=principal_10k, annual_rate_pct=0, years=years)
        assert result["monthly_payment_10k"] == principal_10k / (years * 12)

    def test_validation_principal_zero(self) -> None:
        result = calculate_loan_payment(principal_10k=0, annual_rate_pct=3.5, years=30)
        assert result["error"] == "validation_error"

    def test_validation_years_zero(self) -> None:
        result = calculate_loan_payment(principal_10k=30000, annual_rate_pct=3.5, years=0)
        assert result["error"] == "validation_error"


class TestCalculateCompoundGrowth:
    """Tests for calculate_compound_growth."""

    def test_normal_case(self) -> None:
        result = calculate_compound_growth(
            initial_10k=5000,
            monthly_contribution_10k=50,
            annual_rate_pct=5.0,
            years=10,
        )
        assert result["final_value_10k"] > result["total_contributed_10k"]

    def test_zero_rate(self) -> None:
        initial_10k = 5000
        monthly_contribution_10k = 50.0
        years = 10
        result = calculate_compound_growth(
            initial_10k=initial_10k,
            monthly_contribution_10k=monthly_contribution_10k,
            annual_rate_pct=0,
            years=years,
        )
        assert result["final_value_10k"] == initial_10k + monthly_contribution_10k * years * 12

    def test_no_contribution(self) -> None:
        initial_10k = 5000
        annual_rate_pct = 5.0
        years = 10
        r = annual_rate_pct / 100 / 12
        n = years * 12
        expected = initial_10k * (1 + r) ** n

        result = calculate_compound_growth(
            initial_10k=initial_10k,
            monthly_contribution_10k=0,
            annual_rate_pct=annual_rate_pct,
            years=years,
        )
        assert result["final_value_10k"] == pytest.approx(expected, abs=0.01)

    def test_validation_years_zero(self) -> None:
        result = calculate_compound_growth(
            initial_10k=5000,
            monthly_contribution_10k=50,
            annual_rate_pct=5.0,
            years=0,
        )
        assert result["error"] == "validation_error"


class TestCalculateMonthlyCashflow:
    """Tests for calculate_monthly_cashflow."""

    def test_normal_case(self) -> None:
        result = calculate_monthly_cashflow(
            monthly_income_10k=500,
            monthly_loan_payment_10k=134.67,
            monthly_living_cost_10k=200,
        )
        assert result["monthly_cashflow_10k"] == pytest.approx(165.33, abs=0.01)

    def test_auto_living_cost(self) -> None:
        result = calculate_monthly_cashflow(
            monthly_income_10k=500,
            monthly_loan_payment_10k=100,
            monthly_living_cost_10k=0,
        )
        assert result["living_cost_auto_applied"] is True
        assert result["monthly_living_cost_10k"] == 200

    def test_negative_cashflow(self) -> None:
        result = calculate_monthly_cashflow(
            monthly_income_10k=300,
            monthly_loan_payment_10k=200,
            monthly_living_cost_10k=150,
        )
        assert result["monthly_cashflow_10k"] < 0
        assert "error" not in result

    def test_validation_income_zero(self) -> None:
        result = calculate_monthly_cashflow(
            monthly_income_10k=0,
            monthly_loan_payment_10k=100,
            monthly_living_cost_10k=100,
        )
        assert result["error"] == "validation_error"
