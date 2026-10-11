.PHONY: setup test lint demo bench report public-bench public-cross-load paderborn-bench public-report t0-failure-analysis t0-v2-freeze paderborn-v2-bench clean

setup:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	ruff check src tests

demo:
	python -m denso_a1.cli demo --out reports/demo

bench:
	python -m denso_a1.cli benchmark --out reports/benchmark --seeds 5

report:
	python -m denso_a1.cli report --benchmark reports/benchmark

public-bench:
	python -m denso_a1.cli public-benchmark --raw-root data/raw/cwru --out reports/cwru --seeds 5

public-cross-load:
	python -m denso_a1.cli public-benchmark --raw-root data/raw/cwru --out reports/cwru_cross_load --seeds 5 --split-mode cross_load

paderborn-bench:
	python -m denso_a1.cli paderborn-benchmark --raw-root data/raw/paderborn/extracted --out reports/paderborn --seeds 5 --condition N15_M07_F10

public-report:
	python -m denso_a1.cli public-report --benchmark reports/cwru

t0-failure-analysis:
	python -m denso_a1.cli t0-failure-analysis --raw-root data/raw/paderborn/extracted --out reports/t0_failure_analysis --seeds 5 --condition N15_M07_F10 --measurements 5

t0-v2-freeze:
	python -m denso_a1.cli t0-v2-freeze --out reports/t0_v2_protocol_freeze.json --measurements 5

paderborn-v2-bench:
	python -m denso_a1.cli paderborn-v2-benchmark --raw-root data/raw/paderborn/extracted --out reports/paderborn_v2 --freeze reports/t0_v2_protocol_freeze.json --seeds 5 --measurements 5

clean:
	rm -rf reports/demo reports/benchmark build dist src/denso_a1.egg-info
