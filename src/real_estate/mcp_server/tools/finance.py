"""MCP tools for real estate financial calculations."""

from __future__ import annotations

from typing import Any

from real_estate.mcp_server import mcp


@mcp.tool()
def calculate_loan_payment(
    principal_10k: int,
    annual_rate_pct: float,
    years: int,
) -> dict[str, Any]:
    """Calculate equal principal+interest monthly payment (EMI) in 10k KRW units."""
    if principal_10k < 1:
        return {"error": "validation_error", "message": "principal_10k must be >= 1"}
    if annual_rate_pct < 0:
        return {"error": "validation_error", "message": "annual_rate_pct must be >= 0"}
    if years < 1:
        return {"error": "validation_error", "message": "years must be >= 1"}

    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        monthly = principal_10k / n
    else:
        growth = (1 + r) ** n
        monthly = principal_10k * r * growth / (growth - 1)

    total_payment = monthly * n
    total_interest = total_payment - principal_10k

    return {
        "monthly_payment_10k": round(monthly, 2),
        "total_payment_10k": round(total_payment, 2),
        "total_interest_10k": round(total_interest, 2),
        "principal_10k": principal_10k,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
    }


@mcp.tool()
def calculate_compound_growth(
    initial_10k: int,
    monthly_contribution_10k: float,
    annual_rate_pct: float,
    years: int,
) -> dict[str, Any]:
    """Calculate compounded asset growth with initial capital and monthly contributions."""
    if initial_10k < 0:
        return {"error": "validation_error", "message": "initial_10k must be >= 0"}
    if monthly_contribution_10k < 0:
        return {"error": "validation_error", "message": "monthly_contribution_10k must be >= 0"}
    if annual_rate_pct < 0:
        return {"error": "validation_error", "message": "annual_rate_pct must be >= 0"}
    if years < 1:
        return {"error": "validation_error", "message": "years must be >= 1"}

    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        final = initial_10k + monthly_contribution_10k * n
    else:
        growth = (1 + r) ** n
        final = initial_10k * growth + monthly_contribution_10k * (growth - 1) / r

    total_contributed = initial_10k + monthly_contribution_10k * n
    total_gain = final - total_contributed

    return {
        "final_value_10k": round(final, 2),
        "total_contributed_10k": round(total_contributed, 2),
        "total_gain_10k": round(total_gain, 2),
        "initial_10k": initial_10k,
        "monthly_contribution_10k": monthly_contribution_10k,
        "annual_rate_pct": annual_rate_pct,
        "years": years,
    }


@mcp.tool()
def calculate_monthly_cashflow(
    monthly_income_10k: float,
    monthly_loan_payment_10k: float,
    monthly_living_cost_10k: float,
    other_monthly_costs_10k: float = 0.0,
) -> dict[str, Any]:
    """Calculate monthly free cashflow after debt service and costs."""
    if monthly_income_10k <= 0:
        return {"error": "validation_error", "message": "monthly_income_10k must be > 0"}
    if monthly_loan_payment_10k < 0:
        return {"error": "validation_error", "message": "monthly_loan_payment_10k must be >= 0"}

    living_cost_auto_applied = monthly_living_cost_10k == 0
    living_cost_used = (
        monthly_income_10k * 0.4 if living_cost_auto_applied else monthly_living_cost_10k
    )
    cashflow = (
        monthly_income_10k - monthly_loan_payment_10k - living_cost_used - other_monthly_costs_10k
    )

    return {
        "monthly_cashflow_10k": round(cashflow, 2),
        "monthly_income_10k": monthly_income_10k,
        "monthly_loan_payment_10k": monthly_loan_payment_10k,
        "monthly_living_cost_10k": round(living_cost_used, 2),
        "other_monthly_costs_10k": other_monthly_costs_10k,
        "living_cost_auto_applied": living_cost_auto_applied,
    }
