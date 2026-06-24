.PHONY: seed run test clean

PYTHON ?= python3

seed:
	$(PYTHON) -m src.generate_data --output data/synthetic/cases.csv --count 200

run:
	$(PYTHON) -m pipeline.run_pipeline

test:
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf data/synthetic/*.csv data/warehouse.db output/*.html output/*.csv
