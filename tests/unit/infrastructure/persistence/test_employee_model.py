from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.models.employee import Employee


def test_employment_end_date_maps_to_nullable_mysql_date() -> None:
    column = Employee.__table__.c.employment_end_date

    assert column.type.compile(dialect=mysql.dialect()) == "DATE"
    assert column.nullable is True

