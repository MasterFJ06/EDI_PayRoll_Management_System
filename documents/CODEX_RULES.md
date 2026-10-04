# EPMS Codex Rules

## Rule 1 — Understand Before Editing

Never immediately start coding.

First:

- inspect the relevant files
- inspect related modules
- inspect the schema
- inspect existing tests
- inspect the Unit of Work
- inspect existing API patterns

---

# Rule 2 — Follow Existing Patterns

When implementing a new module, use the closest existing completed module as a reference.

For example:

Attendance Management can be used as an implementation-pattern reference for Workforce modules.

Employee Management can be used as a reference for employee-related behavior.

Organization Management can be used as a reference for organization CRUD.

Do not copy blindly.

Understand the architectural responsibility first.

---

# Rule 3 — Domain First

For a new business module:

1. identify domain concepts
2. identify domain rules
3. implement domain behavior
4. define application use cases
5. define persistence models/repositories
6. define API contracts
7. implement endpoints
8. write tests

---

# Rule 4 — No Frontend-Driven Backend Changes

The Claude-generated frontend contains mock data and prototype assumptions.

Do not modify the backend merely because the frontend expects:

- extra employee fields
- extra department fields
- extra attendance statuses
- fake payroll metrics
- frontend-only concepts

The backend architecture remains authoritative.

---

# Rule 5 — Schema First for Database Work

Before implementing database-backed functionality:

Read:

`database/schema.sql`

Confirm:

- table
- columns
- types
- primary keys
- foreign keys
- unique constraints
- checks
- indexes
- delete/update behavior

Never infer database structure from frontend TypeScript interfaces.

---

# Rule 6 — No Fake Data in Backend Tests

Tests may use controlled fixtures/factories.

Do not introduce hardcoded production-like mock behavior into application code.

---

# Rule 7 — Preserve Existing Public Contracts

When modifying existing modules:

- preserve existing API behavior unless the task explicitly changes it
- preserve existing response structures
- preserve exception handling
- preserve authentication behavior

If a breaking change appears necessary, stop and explain it.

---

# Rule 8 — Test Pyramid

For each module:

## Domain

Test:

- valid construction
- invalid construction
- business rules
- state transitions

## Application

Test:

- successful use cases
- missing entities
- duplicate entities
- business rule failures
- transaction behavior

## Repository

Test:

- retrieval
- insertion
- uniqueness
- relationships where appropriate

## API

Test:

- successful requests
- validation failures
- authentication
- authorization
- business errors
- response schema

---

# Rule 9 — Database Smoke Testing

Unit tests are not sufficient.

For database-backed modules:

1. run automated tests
2. start/reload Uvicorn
3. inspect Swagger
4. execute the relevant endpoint
5. verify database persistence
6. test an important negative case

---

# Rule 10 — Do Not Over-Refactor

If the current architecture works:

Do not rewrite it simply because another design is theoretically cleaner.

Especially do not introduce:

- CQRS
- event sourcing
- microservices
- message brokers
- unnecessary mapper frameworks
- unnecessary dependency injection frameworks

unless explicitly approved.

---

# Rule 11 — Security Is Backend Responsibility

Never trust:

- frontend role checks
- hidden UI buttons
- frontend route protection
- localStorage permissions

Security must be enforced server-side.

---

# Rule 12 — Git Discipline

Before implementation:

`git status`

After implementation:

- inspect diff
- run tests
- verify no unrelated changes
- report changed files

Do not automatically reset user changes.

---

# Rule 13 — Report Architectural Conflicts

If implementation requires an architectural decision that is not already documented:

STOP.

Report:

1. what is conflicting
2. why it conflicts
3. possible options
4. which existing decision is affected

Do not silently choose an architecture.

---

# Rule 14 — Completion Criteria

A module is not complete merely because its code exists.

A module is complete when:

- implementation exists
- tests exist
- tests pass
- API works
- database behavior is verified
- important negative cases are verified
- documentation/status is updated
- changes are reviewed
- Git checkpoint is created

---

# Rule 15 — Current Priority

The next implementation target is:

Leave Management.

Do not begin Payroll implementation until the prerequisite modules and architecture have been completed according to the project plan.