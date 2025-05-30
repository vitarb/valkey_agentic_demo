#!/usr/bin/env python3
"""Create compact Grafana dashboard & datasource (Python ≤3.7 compatible)."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
for sub in (
    "grafana/provisioning/datasources",
    "grafana/provisioning/dashboards",
    "grafana/dashboards",
):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

# datasource ------------------------------------------------------
DATA_SRC = (
    "apiVersion: 1\n"
    "datasources:\n"
    "- uid: prom\n"
    "  name: Prometheus\n"
    "  type: prometheus\n"
    "  url: http://prometheus:9090\n"
    "  isDefault: false\n"
)
(ROOT / "grafana/provisioning/datasources/prom.yaml").write_text(DATA_SRC)

# helper ----------------------------------------------------------
def panel(title, exprs, row, col, stack=False):
    w, h = 12, 8
    x = col * w
    y = row * h
    tgts = [{"expr": e, "refId": chr(65+i)} for i, e in enumerate(exprs)]
    opts = {"legend": {"showLegend": stack}}
    if stack:
        opts["stacking"] = {"mode": "normal"}
    return {
        "type": "timeseries",
        "title": title,
        "datasource": {"uid": "prom"},
        "targets": tgts,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": opts,
    }

panels = [
    panel("Producer msgs / s", ["sum(rate(producer_msgs_total[1m]))"], 0, 0),
    panel("news_raw backlog", ["news_raw_len"], 0, 1),
    panel(
        "Enrich msgs / s",
        ["rate(enrich_in_total[1m])", "sum(rate(enrich_out_total[1m]))"],
        1,
        0,
    ),
    panel("Fan-out backlog", ["topic_stream_len"], 1, 1),
    panel("Fan-out msgs / s", ["sum(rate(fan_out_total[1m]))"], 2, 0),
    panel("Reader pops / s", ["rate(reader_pops_total[1m])"], 2, 1),
    panel(
        "Summariser p95 s",
        ["histogram_quantile(0.95, rate(summariser_latency_seconds_bucket[2m]))"],
        3,
        0,
    ),
    panel("Feeds backlog", ["feed_backlog"], 3, 1),
    panel("Valkey ops / s", ["rate(redis_commands_processed_total[1m])"], 4, 0),
    panel("Valkey mem MB", ["redis_memory_used_bytes/1024/1024"], 4, 1),
    panel("Replay topic msgs / s", ["rate(producer_msgs_total[1m])"], 5, 0, stack=True),
    panel("Enrich out by topic / s", ["rate(enrich_out_total[1m])"], 5, 1, stack=True),
    panel("Fan-out by topic / s", ["rate(fan_out_total[1m])"], 6, 0, stack=True),
    panel(
        "Valkey p95 us",
        ["histogram_quantile(0.95, rate(redis_command_call_duration_seconds_bucket[2m]))"],
        6,
        1,
    ),
    panel(
        "Valkey p99 us",
        ["histogram_quantile(0.99, rate(redis_command_call_duration_seconds_bucket[2m]))"],
        7,
        0,
    ),
]

dashboard = {
    "uid": "agent-overview",
    "title": "Agent Overview",
    "schemaVersion": 38,
    "version": 3,
    "refresh": "5s",
    "panels": panels
}
(ROOT/"grafana/dashboards/agent_overview.json").write_text(json.dumps(dashboard, indent=2))

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

print("✓ Grafana provisioning + dashboard written")

