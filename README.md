# Module 12

- [GitHub repository](https://github.com/obi-a/calculator-web)
- [Docker Hub repository](https://hub.docker.com/r/decodeinvesting/calculator-web/)

## Run the application

Install Docker Desktop, then run from the project root:

```bash
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose up --build -d web
```

Open <http://localhost:8000/> for the existing calculator,
<http://localhost:8000/docs> for interactive Swagger UI, or
<http://localhost:8000/redoc> for API documentation. Tables are created automatically
at startup using the models' shared SQLAlchemy metadata.

`DATABASE_URL` selects the PostgreSQL database. Compose configures it for the `db`
service; running Python on the host defaults to
`postgresql://postgres:postgres@localhost:5432/fastapi_db`.
`JWT_SECRET_KEY` configures the signing key and must be consistent across app
instances and restarts. The fallback `your-secret-key` is for local development
when the environment variable is unset. The export command above supplies a
generated key instead.
Access tokens expire after 30 minutes.

## Run tests locally

Use Python 3.11+ (3.12 recommended) and Docker Compose. From the project root:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium

docker compose up -d db
# Create this database once, after PostgreSQL is ready.
docker compose exec db createdb -U postgres fastapi_test_db

export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fastapi_test_db
pytest --run-slow
```

Individual suites:

```bash
pytest tests/unit
pytest tests/integration --run-slow
pytest tests/integration/test_api_routes.py
pytest tests/e2e
```

## Manual checks with OpenAPI

Start the application and open http://localhost:8000/docs. Use **Try it out**
and **Execute** to check the endpoints:

1. Register through `POST /users/register`; expect `201`. Save the returned user ID.
2. Log in through `POST /users/login`; expect `200`. Copy `access_token` into
   **Authorize**, entering only the token.
3. Create a calculation through `POST /calculations` using:
   `{"a":10,"b":2,"type":"add","user_id":"YOUR_USER_ID"}`.
   Expect `201` with result `12`. Save the calculation ID.
4. Call `GET /calculations` and `GET /calculations/{id}`; expect `200`
   and the saved calculation.
5. Update through `PUT /calculations/{id}` using:
   `{"a":6,"b":7,"type":"multiply","user_id":"YOUR_USER_ID"}`.
   Expect `200` with result `42`.
6. Call `DELETE /calculations/{id}`; expect `204`. Reading it again should return `404`.

A calculation with `"type":"divide"` and `"b":0` should return `400`.
