.PHONY: artifacts help

help:
	@echo "make artifacts DOMAIN=<cafe|food>"


artifacts:
	python -m src.etl.00_eda_report --domain $(DOMAIN)
	python -m src.etl.01_filter_orders --domain $(DOMAIN)
	python -m src.etl.02_export_menu --domain $(DOMAIN)
	python -m src.etl.02_build_aliases --domain $(DOMAIN)
	python -m src.etl.03_build_fewshots --domain $(DOMAIN) --k 200 --only_order_draft
	python -m src.etl.04_build_evalset --domain $(DOMAIN) --n 300
	python -m src.etl.05_validate_artifacts --domain $(DOMAIN)
