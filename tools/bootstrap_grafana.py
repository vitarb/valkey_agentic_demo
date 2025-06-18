#!/usr/bin/env python3
"""(Re)generate the Grafana datasource and compact dashboard ‑ now in **4 columns**.

* Uses the unified *valkey_metrics_exporter.py* metric set (keeps the familiar
  `redis_*` names so the queries stay stable).
* Switches from a fixed 2‑column grid to **responsive 4‑column layout** so more
  panels fit on‑screen without endless scrolling.
"""

from __future__ import annotations
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
for sub in (
    "grafana/provisioning/datasources",
    "grafana/provisioning/dashboards",
    "grafana/dashboards",
):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────
#  Datasource (unchanged)
# ────────────────────────────────────────────────────
DS = (
    "apiVersion: 1\n"
    "datasources:\n"
    "- uid: prom\n"
    "  name: Prometheus\n"
    "  type: prometheus\n"
    "  url: http://prometheus:9090\n"
    "  isDefault: true\n"
)
(ROOT / "grafana/provisioning/datasources/prom.yaml").write_text(DS)

# ────────────────────────────────────────────────────
#  Small helper – auto‑places panels in a 4‑column grid
# ────────────────────────────────────────────────────
COLS: int = 4          # how many charts per row
W, H = 6, 8           # Grafana grid units (24 columns wide → 24/4 = 6)

panels: list[dict] = []


def add_panel(title: str, exprs: list[str] | tuple[str, ...], *, stack: bool = False, unit: str | None = None):
    """Append a timeseries panel and place it automatically."""
    idx = len(panels)
    row, col = divmod(idx, COLS)
    x, y = col * W, row * H
    tgts = [{"expr": e, "refId": chr(65 + i)} for i, e in enumerate(exprs)]

    opts: dict = {"legend": {"showLegend": stack}}
    if stack:
        opts["stacking"] = {"mode": "normal"}
    if unit:
        opts["standardOptions"] = {"unit": unit}

    panels.append({
        "type": "timeseries",
        "title": title,
        "datasource": {"uid": "prom"},
        "targets": tgts,
        "gridPos": {"x": x, "y": y, "w": W, "h": H},
        "options": opts,
    })


# ────────────────────────────────────────────────────
#  Dashboard contents (order ⇒ left‑to‑right, top‑to‑bottom)
# ────────────────────────────────────────────────────
add_panel("Producer msgs / s", ["sum(rate(producer_msgs_total[1m]))"])
add_panel("news_raw backlog", ["news_raw_len"], unit="none")
add_panel("Enrich msgs / s",
          ["rate(enrich_in_total[1m])", "sum(rate(enrich_out_total[1m]))"])
add_panel("Fan‑out backlog", ["sum(topic_stream_len)"], unit="none")

add_panel("Fan‑out msgs / s", ["sum(rate(fan_out_total[1m]))"])
add_panel("Reader pops / s", ["rate(reader_pops_total[1m])"])
add_panel("Feeds backlog", ["feed_backlog"])
add_panel("Valkey ops / s", ["rate(redis_commands_processed_total[1m])"])

add_panel("Valkey memory MB", [
          "redis_memory_used_bytes/1024/1024"], unit="bytes")
add_panel(
    "Valkey p99 µs",
    ["histogram_quantile(0.99, rate(redis_command_call_duration_seconds_bucket[2m])) * 1e6"],
    unit="µs",
)
add_panel("Enrich replicas on GPU", ["sum(enrich_gpu)"], unit="none")
add_panel("news_raw trim ops", ["irate(news_raw_trim_ops_total[5m])"])

add_panel("topic trim ops", ["irate(topic_stream_trim_ops_total[5m])"])
add_panel("Connected clients", ["redis_connected_clients"])
add_panel(
    "Cache hits vs misses /s",
    ["rate(redis_keyspace_hits_total[1m])",
     "rate(redis_keyspace_misses_total[1m])"],
    stack=True,
)
add_panel("CPU util (%)", ["rate(process_cpu_seconds_total[1m]) * 100"])

add_panel("Mem frag ratio", ["redis_mem_fragmentation_ratio"])

# ────────────────────────────────────────────────────
#  Assemble + write dashboard JSON
# ────────────────────────────────────────────────────
dashboard = {
    "uid": "agent-overview",
    "title": "Agent Overview",
    "schemaVersion": 38,
    "version": 7,          # bump so Grafana hot‑reloads
    "refresh": "5s",
    "panels": panels,
}
(ROOT / "grafana/dashboards/agent_overview.json").write_text(
    json.dumps(dashboard, indent=2)
)

# ────────────────────────────────────────────────────
#  Provider stub (unchanged)
# ────────────────────────────────────────────────────
PROV = (
    "apiVersion: 1\n"
    "providers:\n"
    "- name: Agentic Demo\n"
    "  folder: Agentic Demo\n"
    "  type: file\n"
    "  options:\n"
    "    path: /etc/grafana/dashboards\n"
)
(ROOT / "grafana/provisioning/dashboards/dash.yaml").write_text(PROV)

print("✓ Grafana provisioning updated – 4‑column layout (", len(panels), "panels)")
