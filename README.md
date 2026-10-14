# Employee Payroll Management System

A Python-based Employee Payroll Management System designed using
Domain-Driven Design principles.

## Core Technologies

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- MySQL
- Alembic
- pytest

## Core Computer Science Areas

- Data Structures and Algorithms
- Object-Oriented Programming
- Database Management Systems
- Operating Systems and Concurrency
- Computer Networks
- Application Security

## Architecture

The backend follows a layered DDD-oriented architecture:

- Domain
- Application
- Infrastructure
- API

## Development and operations

See [the development runbook](documents/DEVELOPMENT_RUNBOOK.md) for verified
local setup, database initialization, seed-data, startup, health-check, and test
instructions. In particular, read its database and demonstration-account
warnings before initializing a database or testing privileged endpoints.
The React/Vite frontend foundation is in `frontend/`; its local setup, API base
URL, and authentication limitations are also documented in the runbook.
