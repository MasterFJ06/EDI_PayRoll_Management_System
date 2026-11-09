from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.unit_of_work import get_unit_of_work
from app.infrastructure.security.jwt import create_access_token
from app.main import app


class FakeEmployeeRepo:
    def __init__(self):
        self.employees = [
            SimpleNamespace(
                employee_id=1,
                employee_code="EMP001",
                first_name="Farhan",
                last_name="Akhtar",
                department_id=1,
                designation_id=1,
                user_id=1,
                employment_status="ACTIVE",
            )
        ]

    def get_all(self):
        return self.employees

    def get_by_id(self, emp_id):
        return next((e for e in self.employees if e.employee_id == emp_id), None)

    def get_by_code(self, code):
        return next((e for e in self.employees if e.employee_code == code), None)


class FakeDeptRepo:
    def get_by_id(self, dept_id):
        return SimpleNamespace(department_id=dept_id, name="Engineering")


class FakeDesigRepo:
    def get_by_id(self, desig_id):
        return SimpleNamespace(designation_id=desig_id, name="Lead Engineer")


class FakeSalaryRepo:
    def get_all(self):
        return [
            SimpleNamespace(
                salary_structure_id=1,
                employee_id=1,
                effective_from=datetime(2026, 4, 1).date(),
                base_salary=50000.0,
                provident_fund=6000.0,
                professional_tax=200.0,
                income_tax=3500.0,
            )
        ]

    def get_components(self, sid):
        return [
            SimpleNamespace(component_type="EARNING", amount=50000.0, salary_component_id=1),
            SimpleNamespace(component_type="EARNING", amount=25000.0, salary_component_id=2),
            SimpleNamespace(component_type="DEDUCTION", amount=6000.0, salary_component_id=3),
        ]

    def get_assignment_for_employee(self, emp_id):
        return None

    def get_revision_components(self, rev_id):
        return []


class FakePayrollRepo:
    def __init__(self):
        self.results = [
            SimpleNamespace(
                payroll_result_id=1,
                payroll_run_id=1,
                employee_id=1,
                gross_earnings=75000.0,
                total_deductions=9700.0,
                net_salary=65300.0,
                processed_at=datetime(2026, 8, 10, 10, 0),
            )
        ]
        self.runs = [
            SimpleNamespace(
                payroll_run_id=1,
                payroll_year=2026,
                payroll_month=8,
                status="FINALIZED",
            )
        ]

    def get_all_results(self):
        return self.results

    def get_runs(self):
        return self.runs

    def get_result_components(self, rid):
        return []

    def get_issues(self, run_id):
        return []


class FakePayslipRepo:
    def __init__(self):
        self.slips = [
            SimpleNamespace(
                payslip_id=1,
                payroll_result_id=1,
                payslip_number="PS-2026-08-EMP001",
                generated_by_user_id=1,
                generated_at=datetime(2026, 8, 10, 10, 30),
                document_path="/payslips/PS-2026-08-EMP001.pdf",
            )
        ]

    def get_all(self):
        return self.slips

    def add(self, slip):
        slip.payslip_id = len(self.slips) + 1
        self.slips.append(slip)
        return slip


class FakeUserRepo:
    def __init__(self):
        self.users = {
            1: SimpleNamespace(
                user_id=1,
                username="admin",
                email="admin@example.com",
                status="ACTIVE",
            )
        }

    def get_by_id(self, uid):
        return self.users.get(uid)


class FakeUnitOfWork:
    def __init__(self):
        self.employees = FakeEmployeeRepo()
        self.departments = FakeDeptRepo()
        self.designations = FakeDesigRepo()
        self.salaries = FakeSalaryRepo()
        self.payroll = FakePayrollRepo()
        self.payslips = FakePayslipRepo()
        self.users = FakeUserRepo()
        self.attendance = None
        self.leaves = None
        self.audits = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def fake_uow():
    uow = FakeUnitOfWork()
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    yield uow
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def auth_headers():
    token = create_access_token(user_id=1, username="admin")
    return {"Authorization": f"Bearer {token}"}


def test_list_deductions_api(fake_uow, client):
    res = client.get("/api/v1/deductions", headers=auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(d["type"] == "PF" for d in data)


def test_list_tax_rules_api(fake_uow, client):
    res = client.get("/api/v1/tax-rules", headers=auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any("Standard Deduction" in r["rule_name"] for r in data)


def test_list_payslips_api(fake_uow, client):
    res = client.get("/api/v1/payslips", headers=auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["id"] == "PS-2026-08-EMP001"


def test_get_single_payslip_api(fake_uow, client):
    res = client.get("/api/v1/payslips/PS-2026-08-EMP001", headers=auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "PS-2026-08-EMP001"
    assert data["employeeId"] == "EMP001"


def test_download_payslip_pdf_returns_genuine_pdf(fake_uow, client):
    res = client.get("/api/v1/payslips/PS-2026-08-EMP001/pdf", headers=auth_headers())
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in res.headers["content-disposition"]
    # Check that bytes are a genuine PDF file starting with %PDF-
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 500


def test_download_payslip_pdf_not_found_returns_404(fake_uow, client):
    res = client.get("/api/v1/payslips/NONEXISTENT_SLIP/pdf", headers=auth_headers())
    assert res.status_code == 404
    data = res.json()
    assert "not found" in data["detail"].lower()


def test_list_payroll_and_validation_api(fake_uow, client):
    res = client.get("/api/v1/payroll", headers=auth_headers())
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1

    res_val = client.get("/api/v1/payroll-validation", headers=auth_headers())
    assert res_val.status_code == 200
