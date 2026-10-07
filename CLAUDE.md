# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the codebase for CS146S: The Modern Software Developer course at Stanford University (fall 2025). The course teaches modern software development practices through weekly assignments that progressively build on a FastAPI + SQLite application for action item extraction from notes.

## Architecture & Structure

The repository is organized by weeks, with each week containing increasingly sophisticated implementations:

- **Week 1**: Introduction to prompting techniques (k-shot, chain-of-thought, tool calling, etc.)
- **Week 2**: Action Item Extractor - FastAPI + SQLite app with basic extraction logic
- **Weeks 4-5**: Full-stack applications with frontend, backend, and more advanced features
- **Weeks 6+**: Advanced topics building on previous weeks

Each week typically includes:
- `backend/` - FastAPI application with SQLAlchemy ORM
- `frontend/` - Static HTML/JavaScript frontend served by FastAPI
- `tests/` - Pytest-based tests
- `data/` - SQLite database files and seed data
- `assignment.md` - Weekly exercises and requirements

### Core Technology Stack
- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: Vanilla JavaScript, HTML/CSS (no build tools)
- **Dependencies**: Managed with Poetry
- **Testing**: Pytest
- **Formatting/Linting**: Black, Ruff
- **Local LLMs**: Ollama for AI-powered features

## Common Development Commands

### Environment Setup
```bash
# Activate conda environment (Python 3.12 required)
conda activate cs146s

# Install dependencies
poetry install

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Running Applications
```bash
# Navigate to specific week directory
cd week5  # or week4, etc.

# Start development server (with hot reload)
make run

# Or run directly with uvicorn from project root
poetry run uvicorn week5.backend.app.main:app --reload
```

### Testing & Quality Assurance
```bash
# Run tests for a specific week
cd week5 && make test
# Or from project root:
PYTHONPATH=. pytest week5/backend/tests

# Format code
cd week5 && make format
# Or format from project root:
poetry run black . && poetry run ruff check . --fix

# Lint code
cd week5 && make lint
# Or lint from project root:
poetry run ruff check .
```

### Database Management
```bash
# Seed the database
cd week5 && make seed
```

### Week-Specific Operations
Each week builds upon previous weeks, so you may need to:
- Pull required Ollama models: `ollama pull mistral-nemo:12b` and `ollama pull llama3.1:8b`
- Run week-specific assignments as outlined in each week's `assignment.md`

## Development Workflow Notes

- Each week introduces new concepts while building on previous weeks
- The course emphasizes AI-assisted development practices
- Tests are located in `tests/` directories for each week
- Assignment deliverables are documented in `assignment.md` files
- Code should be well-commented to document changes and rationale

## Troubleshooting

- Make sure to activate the correct Python environment before running commands
- Ensure the PYTHONPATH is set correctly when running commands from different directories

## 交互语言

- 默认使用简体中文与用户交流。
- 用户明确要求使用其他语言时，才切换语言。
- 代码、命令、API 名称、文件名、技术术语保持其原始形式。