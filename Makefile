.PHONY: all check docker fix install lint test

all: install check

docker:
	docker build -t christimperley/repairchain .

type:
	poetry run mypy src

lint:
	poetry run ruff check src

test:
	poetry run pytest

fix:
	poetry run ruff check --fix src

install:
	poetry install --with dev

bundle:
	poetry run pyinstaller \
		src/repairchain/__main__.py \
		--noconfirm \
		--onefile \
		--name repairchain

check: lint type test
