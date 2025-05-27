# Valkey Agentic Demo 🚀

This repository contains a small end‑to‑end demo built around [Valkey](https://valkey.io) that showcases an asynchronous agentic pipeline.  Several microservices communicate via Valkey streams and publish metrics for Grafana via Prometheus.

```
replay → enrich → topic:<T> ──► fanout ──► feed:<uid>
                   │
                   └──► doc:<id>
```

The replay service publishes raw news to `news_raw`. The enrich agent classifies
and summarises those articles, caching each under `doc:<id>` and fan-out streams
under `topic:<T>`. The fanout service then distributes items to per-user feeds.

## Running the demo

The easiest way to spin everything up is with Docker Compose.  Make sure Docker and Python 3.8+ are installed, then run:

```bash
make dev
```

This will build the containers, generate a small dataset and launch the services defined in `docker-compose.yml`.  When the stack is up you can explore:

* **Grafana** dashboards at <http://localhost:3000>
* **Prometheus** metrics at <http://localhost:9090>
* **Dashboard** UI at <http://localhost:8501>

To tear everything down run `make down` (or `make clear` to remove volumes).

## Tests

Basic unit tests live under the `tests/` directory and can be run with:

```bash
make test
```

## Contents

* `agents/` – microservices forming the data pipeline
* `tools/`  – helper scripts for bootstrapping demo data
* `valkey/` – Valkey Docker image with JSON module
* `demo.sh` and `manage.py` – utilities for launching a demo EC2 host

Feel free to modify the services or compose file to experiment further!
