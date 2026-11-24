"""HTTP integration tests for user authentication and calculation BREAD."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.calculation import Calculation
from app.models.user import User
from main import app, get_db


@pytest.fixture
def api_client(db_session):
    def override_db():
        yield db_session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def register_and_login(client, username="routeuser"):
    user_data = {
        "username": username,
        "email": f"{username}@example.com",
        "password": "TestPass123",
    }
    registered = client.post("/users/register", json=user_data)
    assert registered.status_code == 201, registered.text
    login = client.post("/users/login", json={
        "username": username, "password": user_data["password"],
    })
    assert login.status_code == 200, login.text
    return registered.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
def authenticated(api_client):
    return register_and_login(api_client)


def calculation_data(user, **changes):
    return {"a": 10, "b": 2, "type": "add", "user_id": user["id"], **changes}


def test_registration_persists_hashed_password(api_client, db_session):
    response = api_client.post("/users/register", json={
        "username": "registered", "email": "registered@example.com", "password": "TestPass123",
    })
    assert response.status_code == 201
    data = response.json()
    user = db_session.get(User, UUID(data["id"]))
    assert user.username == "registered"
    assert user.email == "registered@example.com"
    assert user.password_hash != "TestPass123"
    assert user.verify_password("TestPass123")
    assert data["first_name"] is None
    assert data["last_name"] is None
    assert data["is_active"] is True
    assert data["created_at"]
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.parametrize("field", ["username", "email"])
def test_duplicate_registration(api_client, authenticated, db_session, field):
    user, _ = authenticated
    payload = {"username": "different", "email": "different@example.com", "password": "TestPass123"}
    payload[field] = user[field]
    response = api_client.post("/users/register", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": "Username or email already exists"}
    assert db_session.query(User).count() == 1
    assert api_client.post("/users/register", json={
        "username": "afterduplicate", "email": "afterduplicate@example.com", "password": "TestPass123",
    }).status_code == 201


@pytest.mark.parametrize("changes", [
    {"email": "invalid"}, {"username": "ab"}, {"password": "Shor1"},
    {"password": "alllowercase1"}, {"password": "ALLUPPERCASE1"},
    {"password": "NoDigitsHere"}, {"password": None},
])
def test_invalid_registration_is_not_persisted(api_client, db_session, changes):
    response = api_client.post("/users/register", json={
        "username": "invaliduser", "email": "invaliduser@example.com", "password": "TestPass123", **changes,
    })
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)
    assert db_session.query(User).count() == 0


@pytest.mark.parametrize("password", ["Aa1" + "x" * 70, "Aa1" + "é" * 35])
def test_registration_rejects_passwords_over_72_utf8_bytes(api_client, db_session, password):
    response = api_client.post("/users/register", json={
        "username": "longpassword", "email": "longpassword@example.com", "password": password,
    })
    assert response.status_code == 400
    assert "72" in response.json()["error"]
    assert db_session.query(User).count() == 0


@pytest.mark.parametrize("password", ["Aa1" + "x" * 69, "Aa1" + "é" * 34 + "x"])
def test_password_byte_boundary_and_login_suffix(api_client, db_session, password):
    registered = api_client.post("/users/register", json={
        "username": "boundaryuser", "email": "boundary@example.com", "password": password,
    })
    assert registered.status_code == 201
    credentials = {"username": "boundaryuser", "password": password}
    assert api_client.post("/users/login", json=credentials).status_code == 200
    user = db_session.get(User, UUID(registered.json()["id"]))
    last_login = user.last_login
    rejected = api_client.post("/users/login", json={**credentials, "password": password + "!"})
    assert rejected.status_code == 400
    assert "72" in rejected.json()["error"]
    assert "access_token" not in rejected.json()
    db_session.refresh(user)
    assert user.last_login == last_login


@pytest.mark.parametrize("length", [120, 121, 129])
def test_registration_email_length_matches_database(api_client, db_session, length):
    email = "a" * 64 + "@" + "b" * (length - 69) + ".com"
    response = api_client.post("/users/register", json={
        "username": "emailboundary", "email": email, "password": "TestPass123",
    })
    if length == 120:
        assert response.status_code == 201
        assert db_session.get(User, UUID(response.json()["id"])).email == email
        assert api_client.post("/users/login", json={"username": email, "password": "TestPass123"}).status_code == 200
    else:
        assert response.status_code == 400
        assert "email" in response.json()["error"]
        assert db_session.query(User).count() == 0


@pytest.mark.parametrize("identifier", ["routeuser", "routeuser@example.com"])
def test_login_returns_token_and_updates_database(api_client, authenticated, db_session, identifier):
    user, _ = authenticated
    response = api_client.post("/users/login", json={"username": identifier, "password": "TestPass123"})
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert User.verify_token(data["access_token"]) == UUID(user["id"])
    assert data["user"]["id"] == user["id"]
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]
    assert db_session.get(User, UUID(user["id"])).last_login is not None


@pytest.mark.parametrize("username,password", [("routeuser", "wrong"), ("missinguser", "TestPass123")])
def test_invalid_login(api_client, authenticated, username, password):
    response = api_client.post("/users/login", json={"username": username, "password": password})
    assert response.status_code == 401
    assert response.json() == {"error": "Invalid username or password"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("payload", [{}, {"username": "routeuser"}, {"password": "TestPass123"}])
def test_login_requires_credentials(api_client, payload):
    assert api_client.post("/users/login", json=payload).status_code == 400


@pytest.mark.parametrize("operation,result", [("add", 12), ("subtract", 8), ("multiply", 20), ("divide", 5)])
def test_create_calculation_persists_and_serializes(api_client, authenticated, db_session, operation, result):
    user, headers = authenticated
    response = api_client.post("/calculations", json=calculation_data(user, type=operation.upper()), headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert set(data) == {"id", "user_id", "a", "b", "type", "result"}
    assert data["type"] == operation
    assert data["user_id"] == user["id"]
    assert data["result"] == result
    db_session.expunge_all()
    stored = db_session.get(Calculation, UUID(data["id"]))
    assert stored.type == operation
    assert stored.user_id == UUID(user["id"])
    assert stored.result == result


def test_calculation_bread_lifecycle(api_client, authenticated, db_session):
    user, headers = authenticated
    assert api_client.get("/calculations", headers=headers).json() == []
    created = api_client.post("/calculations", json=calculation_data(user), headers=headers).json()
    path = f"/calculations/{created['id']}"
    listed = api_client.get("/calculations", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == [created]
    read = api_client.get(path, headers=headers)
    assert read.status_code == 200
    assert read.json() == created
    updated = api_client.put(path, json=calculation_data(user, a=6, b=7, type="multiply"), headers=headers)
    assert updated.status_code == 200
    assert updated.json() == {**created, "a": 6, "b": 7, "type": "multiply", "result": 42}
    db_session.expunge_all()
    assert db_session.get(Calculation, UUID(created["id"])).result == 42
    assert api_client.get(path, headers=headers).json() == updated.json()
    deleted = api_client.delete(path, headers=headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert db_session.get(Calculation, UUID(created["id"])) is None
    assert api_client.get(path, headers=headers).status_code == 404
    assert api_client.get("/calculations", headers=headers).json() == []


INVALID_CALCULATIONS = [
    {"a": "invalid"}, {"b": None}, {"type": "modulus"}, {"user_id": "invalid-uuid"},
    {"type": "divide", "b": 0}, {"a": "NaN"}, {"b": "Infinity"},
    {"a": 1e308, "b": 1e308, "type": "multiply"},
]


@pytest.mark.parametrize("changes", INVALID_CALCULATIONS)
def test_invalid_create_does_not_persist(api_client, authenticated, db_session, changes):
    user, headers = authenticated
    response = api_client.post("/calculations", json=calculation_data(user, **changes), headers=headers)
    assert response.status_code == 400
    assert isinstance(response.json()["error"], str)
    assert db_session.query(Calculation).count() == 0


@pytest.mark.parametrize("changes", INVALID_CALCULATIONS)
def test_invalid_update_leaves_record_unchanged(api_client, authenticated, db_session, changes):
    user, headers = authenticated
    created = api_client.post("/calculations", json=calculation_data(user), headers=headers).json()
    path = f"/calculations/{created['id']}"
    response = api_client.put(path, json=calculation_data(user, **changes), headers=headers)
    assert response.status_code == 400
    assert api_client.get(path, headers=headers).json() == created
    stored = db_session.get(Calculation, UUID(created["id"]))
    assert (stored.a, stored.b, stored.type) == (10, 2, "add")


@pytest.mark.parametrize("field", ["a", "b", "type", "user_id"])
def test_create_and_put_require_complete_data(api_client, authenticated, field):
    user, headers = authenticated
    payload = calculation_data(user)
    created = api_client.post("/calculations", json=payload, headers=headers).json()
    del payload[field]
    assert api_client.post("/calculations", json=payload, headers=headers).status_code == 400
    path = f"/calculations/{created['id']}"
    assert api_client.put(path, json=payload, headers=headers).status_code == 400
    assert api_client.get(path, headers=headers).json() == created


@pytest.mark.parametrize("method", ["get", "put", "delete"])
@pytest.mark.parametrize("identifier,status_code", [("invalid-uuid", 400), (str(uuid4()), 404)])
def test_invalid_or_missing_record(api_client, authenticated, method, identifier, status_code):
    user, headers = authenticated
    kwargs = {"headers": headers}
    if method == "put":
        kwargs["json"] = calculation_data(user)
    response = api_client.request(method, f"/calculations/{identifier}", **kwargs)
    assert response.status_code == status_code
    assert isinstance(response.json()["error"], str)


PROTECTED_ROUTES = [("get", "/calculations"), ("post", "/calculations"),
                    ("get", "/calculations/{id}"), ("put", "/calculations/{id}"),
                    ("delete", "/calculations/{id}")]


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
@pytest.mark.parametrize("token_kind", ["missing", "invalid", "expired", "deleted", "basic"])
def test_calculation_authentication(api_client, authenticated, db_session, method, path, token_kind):
    user, headers = authenticated
    if token_kind == "missing":
        headers = {}
    elif token_kind == "invalid":
        headers = {"Authorization": "Bearer invalid.token"}
    elif token_kind == "expired":
        token = User.create_access_token({"sub": user["id"]}, expires_delta=timedelta(minutes=-1))
        headers = {"Authorization": f"Bearer {token}"}
    elif token_kind == "deleted":
        db_session.delete(db_session.get(User, UUID(user["id"])))
        db_session.commit()
    else:
        headers = {"Authorization": "Basic invalid"}
    kwargs = {"headers": headers}
    if method in {"post", "put"}:
        kwargs["json"] = calculation_data(user)
    response = api_client.request(method, path.format(id=uuid4()), **kwargs)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert isinstance(response.json()["error"], str)
    assert db_session.query(Calculation).count() == 0


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
def test_inactive_user_cannot_access_calculations(api_client, authenticated, db_session, method, path):
    user, headers = authenticated
    db_session.get(User, UUID(user["id"])).is_active = False
    db_session.commit()
    kwargs = {"headers": headers}
    if method in {"post", "put"}:
        kwargs["json"] = calculation_data(user)
    response = api_client.request(method, path.format(id=uuid4()), **kwargs)
    assert response.status_code == 400
    assert response.json() == {"error": "Inactive user"}


def test_calculations_are_isolated_between_users(api_client, authenticated, db_session):
    first_user, first_headers = authenticated
    second_user, second_headers = register_and_login(api_client, "seconduser")
    first = api_client.post("/calculations", json=calculation_data(first_user), headers=first_headers).json()
    second = api_client.post("/calculations", json=calculation_data(second_user), headers=second_headers).json()
    assert api_client.get("/calculations", headers=first_headers).json() == [first]
    assert api_client.get("/calculations", headers=second_headers).json() == [second]
    path = f"/calculations/{first['id']}"
    assert api_client.get(path, headers=second_headers).status_code == 404
    assert api_client.put(path, json=calculation_data(second_user), headers=second_headers).status_code == 404
    assert api_client.delete(path, headers=second_headers).status_code == 404
    assert api_client.post("/calculations", json=calculation_data(first_user), headers=second_headers).status_code == 403
    assert api_client.put(path, json=calculation_data(second_user), headers=first_headers).status_code == 403
    assert api_client.get(path, headers=first_headers).json() == first
    assert db_session.query(Calculation).count() == 2


def test_openapi_documents_required_routes_and_bearer_auth(api_client):
    schema = api_client.get("/openapi.json").json()
    routes = [("/users/register", "post"), ("/users/login", "post")]
    routes.extend((path, method) for method, path in PROTECTED_ROUTES)
    for path, method in routes:
        assert method in schema["paths"][path]
        assert "422" not in schema["paths"][path][method]["responses"]
    assert schema["components"]["schemas"]["UserCreate"]["properties"]["email"]["maxLength"] == 120
    for model in ("UserCreate", "UserLogin"):
        assert schema["components"]["schemas"][model]["properties"]["password"]["maxLength"] == 72
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/calculations"]["get"]["security"] == [{"HTTPBearer": []}]
    assert api_client.get("/docs").status_code == 200
    assert api_client.get("/redoc").status_code == 200


def test_documented_error_contract_matches_http_responses(api_client, authenticated):
    user, headers = authenticated
    schema = api_client.get("/openapi.json").json()
    cases = [
        ("post", "/users/register", "/users/register", {}, {}, 400),
        ("post", "/users/login", "/users/login", {"username": user["username"], "password": "wrong"}, {}, 401),
        ("get", "/calculations", "/calculations", None, {}, 401),
        ("post", "/calculations", "/calculations", calculation_data(user, user_id=str(uuid4())), headers, 403),
        ("get", f"/calculations/{uuid4()}", "/calculations/{id}", None, headers, 404),
        ("get", "/calculations/invalid", "/calculations/{id}", None, headers, 400),
        ("post", "/add", "/add", {}, {}, 400),
    ]
    for method, path, documented_path, payload, request_headers, expected_status in cases:
        kwargs = {"headers": request_headers}
        if payload is not None:
            kwargs["json"] = payload
        response = api_client.request(method, path, **kwargs)
        assert response.status_code == expected_status
        assert set(response.json()) == {"error"}
        assert isinstance(response.json()["error"], str)
        responses = schema["paths"][documented_path][method]["responses"]
        assert "422" not in responses
        assert responses[str(expected_status)]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse",
        }
