.PHONY: up down clear logs data test

SERVICES = enrich fanout reader replay dashboard grafana
SEED     = seed

up:
	docker compose up --build -d
	docker compose --profile $(SEED) up --build -d $(SEED)

down:
	docker compose down

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
	pytest -q
