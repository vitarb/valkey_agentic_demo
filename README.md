```markdown
# Valkey Agentic Demo 🚀

A complete micro-pipeline demonstrating how **Valkey** (a Redis fork) powers real-time, _agentic_ applications. News is ingested → enriched on GPU → fanned out to personalized feeds → streamed to a React UI — all observable via Prometheus and Grafana.

```

replay → enrich → topic:<T> ─┬→ fanout ─┬→ feed:<uid>
└→ doc:<id>

````

| Service           | Role                                                       | Metrics Port |
|------------------|------------------------------------------------------------|--------------|
| **replay**        | Streams CSV articles into `news_raw` at a fixed RPS        | `9114` |
| **enrich**        | Tags topics via zero-shot classification (GPU-optional)    | `9110` |
| **fanout**        | De-duplicates and distributes to per-user feeds            | `9111` |
| **user_reader**   | Load-generating reader that auto-ramps with user count     | `9112` |
| **user_seeder**   | Generates synthetic users and topic interests              | `9113` |
| **valkey_exporter** | Unified Valkey → Prometheus exporter (mem, p99, net I/O) | `9121` |
| **gateway**       | FastAPI websocket/API bridge for the UI                    | `8000` |
| **ui-react**      | Single-page React UI                                       | `8500` |
| **grafana**       | Metrics dashboards (auto-generated)                        | `3000` |

---

## 1. Quick Start

> **Requirements:** Docker ≥ 24, Docker Compose, Python 3.8+  
> GPU is optional — see below.

```bash
# Build, generate dataset, and start the full stack
make dev
````

The first run will:

1. Pull `valkey/valkey-extensions:8.1-bookworm` (includes JSON, Bloom, Search modules)
2. Install Python dependencies and cache HuggingFace models
3. **Generate a sample dataset** via
   `python tools/make_cc_csv.py 50000 data/news_sample.csv`
4. **Bootstrap Grafana dashboards** via
   `python tools/bootstrap_grafana.py`
5. Launch all services via Docker Compose

Access in your browser:

* **Feed UI:** [http://localhost:8500](http://localhost:8500)
* **Grafana:** [http://localhost:3000](http://localhost:3000)
* **Prometheus:** [http://localhost:9090](http://localhost:9090)

To stop:

```bash
make down     # Stop services (retain volumes)
make clear    # Full cleanup (removes volumes and Valkey tmp)
```

---

## 2. GPU Acceleration (Optional)

```bash
docker compose --profile gpu up --build -d
```

The `enrich_gpu` service runs with `USE_CUDA=1` and requires
`nvidia-container-toolkit` on the host.

| `ENRICH_USE_CUDA` | Behavior                                           |
| ----------------- | -------------------------------------------------- |
| `auto` (default)  | Use GPU if available (`torch.cuda.is_available()`) |
| `1`               | Force GPU usage                                    |
| `0`               | Force CPU usage                                    |

Check the **"Enrich replicas on GPU"** Grafana panel to see CUDA usage.

---

## 3. Regenerating Artifacts

### 3.1 Dataset

To generate a larger or smaller dataset:

```bash
python tools/make_cc_csv.py 100000 data/news_sample.csv
```

This is equivalent to the Makefile alias:

```bash
make data
```

### 3.2 Grafana Dashboards

After changing metrics or adding new panels:

```bash
python tools/bootstrap_grafana.py
```

This rewrites provisioning files and auto-increments the dashboard version
so Grafana hot-reloads.

---

## 4. Running Tests

```bash
make test
```

Tests use stubs to avoid downloading models and exercise all agents.

---

## 5. Project Structure

```
.
├── agents/                # All microservices
│   ├── enrich.py          # Topic classifier
│   ├── fanout.py          # Fan-out logic with Lua stream trim
│   └── ...                # reader, seeder, replay, etc.
├── api_gateway/           # FastAPI server for API + WebSocket
├── ui-react/              # React front-end app
├── grafana/               # Dashboards and provisioning (auto-generated)
├── tools/                 # Helper scripts (dataset, grafana bootstrap)
├── docker-compose.yml     # Full-stack service definition
├── Dockerfile             # Multi-stage build (CPU/GPU support)
└── Makefile               # Entry points for dev: up / down / data / test
```

---

## 6. Tips & Tricks

* **Scale services** dynamically:

  ```bash
  docker compose up --scale enrich=6 --scale fanout=3 --scale reader=4
  ```

* **Mix CPU and GPU workers** by running both `enrich` and `enrich_gpu`.

* **Tune backlog limits** using environment variables:

  | Variable          | Description                     | Default |
  | ----------------- | ------------------------------- | ------- |
  | `NEWS_RAW_MAXLEN` | Max items in raw article stream | `5000`  |
  | `TOPIC_MAXLEN`    | Max items per topic stream      | `10000` |
  | `FEED_LEN`        | Max items in per-user feed      | `100`   |

* **CORS support** is pre-enabled for local demo (React runs on `:8500`, API on `:8000`).
  Lock it down before deploying publicly.

---

## 7. CI / GitHub Actions

* `build.yml` – verifies build and checks Valkey module availability
* `frontend.yml` – Playwright tests for `ui-react`

---

## 8. License

MIT — free for commercial and non-commercial use.

---

> 🧠 Found a bug? Have an idea?
> PRs and feedback welcome — or ping [@vitarb](https://github.com/vitarb)!

```

