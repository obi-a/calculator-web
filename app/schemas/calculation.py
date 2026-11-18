# app/schemas/calculation.py
"""
Calculation Pydantic Schemas

This module defines Pydantic schemas for validating calculation data at the
API boundary. Pydantic provides automatic validation, serialization, and
documentation generation for FastAPI.

Key Concepts:
- Schemas define the shape of data coming in/out of the API
- Validation happens automatically before data reaches your code
- Field validators provide custom validation logic
- Model validators can validate across multiple fields
- ConfigDict controls schema behavior and documentation

Design Pattern: Data Transfer Objects (DTOs)
These schemas act as DTOs, defining contracts between API and clients.
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, FiniteFloat, field_validator, model_validator


class CalculationType(str, Enum):
    """
    Enumeration of valid calculation types.

    Using an Enum provides:
    1. Type safety: Only valid values can be used
    2. Auto-completion: IDEs can suggest valid values
    3. Documentation: Appears in OpenAPI when a route uses this schema
    4. Validation: Pydantic automatically rejects invalid values

    Inheriting from str makes this a string enum, so values serialize
    naturally as strings in JSON.
    """
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class CalculationCreate(BaseModel):
    """
    Schema for creating a new Calculation.

    This schema is used when a client wants to create a calculation.
    It includes the user_id to associate the calculation with a user.

    In a real application, the user_id would typically come from the
    authenticated user's session rather than the request body.
    """
    a: FiniteFloat
    b: FiniteFloat
    type: CalculationType
    user_id: UUID

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        """Normalize capitalization before the enum validates the calculation type."""
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_divisor(self):
        """
        Validate inputs based on calculation type.

        This demonstrates LBYL (Look Before You Leap) - we validate before
        attempting the operation.

        Returns:
            self: The validated model instance

        Raises:
            ValueError: If validation fails
        """
        if self.type == CalculationType.DIVIDE and self.b == 0:
            raise ValueError("Cannot divide by zero!")
        return self

    model_config = ConfigDict(from_attributes=True)


class CalculationRead(CalculationCreate):
    """
    Schema for reading a Calculation from the database.

    The from_attributes=True config allows this schema to be populated from
    SQLAlchemy model instances using CalculationRead.model_validate(db_calculation).
    """
    id: UUID
    result: float
