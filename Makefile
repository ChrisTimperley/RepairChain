.PHONY: all check install lint

all: install check

lint:
	poetry run ruff check src
	poetry run mypy src

fix:
	poetry run ruff check --fix src

install:
	poetry install --with dev

check: lint test
