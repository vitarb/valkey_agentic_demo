.PHONY: dev down clear logs data test

SERVICES = enrich fanout reader replay dashboard grafana gateway ui_web valkey_exporter
SEED     = seed

dev:
	docker compose --profile cpu build --progress=plain
	docker compose --profile cpu up -d

down:
	COMPOSE_PROFILES=cpu,gpu docker compose down --remove-orphans

clear:
	docker compose down -v
	docker system prune -f
	rm -rf valkey/tmp || true

logs:
	@for s in $(SERVICES) $(SEED); do \
	  echo "\n===== $$s ====="; \
	  docker compose logs --tail 100 $$s || true; \
	done

data:
	python tools/make_cc_csv.py 50000 data/news_sample.csv
	@echo "CSV ready → data/news_sample.csv"

test:
	PYTHONPATH=$(CURDIR) pytest -q

