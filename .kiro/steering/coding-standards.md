# Coding Standards for Hybrid Cloud Controller

## Technical Standards
- Use Python 3.13+ syntax
- Implement proper error handling with specific exception types
- Use async/await for asynchronous operations (API calls, database queries, external services)
- Use Bulma CSS framework for the Web UI (or Bootstrap if already present)
- Prefer vanilla JavaScript over frameworks
- Run `ruff format` and `ruff check --fix` on all Python files after editing
- Prefer `pathlib.Path` over `os.path` for path operations

## Code Style
- Follow PEP8 and Ruff's formatting guidelines
- Use guard clauses with early returns rather than nested code
- Use `Optional[type]` for optional types (not `type | None`)
- Use builtin types for type hints (e.g., `list[int]` over `typing.List[int]`)

## Project Structure
- Keep components and functions small and focused
- Use proper file naming conventions (snake_case for modules)
- Prefer functions in modules over object-oriented programming (classes when they make sense)
- Use standalone `pytest.ini` for test configuration (not embedded in pyproject.toml)
- Use `requirements.piptools` for production dependencies
- Use `requirements-development.piptools` for development dependencies
- Keep dependencies in sync between requirements.piptools and pyproject.toml if both exist

## Tools
- Use `uv` for dependency management (`uv pip install`, `uv pip-compile`)
- Use `ruff.toml` for formatting rules if present
- Use `ruff format` and `ruff check` for formatting and linting

## Import Style

**Internal project imports:**
- **Functions**: Use namespace imports (`from package import module` → `module.function()`)
- **Classes/Exceptions**: Use direct imports (`from package.module import ClassName`)

**Examples:**
```python
# ✅ Functions - namespace import
from hybrid_cloud_controller.services import pricing_service
result = pricing_service.fetch_pricing_data()

# ✅ Classes/Exceptions - direct import
from hybrid_cloud_controller.models.configuration import Configuration
from hybrid_cloud_controller.exceptions import ValidationError

# ❌ Wrong - don't import functions directly
from hybrid_cloud_controller.services.pricing_service import fetch_pricing_data
```

## Development Configuration
- Web app development port: 10000 or higher
- Maintain `change-log.md` for major changes and features

## Change Log
When major changes or features are made/added, add a concise summary to `change-log.md` including:
- Description of the change
- Files involved (summarize if too many)
