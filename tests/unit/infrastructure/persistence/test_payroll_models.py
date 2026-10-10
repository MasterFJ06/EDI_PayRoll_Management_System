from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.payroll_processing_issue import (
    PayrollProcessingIssueModel,
)
from app.infrastructure.persistence.models.payroll_result import PayrollResultModel
from app.infrastructure.persistence.models.payroll_result_component import (
    PayrollResultComponentModel,
)
from app.infrastructure.persistence.models.payroll_run import PayrollRunModel
from app.infrastructure.persistence.models.payroll_run_workforce_snapshot import (
    PayrollRunWorkforceSnapshotModel,
)
from app.infrastructure.persistence.models.payslip import PayslipModel


PAYROLL_MODELS = {
    "payroll_runs": PayrollRunModel,
    "payroll_run_workforce_snapshots": PayrollRunWorkforceSnapshotModel,
    "payroll_results": PayrollResultModel,
    "payroll_result_components": PayrollResultComponentModel,
    "payroll_processing_issues": PayrollProcessingIssueModel,
    "payslips": PayslipModel,
}


def test_payroll_models_register_exact_authoritative_tables() -> None:
    assert {table for table in Base.metadata.tables if table in PAYROLL_MODELS} == set(
        PAYROLL_MODELS
    )


def test_payroll_models_use_innodb_and_unsigned_bigint_keys_and_foreign_keys() -> None:
    for model in PAYROLL_MODELS.values():
        table = model.__table__
        assert table.dialect_options["mysql"]["engine"] == "InnoDB"
        for column in table.columns:
            if column.primary_key or column.foreign_keys:
                assert column.type.compile(dialect=mysql.dialect()) == "BIGINT UNSIGNED"
                for foreign_key in column.foreign_keys:
                    assert foreign_key.ondelete in {"RESTRICT", "CASCADE"}
                    assert foreign_key.onupdate == "RESTRICT"


def test_payroll_model_mysql_column_types_match_schema() -> None:
    expected_types = {
        "payroll_runs": {
            "payroll_run_id": "BIGINT UNSIGNED", "payroll_year": "SMALLINT UNSIGNED",
            "payroll_month": "TINYINT UNSIGNED", "status": "VARCHAR(20)",
            "initiated_by_user_id": "BIGINT UNSIGNED", "started_at": "DATETIME",
            "attempt_number": "BIGINT UNSIGNED",
            "attempt_lease_expires_at": "DATETIME(6)",
            "completed_at": "DATETIME", "finalized_at": "DATETIME",
            "created_at": "DATETIME", "updated_at": "DATETIME",
        },
        "payroll_run_workforce_snapshots": {
            "payroll_run_id": "BIGINT UNSIGNED",
            "employee_id": "BIGINT UNSIGNED",
            "attempt_number": "BIGINT UNSIGNED",
            "snapshot_at": "DATETIME(6)",
            "snapshot": "JSON",
        },
        "payroll_results": {
            "payroll_result_id": "BIGINT UNSIGNED", "payroll_run_id": "BIGINT UNSIGNED",
            "employee_id": "BIGINT UNSIGNED", "salary_assignment_id": "BIGINT UNSIGNED",
            "gross_earnings": "DECIMAL(15, 2)", "total_deductions": "DECIMAL(15, 2)",
            "net_salary": "DECIMAL(15, 2)", "processed_at": "DATETIME",
            "workforce_calculation_snapshot": "JSON",
        },
        "payroll_result_components": {
            "payroll_result_component_id": "BIGINT UNSIGNED",
            "payroll_result_id": "BIGINT UNSIGNED", "salary_component_id": "BIGINT UNSIGNED",
            "component_type": "VARCHAR(20)", "amount": "DECIMAL(15, 2)",
            "calculation_order": "INTEGER UNSIGNED",
        },
        "payroll_processing_issues": {
            "payroll_issue_id": "BIGINT UNSIGNED", "payroll_run_id": "BIGINT UNSIGNED",
            "employee_id": "BIGINT UNSIGNED", "issue_code": "VARCHAR(100)",
            "issue_message": "VARCHAR(1000)", "status": "VARCHAR(20)",
            "detected_at": "DATETIME", "resolved_at": "DATETIME",
        },
        "payslips": {
            "payslip_id": "BIGINT UNSIGNED", "payroll_result_id": "BIGINT UNSIGNED",
            "payslip_number": "VARCHAR(50)", "generated_by_user_id": "BIGINT UNSIGNED",
            "generated_at": "DATETIME", "document_path": "VARCHAR(500)",
        },
    }
    for table_name, model in PAYROLL_MODELS.items():
        actual = {
            column.name: column.type.compile(dialect=mysql.dialect())
            for column in model.__table__.columns
        }
        assert actual == expected_types[table_name]


