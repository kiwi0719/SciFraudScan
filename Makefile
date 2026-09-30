.PHONY: install dev test lint fmt check examples examples-check demo package clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

fmt:
	$(PYTHON) -m ruff check --fix .

# Everything CI runs. Must be green before a PR.
check: lint test examples-check

# The examples are generated from a fixed seed; regenerating must not change them.
examples:
	$(PYTHON) benchmarks/generate_examples.py

examples-check:
	@tmp=$$(mktemp -d) && cp -R examples "$$tmp/" && \
	  $(PYTHON) benchmarks/generate_examples.py >/dev/null && \
	  diff -r "$$tmp/examples" examples >/dev/null; rc=$$?; rm -rf "$$tmp"; \
	  if [ $$rc -ne 0 ]; then echo "examples/ drifted from generate_examples.py"; exit 1; fi
	@echo "examples ok"

demo:
	$(PYTHON) scripts/scan.py examples/fabricated_trial.csv \
	  --group-column arm --time-column enrol_day \
	  --reported-stats examples/reported_stats.csv \
	  --p-values examples/p_values.csv --experimental

# Zip for upload as a Claude.ai skill. The top-level folder inside the zip must
# be named after `name:` in SKILL.md, whatever this checkout is called.
package:
	@rm -rf dist && mkdir -p dist/scifraudscan
	@tar -cf - --exclude .git --exclude dist --exclude .github --exclude tests \
	  --exclude __pycache__ --exclude .pytest_cache --exclude .ruff_cache \
	  --exclude .DS_Store . | tar -xf - -C dist/scifraudscan
	@cd dist && zip -qr scifraudscan.zip scifraudscan && rm -rf scifraudscan
	@echo "dist/scifraudscan.zip"

clean:
	rm -rf dist .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
