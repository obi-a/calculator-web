# app/models/calculation.py

import uuid

from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.user import Base
from app.operations.factory import get_operation


class Calculation(Base):
    """All calculation types share the 'calculations' table"""
    __tablename__ = "calculations"

    # Unique identifier for each calculation (UUID for distribution)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key to the user who owns this calculation.
    #
    # CASCADE delete ensures calculations are deleted when user is deleted.
    # Index improves query performance when filtering by user_id.
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    type = Column(String(8), nullable=False)

    @property
    def result(self) -> float:
        """The computed result of the calculation."""
        return get_operation(self.type)(self.a, self.b)
