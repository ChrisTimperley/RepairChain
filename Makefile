.PHONY: all check docker fix install lint test

all: install check

docker:
	docker build -t christimperley/repairchain .

type:
	poetry run mypy src

lint:
	poetry run ruff check --preview src

test:
	poetry run pytest test

fix:
	poetry run ruff check --preview --fix src

install:
	git submodule update --init --recursive extern/darjeeling
	git submodule update --init --recursive extern/kaskara
	git submodule update --init --recursive extern/dockerblade
	git submodule update --init --recursive extern/sourcelocation
	poetry install --with dev

bundle:
	poetry run pyinstaller \
		src/repairchain/__main__.py \
		--noconfirm \
		--onefile \
		--name repairchain \
		--hidden-import=tiktoken_ext.openai_public \
		--hidden-import=tiktoken_ext
	./dist/repairchain --help

check: lint type test
