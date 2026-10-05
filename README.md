# Production Task API

A multi-user task management REST API built to demonstrate production-style Python backend engineering: secure authentication, user-scoped authorization, relational persistence, schema migrations, integration testing, containerized development, and continuous integration.

## Engineering Highlights

- JWT authentication with Argon2 password hashing and validated expiry, issuer, audience, and token type
- Owner-scoped queries that prevent cross-user task access
- PostgreSQL persistence through SQLAlchemy 2.x repositories
- Versioned Alembic database migrations
- Filtering, search, deterministic sorting, and bounded pagination
- Structured validation and error responses
- Health and database-readiness endpoints
- Behavior-focused API tests that run quickly on SQLite locally and against PostgreSQL in CI
- Docker Compose development environment with PostgreSQL health checks
- GitHub Actions checks for migrations, Ruff, MyPy, and pytest

## Architecture

```mermaid
flowchart LR
    Client[API client] --> Routes[FastAPI routes]
    Routes --> Auth[Authentication dependencies]
    Routes --> Services[Application services]
    Services --> Repositories[SQLAlchemy repositories]
    Repositories --> DB[(PostgreSQL)]
    Alembic[Alembic migrations] --> DB
```

Routes handle HTTP concerns, services enforce application rules, and repositories own database queries. Authentication is implemented as a reusable dependency so protected routes receive an authenticated `User` rather than decoding tokens independently.

## Tech Stack

Python 3.12+ · FastAPI · PostgreSQL · SQLAlchemy 2.x · Alembic · Pydantic · PyJWT · Argon2 · pytest · Ruff · MyPy · Docker · GitHub Actions

## API Endpoints

| Method | Endpoint | Authentication | Purpose |
|---|---|---:|---|
| `GET` | `/health` | No | Application liveness |
| `GET` | `/health/ready` | No | Database readiness |
| `POST` | `/auth/register` | No | Create an account |
| `POST` | `/auth/login` | No | Obtain a JWT access token |
| `GET` | `/users/me` | Yes | Retrieve the current profile |
| `POST` | `/tasks` | Yes | Create a task |
| `GET` | `/tasks` | Yes | Filter and paginate owned tasks |
| `GET` | `/tasks/{task_id}` | Yes | Retrieve an owned task |
| `PATCH` | `/tasks/{task_id}` | Yes | Update an owned task or its status |
| `DELETE` | `/tasks/{task_id}` | Yes | Delete an owned task |

`GET /tasks` supports `page`, `page_size`, `status`, `priority`, `search`, `sort_by`, and `sort_order`. Page size is limited to 100 records. Every ordering includes the task ID as a direction-matched tie-breaker, so page results are deterministic for equal sort values. Search treats `%` and `_` as literal characters rather than user-supplied SQL wildcard syntax.

## Authentication and Authorization

Registration stores an Argon2 password hash. Email addresses are normalized for application lookups, while a unique index on `lower(email)` protects against case-variant duplicates and registration races at the database boundary. Login returns a signed, time-limited JWT with validated subject, token type, issuer, audience, issued-at, expiry, and token ID claims. Inactive users cannot log in or use an existing token.

Every task query includes `owner_id`. Requests for another user's task return the same `404` response as a missing task, which avoids exposing whether another user's resource exists.

## Database Model

```mermaid
erDiagram
    USERS ||--o{ TASKS : owns
    USERS {
        int id PK
        string email UK
        string full_name
        string hashed_password
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    TASKS {
        int id PK
        string title
        text description
        string status
        string priority
        date due_date
        int owner_id FK
        datetime created_at
        datetime updated_at
    }
```

Composite indexes support common owner-plus-status and owner-plus-priority filters. A functional unique index enforces case-insensitive email uniqueness. The user relationship uses cascading deletion at both the ORM and foreign-key levels.

## Run with Docker

```bash
docker compose up --build
```

The API waits for PostgreSQL readiness, applies migrations, and starts on `http://localhost:8000`. Docker publishes the port only on `127.0.0.1`.

Stop the environment with:

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to remove the local PostgreSQL volume.

## Local Development

Start PostgreSQL through Docker, then run the API from a local virtual environment:

