"""Factory and arithmetic tests."""

from uuid import uuid4

import pytest

from app.models.calculation import Calculation
from app.operations import add, subtract, multiply, divide
from app.operations.factory import get_operation


@pytest.mark.parametrize(
    "calculation_type, operation",
    [("add", add), ("subtract", subtract), ("multiply", multiply), ("divide", divide)],
)
def test_factory_selects_existing_operation(calculation_type, operation):
    """Test that the factory is case-insensitive."""
    assert get_operation(calculation_type) is operation
    assert get_operation(calculation_type.upper()) is operation


@pytest.mark.parametrize("calculation_type", ["modulus", "", None, 123])
def test_factory_rejects_invalid_type(calculation_type):
    """
    This verifies that the factory pattern properly handles invalid inputs
    and provides clear error messages.
    """
    with pytest.raises(ValueError, match="Unsupported calculation type"):
        get_operation(calculation_type)


# ============================================================================
# Tests for Individual Calculation Types
# ============================================================================

@pytest.mark.parametrize(
    "calculation_type, a, b, expected",
    [
        ("add", -10, 2.5, -7.5),
        ("subtract", 10, 2.5, 7.5),
        ("multiply", -2.5, 4, -10),
        ("divide", 10, 4, 2.5),
        ("divide", 0, 4, 0),
    ],
)
def test_model_result(calculation_type, a, b, expected):
    calculation = Calculation(user_id=uuid4(), type=calculation_type, a=a, b=b)
    assert calculation.result == pytest.approx(expected)


def test_result_is_recomputed_when_operands_change():
    calculation = Calculation(user_id=uuid4(), type="add", a=10, b=5)
    assert calculation.result == 15
    calculation.b = 2
    assert calculation.result == 12


def test_model_division_by_zero():
    """
    Test that accessing the result raises ValueError for a zero divisor.
    The underlying divide function checks the divisor before performing division.
    """
    calculation = Calculation(user_id=uuid4(), type="divide", a=10, b=0)
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        _ = calculation.result
