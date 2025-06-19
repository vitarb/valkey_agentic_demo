#!/usr/bin/env python3
"""Generate / refresh Grafana provisioning (4‑column layout)."""

from __future__ import annotations
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
for sub in ("grafana/provisioning/datasources",
            "grafana/provisioning/dashboards",
            "grafana/dashboards"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

# ─── datasource (unchanged) ──────────────────────────────────────────
(ROOT / "grafana/provisioning/datasources/prom.yaml").write_text("""\
apiVersion: 1
datasources:
- uid: prom
  name: Prometheus
  type: prometheus
  url: http://prometheus:9090
  isDefault: true
""")

# ─── helper for 4‑col grid ───────────────────────────────────────────
COLS, W, H = 4, 6, 8
panels: list[dict] = []


def add(title: str, exprs, *, unit: str | None = None, stack=False):
    i = len(panels)
    x, y = (i % COLS) * W, (i // COLS) * H
    targets = [{"expr": e, "refId": chr(65 + n)} for n, e in enumerate(exprs)]
    opts = {"legend": {"showLegend": stack}}
    if stack:
        opts["stacking"] = {"mode": "normal"}
    if unit:
        opts["standardOptions"] = {"unit": unit}
    panels.append({
        "type": "timeseries", "title": title, "datasource": {"uid": "prom"},
        "targets": targets, "gridPos": {"x": x, "y": y, "w": W, "h": H},
        "options": opts,
    })


# ─── existing panels (unchanged order) ───────────────────────────────
add("Producer msgs /s", ["sum(rate(producer_msgs_total[1m]))"])
add("news_raw backlog", ["news_raw_len"], unit="none")
add("Enrich msgs /s", ["rate(enrich_in_total[1m])",
                       "sum(rate(enrich_out_total[1m]))"])
add("Fan‑out backlog", ["sum(topic_stream_len)"], unit="none")

add("Fan‑out msgs /s", ["sum(rate(fan_out_total[1m]))"])
add("Reader pops /s",  ["rate(reader_pops_total[1m])"])
add("Feeds backlog",   ["feed_backlog"])
add("Valkey ops /s",   ["rate(redis_commands_processed_total[1m])"])

add("Valkey memory MB", ["redis_memory_used_bytes/1024/1024"], unit="bytes")
add("Valkey p99 µs", [
    "histogram_quantile(0.99, rate(redis_command_call_duration_seconds_bucket[2m]))*1e6"
], unit="µs")
add("Valkey p50 µs", [
    "histogram_quantile(0.50, rate(redis_command_call_duration_seconds_bucket[2m]))*1e6"
], unit="µs")
add("Enrich replicas on GPU", ["sum(enrich_gpu)"], unit="none")
add("Reader target RPS", ["reader_target_rps"])
add("Avg feed backlog",  ["avg_feed_backlog"])

add("news_raw trim ops", ["irate(news_raw_trim_ops_total[5m])"])
add("topic trim ops",    ["irate(topic_stream_trim_ops_total[5m])"])
add("Connected clients", ["redis_connected_clients"])
add("Cache hits vs misses /s",
    ["rate(redis_keyspace_hits_total[1m])",
     "rate(redis_keyspace_misses_total[1m])"],
    stack=True)

add("Valkey net KB/s",
    ["rate(redis_net_input_bytes_total[1m])/1024",
     "rate(redis_net_output_bytes_total[1m])/1024"],
    unit="bytes")
add("Dataset memory MB",
    ["redis_memory_dataset_bytes/1024/1024"],
    unit="bytes")
add("CPU util (%)", ["rate(process_cpu_seconds_total[1m])*100"])
add("Mem frag ratio", ["redis_mem_fragmentation_ratio"])

# ─── write dashboard & provider files ────────────────────────────────
dashboard = {
    "uid": "agent-overview",
    "title": "Agent Overview",
    "schemaVersion": 38,
    "version": 11,               # bump → Grafana auto‑reload
    "refresh": "5s",
    "panels": panels,
}
(ROOT / "grafana/dashboards/agent_overview.json"
 ).write_text(json.dumps(dashboard, indent=2))

(ROOT / "grafana/provisioning/dashboards/dash.yaml"
 ).write_text("""\
apiVersion: 1
providers:
- name: Agentic Demo
  folder: Agentic Demo
  type: file
  options:
    path: /etc/grafana/dashboards
""")

print(f"✓ Grafana dashboard updated – {len(panels)} panels, version 10")
