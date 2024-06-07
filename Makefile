.PHONY: all check docker fix install lint

all: install check

docker:
	docker build -t christimperley/repairchain .

lint:
	poetry run ruff check src
	poetry run mypy src

fix:
	poetry run ruff check --fix src

install:
	poetry install --with dev

check: lint test
