from datetime import datetime
from uuid import uuid4

import pytest

from app.models.user import User
from app.schemas.user import UserRead


def test_hash_password_does_not_store_plaintext():
    password = "TestPass123"
    hashed = User.hash_password(password)
    assert hashed != password
    assert password not in hashed


@pytest.mark.parametrize("password, matches", [("TestPass123", True), ("WrongPass123", False)])
def test_verify_password(password, matches):
    user = User(password_hash=User.hash_password("TestPass123"))
    assert user.verify_password(password) is matches


def test_password_hashes_use_different_salts():
    assert User.hash_password("TestPass123") != User.hash_password("TestPass123")


def test_user_read_from_orm_excludes_passwords():
    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        password_hash=User.hash_password("TestPass123"),
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    response = UserRead.model_validate(user).model_dump()
    assert response["id"] == user.id
    assert response["username"] == user.username
    assert response["email"] == user.email
    assert response["first_name"] is None
    assert response["last_name"] is None
    assert "password" not in response
    assert "password_hash" not in response
