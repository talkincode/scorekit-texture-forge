.PHONY: all install test clean lint

PYTHON ?= python3

all: test

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -v tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov out/
	find . -type d -name "__pycache__" -exec rm -rf {} +
