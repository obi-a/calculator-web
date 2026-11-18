"""
These tests verify that Pydantic schemas correctly validate calculation data
before it reaches the application logic. This is an important security and
data integrity layer that prevents invalid data from entering the system.

Key Testing Concepts:
1. Valid Data: Ensure schemas accept correct data
2. Invalid Data: Ensure schemas reject incorrect data with clear messages
3. Edge Cases: Test boundary conditions
4. Business Rules: Verify domain-specific validation (e.g., no division by 0)
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.calculation import Calculation
from app.schemas.calculation import CalculationCreate, CalculationRead, CalculationType


# ============================================================================
# Tests for CalculationCreate Schema
# ============================================================================

@pytest.mark.parametrize("calculation_type", list(CalculationType))
def test_create_accepts_valid_data_and_normalizes_type(calculation_type):
    """Test CalculationCreate with valid data."""
    user_id = uuid4()
    data = CalculationCreate(a=-10.5, b=2, type=calculation_type.upper(), user_id=str(user_id))
    assert data.a == -10.5
    assert data.b == 2
    assert data.type == calculation_type
    assert data.user_id == user_id


@pytest.mark.parametrize("field", ["a", "b", "type", "user_id"])
def test_create_requires_all_fields(field):
    data = dict(a=10, b=2, type="add", user_id=uuid4())
    del data[field]
    with pytest.raises(ValidationError):
        CalculationCreate(**data)


@pytest.mark.parametrize(
    "changes",
    [
        {"type": "modulus"},  # Invalid type
        {"type": None},
        {"type": 123},
        {"user_id": "invalid-uuid"},
        {"a": "not-a-number"},
        {"b": None},
        {"a": float("nan")},
        {"b": float("inf")},
        {"a": float("-inf")},
        {"type": "divide", "b": 0},  # Division by zero
        {"type": "divide", "b": -0.0},
    ],
)
def test_create_rejects_invalid_data(changes):
    data = dict(a=10, b=2, type="add", user_id=uuid4())
    data.update(changes)
    with pytest.raises(ValidationError):
        CalculationCreate(**data)


def test_create_allows_zero_numerator():
    """Test that zero as the first input (numerator) is allowed."""
    data = CalculationCreate(a=0, b=5, type="divide", user_id=uuid4())
    assert data.a == 0


def test_read_serializes_orm_fields_without_sensitive_data():
    calculation = Calculation(id=uuid4(), user_id=uuid4(), a=10, b=5, type="add")
    calculation.password_hash = "must-not-be-serialized"
    data = CalculationRead.model_validate(calculation).model_dump(mode="json")
    assert data == {
        "id": str(calculation.id),
        "user_id": str(calculation.user_id),
        "a": 10,
        "b": 5,
        "type": "add",
        "result": 15,
    }
