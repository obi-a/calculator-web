# Module 12

- [GitHub repository](https://github.com/obi-a/calculator-web)
- [Docker Hub repository](https://hub.docker.com/r/decodeinvesting/calculator-web/)

## Run the application

Install Docker Desktop, then run from the project root:

```bash
export JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
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
