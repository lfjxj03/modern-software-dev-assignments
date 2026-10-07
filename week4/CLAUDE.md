# CLAUDE.md for Week 4

This file provides guidance to Claude Code when working with code in the week4 directory.

## Application Overview

Week 4 application is a full-stack "developer's command center" designed for practicing autonomous coding agent workflows. It consists of a FastAPI backend with SQLite and a vanilla JavaScript frontend.

## Key Architecture

### Backend Structure
- **Main app**: `backend/app/main.py` - FastAPI application entry point
- **Database**: `backend/app/db.py` - SQLAlchemy configuration and session management
- **Models**: `backend/app/models.py` - SQLAlchemy ORM models (Note, ActionItem)
- **Schemas**: `backend/app/schemas.py` - Pydantic models for validation
- **Routers**: `backend/app/routers/` - API route definitions
- **Services**: `backend/app/services/` - Business logic

### Frontend Structure
- **HTML**: `frontend/index.html` - Main application page
- **JavaScript**: `frontend/app.js` - Client-side logic and API interactions
- **CSS**: `frontend/styles.css` - Styling

## API Endpoints

### Notes
- `GET /notes/` - List all notes
- `POST /notes/` - Create a note
- `GET /notes/{id}` - Get specific note
- `GET /notes/search/?q=` - Search notes

### Action Items
- `GET /action-items/` - List all action items
- `POST /action-items/` - Create action item
- `PUT /action-items/{id}/complete` - Mark as completed

## Development Commands

Always run from the `week4/` directory:
- `make run` - Start development server
- `make test` - Run tests
- `make format` - Format code
- `make lint` - Lint code
- `make seed` - Initialize database

## Development Workflow

When asked to implement features:
1. Check `docs/TASKS.md` for suggested tasks
2. Look at existing tests in `backend/tests/` to understand expected behavior
3. Follow existing patterns in the codebase for consistency
4. Write tests for new functionality
5. Use the same Pydantic schemas and SQLAlchemy patterns as existing code

## Key Patterns

- Dependency injection for database sessions using `Depends(get_db)`
- Transaction management with automatic commit/rollback
- Request/response validation with Pydantic schemas
- Frontend-backend communication via fetch API
- Error handling with HTTPException

## Files to Check

- For new endpoints: look at existing routers in `backend/app/routers/`
- For database operations: reference `backend/app/db.py` and `models.py`
- For validation: check `backend/app/schemas.py`
- For business logic: examine `backend/app/services/`
- For tests: review `backend/tests/` files

## Common Tasks

When enhancing this application, consider:
- Maintaining the minimal, no-build-tools frontend approach
- Keeping the SQLite database approach for simplicity
- Following the existing FastAPI patterns for consistency
- Writing tests that match the existing test style