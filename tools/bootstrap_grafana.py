#!/usr/bin/env python3
"""Create compact Grafana dashboard & datasource (Python ≤3.7 compatible)."""
import json, yaml, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
for sub in ("grafana/provisioning/datasources",
            "grafana/provisioning/dashboards",
            "grafana/dashboards"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

# datasource ------------------------------------------------------
(ROOT/"grafana/provisioning/datasources/prom.yaml").write_text(yaml.dump({
    "apiVersion": 1,
    "datasources": [{
        "uid": "prom",
        "name": "Prometheus",
        "type": "prometheus",
        "url": "http://prometheus:9090",
        "isDefault": False
    }]
}, sort_keys=False))

# helper ----------------------------------------------------------
def panel(title, exprs, row, col):
    w, h = 12, 8
    x = col * w
    y = row * h
    tgts = [{"expr": e, "refId": chr(65+i)} for i, e in enumerate(exprs)]
    return {
        "type": "timeseries",
        "title": title,
        "datasource": {"uid": "prom"},
        "targets": tgts,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "options": {"legend": {"showLegend": False}}
    }

panels = [
    panel("Producer msgs / s", ["rate(producer_msgs_total[1m])"], 0, 0),
    panel("news_raw backlog", ["news_raw_len"], 0, 1),
    panel("Enrich msgs / s",
          ["rate(enrich_in_total[1m])", "rate(enrich_out_total[1m])"], 1, 0),
    panel("Fan-out backlog", ["topic_stream_len"], 1, 1),
    panel("Fan-out msgs / s", ["rate(fan_out_total[1m])"], 2, 0),
    panel("Reader pops / s", ["rate(reader_pops_total[1m])"], 2, 1),
    panel("Classifier p95 s",
          ["histogram_quantile(0.95, rate(classifier_latency_seconds_bucket[2m]))"], 3, 0),
    panel("Summariser p95 s",
          ["histogram_quantile(0.95, rate(summariser_latency_seconds_bucket[2m]))"], 3, 1),
    panel("Valkey ops / s", ["rate(redis_commands_processed_total[1m])"], 4, 0),
    panel("Valkey mem MB", ["redis_memory_used_bytes/1024/1024"], 4, 1),
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

(ROOT/"grafana/provisioning/dashboards/dash.yaml").write_text(yaml.dump({
    "apiVersion": 1,
    "providers": [{
        "name": "Agentic Demo",
        "folder": "Agentic Demo",
        "type": "file",
        "options": {"path": "/etc/grafana/dashboards"}
    }]
}, sort_keys=False))

print("✓ Grafana provisioning + dashboard written")

