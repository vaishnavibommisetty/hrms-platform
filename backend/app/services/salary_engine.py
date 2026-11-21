"""
Salary calculation engine.

Turns an annual CTC plus a salary structure into a monthly breakdown.
Rules:
  * Monthly gross = annual CTC / 12
  * Components are calculated in `sequence` order
  * FIXED                -> the value itself (monthly amount)
  * PERCENTAGE_OF_GROSS  -> value% of monthly gross
  * PERCENTAGE_OF_BASIC  -> value% of the BASIC component
  * If earnings fall short of gross, the gap is paid as "Special Allowance"
"""
from decimal import Decimal, ROUND_HALF_UP

from app.models.salary import SalaryStructure, ComponentType, CalculationType

TWO = Decimal("0.01")


def _q(v: Decimal) -> Decimal:
    return v.quantize(TWO, rounding=ROUND_HALF_UP)


def calculate_breakdown(structure: SalaryStructure, annual_ctc) -> dict:
    gross = _q(Decimal(str(annual_ctc)) / 12)
    basic = Decimal("0")
    items = []

    for sc in sorted(structure.components, key=lambda c: (c.sequence or 0, c.id or 0)):
        comp = sc.component
        value = Decimal(str(sc.value))
        if comp.calculation_type == CalculationType.FIXED:
            amount = value
        elif comp.calculation_type == CalculationType.PERCENTAGE_OF_GROSS:
            amount = gross * value / 100
        else:
            amount = basic * value / 100
        amount = _q(amount)
        if comp.code.upper() == "BASIC":
            basic = amount
        items.append({
            "component_id": comp.id,
            "code": comp.code,
            "name": comp.name,
            "type": comp.component_type.value,
            "calculation": comp.calculation_type.value,
            "rate": float(value),
            "amount": amount,
            "sequence": sc.sequence or 0,
        })

    earnings = sum((i["amount"] for i in items if i["type"] == ComponentType.EARNING.value), Decimal("0"))
    if earnings < gross:
        items.append({
            "component_id": None,
            "code": "SPECIAL",
            "name": "Special Allowance",
            "type": ComponentType.EARNING.value,
            "calculation": "balancing",
            "rate": 0.0,
            "amount": _q(gross - earnings),
            "sequence": 999,
        })
        earnings = gross

    deductions = sum((i["amount"] for i in items if i["type"] == ComponentType.DEDUCTION.value), Decimal("0"))
    return {
        "monthly_gross": gross,
        "total_earnings": _q(earnings),
        "total_deductions": _q(deductions),
        "net_pay": _q(earnings - deductions),
        "items": items,
    }


def breakdown_json(b: dict) -> dict:
    """Same breakdown with Decimals converted for JSON responses."""
    return {
        "monthly_gross": float(b["monthly_gross"]),
        "total_earnings": float(b["total_earnings"]),
        "total_deductions": float(b["total_deductions"]),
        "net_pay": float(b["net_pay"]),
        "items": [{**i, "amount": float(i["amount"])} for i in b["items"]],
    }
