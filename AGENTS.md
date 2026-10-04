# EPMS — Codex Development Instructions

## Project

This repository contains the Employee Payroll Management System (EPMS), an enterprise-style academic software engineering project.

The system is being implemented using:

- Python 3.12+
- FastAPI
- Pydantic 2.x
- SQLAlchemy 2.x
- MySQL 8.x
- PyMySQL
- Alembic
- JWT authentication
- Argon2id password hashing
- pytest
- React + TypeScript + Vite + Tailwind for the frontend

The backend architecture is the source of truth.

---

# 1. READ BEFORE MODIFYING

Before making code changes:

1. Read `docs/ARCHITECTURE.md`.
2. Read `docs/DATABASE_SCHEMA.md`.
3. Read `docs/ARCHITECTURE_DECISIONS.md`.
4. Read `docs/API_CONTRACTS.md`.
5. Read `docs/DEVELOPMENT_STATUS.md`.
6. Read `docs/CODEX_RULES.md`.
7. Inspect the existing implementation and tests.
8. Inspect `database/schema.sql` before making database-related changes.

Do not begin implementation based only on the current task description.

---

# 2. ARCHITECTURE AUTHORITY

The following order of authority applies:

1. Explicit architecture decisions documented in `/docs`
2. `database/schema.sql` for the physical database schema
3. Existing implemented architecture and patterns
4. Current task requirements
5. Convenience or personal implementation preference

Do not redesign the architecture merely because another approach appears simpler.

---

# 3. DO NOT INVENT ARCHITECTURE

Do not:

- create duplicate services
- create duplicate repositories
- create duplicate Unit of Work implementations
- introduce new bounded contexts without approval
- create new database tables without approval
- add database columns without approval
- rename authoritative tables without approval
- invent relationships
- invent API contracts
- change existing architectural decisions for convenience
- introduce a new framework or major dependency without approval

If the required implementation appears to conflict with the architecture, STOP and explain the conflict before making architectural changes.

---

# 4. LAYERED ARCHITECTURE

Follow:

API
↓
Application
↓
Domain
↓
Infrastructure
↓
Database

Responsibilities:

## API

Responsible for:

- HTTP routes
- request/response DTOs
- authentication dependencies
- authorization dependencies
- HTTP-specific concerns

Do not put business logic in API endpoints.

## Application

Responsible for:

- use cases
- orchestration
- transaction boundaries
- application-level validation
- coordination between repositories/domain objects

## Domain

Responsible for:

- business rules
- domain entities
- domain value objects
- domain exceptions
- domain behavior

Do not make the domain depend on FastAPI or SQLAlchemy.

## Infrastructure

Responsible for:

- SQLAlchemy ORM models
- repositories
- database sessions
- Unit of Work implementation
- JWT implementation
- password hashing
- infrastructure services

## Database

MySQL/InnoDB is the persistence layer.

---

# 5. EXISTING CODE MUST BE INSPECTED FIRST

Before creating a new file:

1. Search the repository for an existing implementation.
2. Search for the relevant service.
3. Search for the relevant repository.
4. Search for the relevant ORM model.
5. Search the Unit of Work.
6. Search existing tests.
7. Follow established naming and structural conventions.

Never create a duplicate because the existing implementation was not immediately found.

---

# 6. DATABASE RULES

The authoritative physical schema is:

`database/schema.sql`

Do not invent schema elements.

The authoritative schema currently contains 27 tables.

Reporting & Analytics does not introduce additional authoritative tables.

Use SQLAlchemy repositories and the existing Unit of Work pattern.

Use transactions for state-changing operations.

---

# 7. SECURITY RULES

Passwords must never be stored in plaintext.

Use the existing password hashing implementation using Argon2id through `pwdlib`.

Authentication uses JWT access tokens.

Backend authorization is authoritative.

Do not rely on frontend route protection for security.

Validate request data using Pydantic.

Use parameterized SQL / SQLAlchemy.

Do not expose secrets in source code.

Do not commit `.env`.

---

# 8. TRANSACTION RULES

Use the existing Unit of Work.

State-changing operations must have a clear transaction boundary.

Do not manually create unrelated database sessions inside application services.

Repositories must use the Unit of Work session.

---

# 9. CONCURRENCY RULES

Payroll processing will eventually use bounded concurrency.

The planned approach includes:

- bounded worker pool
- independent database session per worker
- persisted payroll state
- transaction boundaries
- row locking where required
- consistent lock ordering
- bounded deadlock retry

Do not implement a different concurrency architecture without approval.

---

# 10. TESTING RULES

Every new backend module must include appropriate tests.

At minimum, consider:

- domain tests
- application/service tests
- repository/infrastructure tests
- API tests

Run the relevant tests after implementation.

Run the complete test suite before declaring a module complete.

Do not remove existing tests merely to make the suite pass.

Do not weaken assertions without justification.

---

# 11. ERROR HANDLING

Use the existing domain exception hierarchy and FastAPI exception handlers.

Do not create ad-hoc error response formats for individual endpoints.

Preserve request/correlation ID behavior.

---

# 12. GIT SAFETY

Before making significant changes:

- inspect git status
- inspect relevant existing files
- avoid unrelated modifications

Do not overwrite unrelated work.

Do not reset or discard user changes unless explicitly instructed.

Keep changes scoped to the current task.

---

# 13. IMPLEMENTATION STYLE

Prefer:

- small cohesive changes
- existing project conventions
- explicit typing
- clear names
- deterministic behavior
- testable services
- thin API endpoints

Avoid:

- unnecessary abstractions
- speculative features
- premature optimization
- unrelated refactoring
- large architectural rewrites

---

# 14. STOP CONDITIONS

Stop and ask for clarification before changing architecture when:

- a required feature needs a new authoritative table
- an existing table needs structural changes
- an existing bounded context needs to be split/merged
- a new major dependency is required
- existing architecture conflicts with the task
- the requested behavior contradicts documented architecture

Do not silently make architectural decisions.

---

# 15. FRONTEND

The frontend is currently a Claude-generated UI prototype.

The backend architecture is authoritative.

Do not modify the backend to accommodate frontend mock data or UI assumptions.

When frontend work begins, adapt the UI to the actual backend API contracts.

---

# 16. CURRENT DEVELOPMENT PHILOSOPHY

Implement the system incrementally.

Preferred cycle:

Plan
→ Inspect
→ Implement
→ Test
→ Review
→ Smoke test
→ Commit

Do not attempt to implement the entire EPMS in one operation.