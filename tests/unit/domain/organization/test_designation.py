import pytest

from app.domain.organization.designation import Designation
from app.domain.shared.exceptions import BusinessRuleViolation


def test_designation_can_be_created() -> None:
    designation = Designation(
        designation_id=None,
        designation_code=" DEV ",
        designation_name=" Software Developer ",
    )

    assert designation.id is None
    assert designation.designation_code == "DEV"
    assert designation.designation_name == "Software Developer"
    assert designation.status == Designation.ACTIVE


def test_designation_normalizes_status() -> None:
    designation = Designation(
        designation_id=None,
        designation_code="DEV",
        designation_name="Software Developer",
        status=" inactive ",
    )

    assert designation.status == Designation.INACTIVE


def test_designation_rejects_blank_code() -> None:
    with pytest.raises(BusinessRuleViolation):
        Designation(
            designation_id=None,
            designation_code="   ",
            designation_name="Software Developer",
        )


def test_designation_rejects_blank_name() -> None:
    with pytest.raises(BusinessRuleViolation):
        Designation(
            designation_id=None,
            designation_code="DEV",
            designation_name="   ",
        )


def test_designation_rejects_invalid_status() -> None:
    with pytest.raises(BusinessRuleViolation):
        Designation(
            designation_id=None,
            designation_code="DEV",
            designation_name="Software Developer",
            status="DELETED",
        )


def test_designation_can_be_deactivated() -> None:
    designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
    )

    designation.deactivate()

    assert designation.status == Designation.INACTIVE


def test_designation_can_be_activated() -> None:
    designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
        status=Designation.INACTIVE,
    )

    designation.activate()

    assert designation.status == Designation.ACTIVE


def test_designation_can_be_renamed() -> None:
    designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
    )

    designation.rename("Senior Software Developer")

    assert designation.designation_name == "Senior Software Developer"


def test_designation_can_change_code() -> None:
    designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
    )

    designation.change_code("SDEV")

    assert designation.designation_code == "SDEV"


def test_designation_rejects_blank_rename() -> None:
    designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
    )

    with pytest.raises(BusinessRuleViolation):
        designation.rename("   ")


def test_designation_rejects_blank_code_change() -> None:
    designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
    )

    with pytest.raises(BusinessRuleViolation):
        designation.change_code("   ")