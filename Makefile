.PHONY: test typecheck ci

test:
	uv run pytest

typecheck:
	uv run mypy

ci: test typecheck
