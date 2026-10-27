PY ?= .venv/bin/python
.PHONY: install test demo clean
install:
	python3 -m venv .venv && .venv/bin/pip install -e .[dev]
test:
	$(PY) -m pytest -q
demo:
	$(PY) examples/download_binance.py && .venv/bin/hifi run --config examples/config.demo.yaml
clean:
	rm -rf out examples/data
