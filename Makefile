PY ?= .venv/bin/python
HIFI ?= .venv/bin/hifi
.PHONY: install test demo demo-fx clean
install:
	python3 -m venv .venv && .venv/bin/pip install -e .[dev]
test:
	$(PY) -m pytest -q
demo:
	$(PY) examples/download_binance.py && $(HIFI) run --config examples/config.demo.yaml
demo-fx:
	for s in bid mid ask; do $(HIFI) fetch --symbol EURUSD --tf 15m --from 2025-01-06 --to 2025-01-13 --side $$s --out examples/data/EURUSD_15m_$$s.csv || exit 1; done
	$(HIFI) run --config examples/config.eurusd.yaml
clean:
	rm -rf out examples/data
