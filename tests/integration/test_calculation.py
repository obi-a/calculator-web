"""PostgreSQL persistence, validation, and ownership tests."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.calculation import Calculation
from app.schemas.calculation import CalculationCreate, CalculationRead


@pytest.mark.parametrize(
    "calculation_type, expected",
    [("add", 12.5), ("subtract", 7.5), ("multiply", 25), ("divide", 4)],
)
def test_calculation_round_trip(db_session, test_user, calculation_type, expected):
    data = CalculationCreate(a=10, b=2.5, type=calculation_type, user_id=test_user.id)
    calculation = Calculation(**data.model_dump())
    db_session.add(calculation)
    db_session.commit()
    calculation_id = calculation.id
    owner_id = test_user.id
    db_session.expunge_all()

    stored = db_session.get(Calculation, calculation_id)
    assert stored.user_id == owner_id
    assert stored.a == 10
    assert stored.b == 2.5
    assert stored.type == calculation_type
    assert stored.result == pytest.approx(expected)
    response = CalculationRead.model_validate(stored).model_dump(mode="json")
    assert response["id"] == str(calculation_id)
    assert response["user_id"] == str(owner_id)
    assert response["type"] == calculation_type
    assert response["result"] == pytest.approx(expected)
    assert set(response) == {"id", "user_id", "a", "b", "type", "result"}


def test_calculations_can_be_filtered_by_owner(db_session, seed_users):
    first_owner, second_owner = seed_users[:2]
    first = Calculation(user_id=first_owner.id, type="add", a=1, b=2)
    second = Calculation(user_id=second_owner.id, type="multiply", a=3, b=4)
    db_session.add_all([first, second])
    db_session.commit()

    owned = db_session.query(Calculation).filter_by(user_id=first_owner.id).all()
    assert [calculation.id for calculation in owned] == [first.id]


def test_calculation_requires_existing_owner(db_session):
    calculation = Calculation(user_id=uuid4(), type="add", a=1, b=2)
    db_session.add(calculation)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(Calculation).count() == 0


def test_deleting_owner_removes_calculations(db_session, test_user):
    calculation = Calculation(user_id=test_user.id, type="add", a=1, b=2)
    db_session.add(calculation)
    db_session.commit()
    db_session.delete(test_user)
    db_session.commit()
    assert db_session.query(Calculation).count() == 0


@pytest.mark.parametrize(
    "changes",
    [{"type": "modulus"}, {"a": "invalid"}, {"b": float("inf")}, {"type": "divide", "b": 0}],
)
def test_invalid_input_is_not_persisted(db_session, test_user, changes):
    data = dict(a=10, b=2, type="add", user_id=test_user.id)
    data.update(changes)
    with pytest.raises(ValidationError):
        validated = CalculationCreate(**data)
        db_session.add(Calculation(**validated.model_dump()))
        db_session.commit()
    assert db_session.query(Calculation).count() == 0
