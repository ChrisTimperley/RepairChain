.PHONY: all check docker fix install lint test

all: install check

docker:
	docker build -t christimperley/repairchain .

lint:
	poetry run ruff check src
	poetry run mypy src

test:
	poetry run pytest

fix:
	poetry run ruff check --fix src

install:
	poetry install --with dev

check: lint test
