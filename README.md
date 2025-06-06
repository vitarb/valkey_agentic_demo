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
User feeds are stored in Redis lists, while topic streams remain implemented as
Redis streams.

## Running the demo

The easiest way to spin everything up is with Docker Compose.  Make sure Docker and Python 3.8+ are installed, then run:

```bash
make dev
```

The stack relies on `valkey/valkey-extensions:8.1-bookworm`, which includes the JSON, Bloom and Search modules out of the box.

The demo runs CPU-only by default. To use the CUDA build simply run

```bash
docker compose --profile gpu up --build -d
```

### GPU acceleration

The `enrich` service will automatically run on GPU when a CUDA device is
available.  This behaviour can be controlled via the `ENRICH_USE_CUDA`
environment variable:

* `auto` (default) – use GPU if `torch.cuda.is_available()`
* `1` – force GPU usage
* `0` – force CPU usage

GPU containers rely on the host's NVIDIA drivers. Make sure
`nvidia-container-toolkit` is installed so Docker can mount them
correctly.

This will build the containers, generate a small dataset and launch the services defined in `docker-compose.yml`.  When the stack is up you can explore:

* **Grafana** dashboards at <http://localhost:3000>
* **Prometheus** metrics at <http://localhost:9090>
* **React demo** at <http://localhost:8500>

To tear everything down run `make down` (or `make clear` to remove volumes).

## Tests

Basic unit tests live under the `tests/` directory and can be run with:

```bash
make test
```

## Contents

* `agents/` – microservices forming the data pipeline
* `tools/`  – helper scripts for bootstrapping demo data
* `valkey/valkey-extensions` image with JSON, Bloom and Search modules
* `demo.sh` and `manage.py` – utilities for launching a demo EC2 host

To lower backlog curves, set `TOPIC_MAXLEN=2000` in `docker-compose.yml`.

Feel free to modify the services or compose file to experiment further!

Both `/ws/feed/{uid}` and `/ws/topic/{slug}` accept an optional `backlog` query
parameter to stream the latest N items on connect.