def test_payroll_models_keep_authoritative_constraints_and_indexes() -> None:
    expected = {
        "payroll_runs": (
            {"pk_payroll_runs", "uq_payroll_period", "chk_payroll_month", "chk_payroll_run_status", "fk_payroll_run_initiator"},
            set(),
        ),
        "payroll_run_workforce_snapshots": (
            {
                "pk_payroll_run_workforce_snapshots",
                "fk_payroll_workforce_snapshot_run",
                "fk_payroll_workforce_snapshot_employee",
            },
            {"idx_payroll_run_workforce_snapshots_attempt"},
        ),
        "payroll_results": (
            {"pk_payroll_results", "uq_payroll_result_employee", "chk_payroll_gross_earnings", "chk_payroll_total_deductions", "chk_payroll_net_salary", "fk_payroll_result_run", "fk_payroll_result_employee", "fk_payroll_result_assignment"},
            {"idx_payroll_results_employee", "idx_payroll_results_assignment"},
        ),
        "payroll_result_components": (
            {"pk_payroll_result_components", "uq_payroll_result_component", "chk_payroll_result_component_type", "chk_payroll_component_amount", "fk_payroll_component_result", "fk_payroll_component_definition"},
            {"idx_payroll_result_components_component"},
        ),
        "payroll_processing_issues": (
            {"pk_payroll_processing_issues", "chk_payroll_issue_status", "chk_payroll_issue_resolution", "fk_payroll_issue_run", "fk_payroll_issue_employee"},
            {"idx_payroll_issues_run_status", "idx_payroll_issues_employee"},
        ),
        "payslips": (
            {"pk_payslips", "uq_payslip_result", "uq_payslip_number", "fk_payslip_result", "fk_payslip_generator"},
            set(),
        ),
    }
    for table_name, model in PAYROLL_MODELS.items():
        table = model.__table__
        constraint_names = {constraint.name for constraint in table.constraints}
        index_names = {index.name for index in table.indexes}
        assert expected[table_name][0] <= constraint_names
        assert expected[table_name][1] == index_names


def test_payroll_models_match_authoritative_column_names_and_nullability() -> None:
    expected = {
        "payroll_runs": {"payroll_run_id", "payroll_year", "payroll_month", "status", "initiated_by_user_id", "started_at", "attempt_number", "attempt_lease_expires_at", "completed_at", "finalized_at", "created_at", "updated_at"},
        "payroll_run_workforce_snapshots": {"payroll_run_id", "employee_id", "attempt_number", "snapshot_at", "snapshot"},
        "payroll_results": {"payroll_result_id", "payroll_run_id", "employee_id", "salary_assignment_id", "gross_earnings", "total_deductions", "net_salary", "processed_at", "workforce_calculation_snapshot"},
        "payroll_result_components": {"payroll_result_component_id", "payroll_result_id", "salary_component_id", "component_type", "amount", "calculation_order"},
        "payroll_processing_issues": {"payroll_issue_id", "payroll_run_id", "employee_id", "issue_code", "issue_message", "status", "detected_at", "resolved_at"},
        "payslips": {"payslip_id", "payroll_result_id", "payslip_number", "generated_by_user_id", "generated_at", "document_path"},
    }
    nullable_columns = {
        "payroll_runs": {"started_at", "attempt_lease_expires_at", "completed_at", "finalized_at"},
        "payroll_run_workforce_snapshots": set(),
        "payroll_results": {"workforce_calculation_snapshot"},
        "payroll_result_components": set(),
        "payroll_processing_issues": {"employee_id", "resolved_at"},
        "payslips": set(),
    }
    for name, model in PAYROLL_MODELS.items():
        assert set(model.__table__.columns.keys()) == expected[name]
        for column in model.__table__.columns:
            assert column.nullable == (column.name in nullable_columns[name])
