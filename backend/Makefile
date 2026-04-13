.PHONY: test test-integration test-full test-stage

## Dev loop — unit only, sem I/O externo (< 2 min)
test:
	python -m pytest -m unit -q

## Pre-push — unit + integration (< 35 min)
test-integration:
	python -m pytest -m "unit or integration" -q

## CI nightly — suite completa incluindo benchmark
test-full:
	python -m pytest -q

## Smoke por stage: make test-stage N=3
test-stage:
	python -m pytest -m unit -k "stage$(N)" -q
