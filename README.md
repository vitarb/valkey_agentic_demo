# Valkey Agentic Demo 🚀

This repository contains a small end‑to‑end demo built around [Valkey](https://valkey.io) that showcases an asynchronous agentic pipeline.  Several microservices communicate via Valkey streams and publish metrics for Grafana via Prometheus.

```
replay → enrich → topic:<T> ──► fanout ──► feed:<uid>
                   │
                   └──► doc:<id>
```

The replay service publishes raw news to `news_raw`. The enrich agent processes
those articles, caching each under `doc:<id>` and fan-out streams under
`topic:<T>`. The fanout service then distributes items to per-user feeds.

## Running the demo

The easiest way to spin everything up is with Docker Compose.  Make sure Docker and Python 3.8+ are installed, then run:

```bash
make dev
```

The base image installs a CPU build of PyTorch.  To enable CUDA support
during the build, pass `--build-arg USE_CUDA=1` when invoking Docker
Compose, e.g. `docker compose build --build-arg USE_CUDA=1`.

### GPU acceleration

The `enrich` service will automatically run on GPU when a CUDA device is
available.  This behaviour can be controlled via the `ENRICH_USE_CUDA`
environment variable:

* `auto` (default) – use GPU if `torch.cuda.is_available()`
* `1` – force GPU usage
* `0` – force CPU usage

This will build the containers, generate a small dataset and launch the services defined in `docker-compose.yml`.  When the stack is up you can explore:

* **Grafana** dashboards at <http://localhost:3000>
* **Prometheus** metrics at <http://localhost:9090>
* **Streamlit demo** at <http://localhost:8502> (User & Topic tabs)

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

To lower backlog curves, set `TOPIC_MAXLEN=2000` in `docker-compose.yml`.

Feel free to modify the services or compose file to experiment further!
