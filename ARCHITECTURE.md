# Architecture

## Request Flow

1. FastAPI validates the incoming request with a Pydantic schema.
2. Protected routes resolve the bearer token through the authentication dependency.
3. The route calls an application service rather than issuing database queries directly.
4. The service enforces the use case and delegates persistence to a repository.
5. The repository executes SQLAlchemy 2.x statements against PostgreSQL.
6. FastAPI serializes ORM objects through explicit response schemas.

## Authorization Boundary

JWT validation establishes identity. Authorization is enforced at the query boundary: task reads, updates, and deletes match both the task ID and authenticated owner ID. This prevents insecure direct object reference behavior and avoids leaking the existence of another user's records.

## Persistence

`User` has a one-to-many relationship with `Task`. Alembic owns schema evolution; application startup in Docker applies migrations rather than calling `create_all`. Composite indexes support the primary filtered-list access patterns. A functional unique index on `lower(email)` makes case-insensitive identity a database invariant, including under concurrent registration attempts.

## Configuration

Pydantic Settings reads environment variables and an optional local `.env`. The repository includes only `.env.example`. Docker Compose and CI inject separate non-production values.

## Testing Strategy

API tests exercise the application through FastAPI's test client and override only the database-session dependency. This keeps routing, authentication, services, repositories, validation, and error handling in scope. Local tests use isolated SQLite state for fast feedback. CI applies the real Alembic migration and runs the same behavioral suite on a dedicated PostgreSQL database, with cleanup between tests. PostgreSQL-only assertions cover timezone-aware timestamp round trips.

## Failure Handling

Validation errors use a structured error envelope. Authentication failures return `401` with the required bearer challenge, duplicate registration returns `409`, missing or non-owned tasks return `404`, and readiness returns `503` when the database cannot be reached. Request-scoped sessions roll back on exceptions. Request logging includes method, path, status, duration, and request ID without logging credentials or request bodies.
