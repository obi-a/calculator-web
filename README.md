# Module 10

Dockerhub URL:
https://hub.docker.com/r/decodeinvesting/calculator-web/

## Run tests locally

Use Python 3.11+ (3.12 recommended) and Docker Compose. From the project root:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium

docker compose up -d

pytest
```

To run individual suites:

```bash
pytest tests/unit          # run only the unit tests
pytest tests/integration   # run integration tests
pytest tests/e2e           # run E2E tests
pytest                     # run all suites
```

