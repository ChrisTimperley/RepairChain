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

bundle:
	poetry run pyinstaller \
		src/repairchain/__main__.py \
		--noconfirm \
		--onefile \
		--name repairchain

check: lint test
