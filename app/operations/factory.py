"""Select existing arithmetic functions."""

from app.operations import add, subtract, multiply, divide


def get_operation(calculation_type: str):
    """
    Raises:
        ValueError: If calculation_type is not supported
    """
    operations = {
        "add": add,
        "subtract": subtract,
        "multiply": multiply,
        "divide": divide,
    }
    try:
        return operations[calculation_type.lower()]
    except (KeyError, AttributeError) as exc:
        raise ValueError(f"Unsupported calculation type: {calculation_type}") from exc
