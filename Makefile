.PHONY: all check install lint

all: install check

lint:
	poetry run ruff check src
	poetry run mypy src

install:
	poetry install --with dev

check: lint test
