"""Payroll Engine — Formulas and Calculation Components.

This module houses all computation logic and business formulas for employee payroll,
allowances, statutory deductions, tax rules, and attendance adjustments.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class EmployeePayrollInput:
    employee_id: int
    employee_code: str
    employee_name: str
    basic_salary: Decimal
    hra: Decimal = Decimal("0")
    da: Decimal = Decimal("0")
    special_allowance: Decimal = Decimal("0")
    travel_allowance: Decimal = Decimal("0")
    medical_allowance: Decimal = Decimal("0")
    other_allowances: Decimal = Decimal("0")
    bonus: Decimal = Decimal("0")
    overtime_hours: Decimal = Decimal("0")
    overtime_rate: Decimal = Decimal("0")
    provident_fund: Decimal = Decimal("0")
    esi: Decimal = Decimal("0")
    professional_tax: Decimal = Decimal("0")
    income_tax: Decimal = Decimal("0")
    insurance: Decimal = Decimal("0")
    loan_deduction: Decimal = Decimal("0")
    other_deductions: Decimal = Decimal("0")
    leave_deductions: Decimal = Decimal("0")
    working_days: int = 30
    present_days: Decimal = Decimal("30")


@dataclass
class CalculatedPayrollResult:
    employee_id: int
    basic_salary: Decimal
    allowances: Decimal
    overtime: Decimal
    leave_deductions: Decimal
    tax: Decimal
    other_deductions: Decimal
    gross_salary: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    component_breakdown: list[dict[str, Any]]


class PayrollEngine:
    """Core calculation engine implementing statutory Indian/Standard payroll formulas."""

    # Default Statutory Constants
    DEFAULT_HRA_PERCENT = Decimal("0.40")  # 40% of Basic
    DEFAULT_DA_PERCENT = Decimal("0.10")   # 10% of Basic
    DEFAULT_SPECIAL_ALLOWANCE_PERCENT = Decimal("0.08")  # 8% of Basic
    DEFAULT_PF_PERCENT = Decimal("0.12")   # 12% of Basic
    ESI_WAGE_LIMIT = Decimal("21000")      # ESI applicable if Gross/Basic <= 21,000
    ESI_PERCENT = Decimal("0.0075")        # 0.75% of Gross/Basic
    STANDARD_PT = Decimal("200")           # Professional Tax flat Rs 200/month
    STANDARD_TDS_PERCENT = Decimal("0.04") # 4% estimated standard TDS

    @classmethod
    def calculate_default_allowances(cls, basic: Decimal) -> dict[str, Decimal]:
        """Compute standard allowances based on basic salary."""
        return {
            "hra": (basic * cls.DEFAULT_HRA_PERCENT).quantize(Decimal("1.00")),
            "da": (basic * cls.DEFAULT_DA_PERCENT).quantize(Decimal("1.00")),
            "special_allowance": (basic * cls.DEFAULT_SPECIAL_ALLOWANCE_PERCENT).quantize(Decimal("1.00")),
            "travel_allowance": Decimal("1600.00"),
            "medical_allowance": Decimal("1250.00"),
            "other_allowances": Decimal("500.00"),
        }

    @classmethod
    def calculate_default_deductions(cls, basic: Decimal) -> dict[str, Decimal]:
        """Compute standard statutory deductions based on basic salary."""
        pf = (basic * cls.DEFAULT_PF_PERCENT).quantize(Decimal("1.00"))
        esi = (basic * cls.ESI_PERCENT).quantize(Decimal("1.00")) if basic <= cls.ESI_WAGE_LIMIT else Decimal("0.00")
        pt = cls.STANDARD_PT
        income_tax = (basic * cls.STANDARD_TDS_PERCENT).quantize(Decimal("1.00"))
        insurance = Decimal("450.00")

        return {
            "provident_fund": pf,
            "esi": esi,
            "professional_tax": pt,
            "income_tax": income_tax,
            "insurance": insurance,
            "loan_deduction": Decimal("0.00"),
            "other_deductions": Decimal("0.00"),
        }

    @classmethod
    def compute(cls, inp: EmployeePayrollInput) -> CalculatedPayrollResult:
        """Execute complete payroll computation for a single employee."""
        # 1. Allowances total
        allowances = (
            inp.hra
            + inp.da
            + inp.special_allowance
            + inp.travel_allowance
            + inp.medical_allowance
            + inp.other_allowances
        )

        # 2. Overtime calculation
        overtime = (inp.overtime_hours * inp.overtime_rate).quantize(Decimal("1.00"))

        # 3. Attendance adjustment / Unpaid leave deduction
        leave_deductions = inp.leave_deductions
        if inp.working_days > 0 and inp.present_days < inp.working_days:
            daily_rate = (inp.basic_salary + allowances) / Decimal(str(inp.working_days))
            unpaid_days = Decimal(str(inp.working_days)) - inp.present_days
            leave_deductions += (daily_rate * unpaid_days).quantize(Decimal("1.00"))

        # 4. Gross salary
        gross_salary = (inp.basic_salary + allowances + inp.bonus + overtime).quantize(Decimal("1.00"))

        # 5. Total deductions
        total_deductions = (
            inp.provident_fund
            + inp.esi
            + inp.professional_tax
            + inp.income_tax
            + inp.insurance
            + inp.loan_deduction
            + inp.other_deductions
            + leave_deductions
        ).quantize(Decimal("1.00"))

        # 6. Net salary (Gross - Deductions)
        net_salary = max(Decimal("0.00"), gross_salary - total_deductions)

        # 7. Component breakdown
        components = [
            {"code": "BASIC", "name": "Basic Salary", "type": "EARNING", "amount": float(inp.basic_salary)},
            {"code": "HRA", "name": "House Rent Allowance", "type": "EARNING", "amount": float(inp.hra)},
            {"code": "DA", "name": "Dearness Allowance", "type": "EARNING", "amount": float(inp.da)},
            {"code": "SPECIAL", "name": "Special Allowance", "type": "EARNING", "amount": float(inp.special_allowance)},
            {"code": "TRAVEL", "name": "Travel Allowance", "type": "EARNING", "amount": float(inp.travel_allowance)},
            {"code": "MEDICAL", "name": "Medical Allowance", "type": "EARNING", "amount": float(inp.medical_allowance)},
            {"code": "OTHER_EARN", "name": "Other Allowances", "type": "EARNING", "amount": float(inp.other_allowances)},
            {"code": "OVERTIME", "name": "Overtime", "type": "EARNING", "amount": float(overtime)},
            {"code": "PF", "name": "Provident Fund", "type": "DEDUCTION", "amount": float(inp.provident_fund)},
            {"code": "ESI", "name": "Employee State Insurance", "type": "DEDUCTION", "amount": float(inp.esi)},
            {"code": "PT", "name": "Professional Tax", "type": "DEDUCTION", "amount": float(inp.professional_tax)},
            {"code": "IT", "name": "Income Tax / TDS", "type": "DEDUCTION", "amount": float(inp.income_tax)},
            {"code": "INS", "name": "Insurance", "type": "DEDUCTION", "amount": float(inp.insurance)},
            {"code": "LEAVE_DED", "name": "Leave Deductions", "type": "DEDUCTION", "amount": float(leave_deductions)},
        ]

        return CalculatedPayrollResult(
            employee_id=inp.employee_id,
            basic_salary=inp.basic_salary,
            allowances=allowances,
            overtime=overtime,
            leave_deductions=leave_deductions,
            tax=inp.income_tax,
            other_deductions=inp.other_deductions,
            gross_salary=gross_salary,
            total_deductions=total_deductions,
            net_salary=net_salary,
            component_breakdown=components,
        )
