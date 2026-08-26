# fastapi-slice

A minimal FastAPI-style web framework slice. Demonstrates dependency injection, route handlers, and data models.

## Example questions

1. "What would break if I removed the `Depends()` helper?"
2. "Which route handlers call `get_db`?"
3. "What is the full call chain from `create_app` down to the database?"
4. "Find the definition of `require_auth` and show its source."
5. "What is the shortest dependency path between `list_users` and `get_db`?"