```bash
cp .env.example .env
docker compose up -d db

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

alembic upgrade head
uvicorn app.main:app --reload
```

Replace the placeholder values in `.env` for local use. Never commit `.env`.

## Example Requests

Register:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"developer@example.com","full_name":"API Developer","password":"replace-with-a-secure-password"}'
```

Log in and copy the returned `access_token`:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"developer@example.com","password":"replace-with-a-secure-password"}'
```

Create and filter tasks:

```bash
export ACCESS_TOKEN='paste-token-here'

curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Review API release","priority":"high","status":"in_progress","due_date":"2026-10-20"}'

curl 'http://localhost:8000/tasks?status=in_progress&priority=high&page=1&page_size=20' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

## Testing and Quality Checks

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

The test suite covers registration, case-insensitive uniqueness, duplicate-registration race handling and rollback, token expiry and claims, inactive accounts, task CRUD, owner isolation, literal search, deterministic pagination, validation boundaries, and PostgreSQL timestamp round trips. Local tests default to isolated in-memory SQLite for speed. CI applies Alembic migrations and runs the same API suite against PostgreSQL, so dialect-specific constraints and behavior are exercised rather than inferred from SQLite.

To run the suite against a dedicated local PostgreSQL test database, use a database whose name ends in `_test`:

```bash
export DATABASE_URL='postgresql+psycopg://task_api:task_api_test@localhost:5432/task_api_test'
export TEST_DATABASE_URL="$DATABASE_URL"
export JWT_SECRET_KEY='replace-with-a-test-secret-at-least-32-bytes'
alembic upgrade head
pytest
```

The `_test` suffix guard prevents the test cleanup fixture from targeting a normal development database.

## Continuous Integration

`.github/workflows/ci.yml` runs on pushes and pull requests. It starts PostgreSQL, installs development dependencies, applies migrations, checks for model/migration drift, runs lint and formatting checks, performs strict type checking, and executes the complete pytest suite against PostgreSQL using safe CI-only configuration.

## Repository Structure

```text
app/
├── api/              # Routes and authentication dependencies
├── core/             # Configuration, security, and logging
├── db/               # SQLAlchemy base and sessions
├── models/           # Relational database models
├── repositories/     # Owner-scoped database access
├── schemas/          # Pydantic request and response contracts
├── services/         # Authentication and task use cases
└── main.py            # FastAPI application and error handling
alembic/               # Versioned database migrations
scripts/               # Container startup and optional demo seeding
tests/                 # Behavior-focused API tests
Dockerfile
docker-compose.yml
pyproject.toml
requirements.txt
requirements-dev.txt
```

## Security Notes

- Secrets and database credentials are supplied through environment variables.
- Passwords are hashed with Argon2 and never returned by the API.
- JWT secrets must be random and at least 32 bytes in deployed environments.
- Login failures use a generic message to avoid distinguishing unknown, inactive, and incorrect-password accounts. Registration returns `409` for an existing email because clients need an actionable conflict response.
- Task lookups are scoped to the authenticated owner.
- This portfolio project implements access tokens only; refresh-token rotation, email verification, account recovery, and token revocation are outside the current scope.

## Engineering Decisions and Limitations

- **Authorization at query level:** reads, updates, and deletes select by both task ID and authenticated owner ID. A task is never loaded first and authorized afterward, reducing the chance of an IDOR regression.
- **Database-enforced identity:** application normalization improves UX, but the case-insensitive database index is the final protection against concurrent duplicate registrations.
- **Migrations rather than runtime schema creation:** Alembic provides reviewable schema history and CI checks for drift. The application does not call `create_all` in production startup.
- **Explicit transaction recovery:** request-scoped sessions roll back when a route fails, and duplicate registration handles the expected integrity error before returning `409`.
- **Simple deployment model:** Docker Compose runs migrations before one API process starts. A multi-replica deployment would need a separate, serialized migration job rather than every replica migrating on startup.
- **Offset pagination:** ordering is deterministic, but offset pagination can still shift if records are inserted between requests. Cursor pagination would be preferable for a high-write workload.
- **Authentication scope:** the API does not currently provide refresh tokens, revocation, rate limiting, email verification, or account recovery.

## Author

Yi Xin Ding
