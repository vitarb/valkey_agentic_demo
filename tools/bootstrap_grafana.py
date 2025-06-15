#!/usr/bin/env python3
"""Create (or overwrite) the compact Grafana dashboard & datasource.

 * fixes outdated Redis metric names
 * surfaces trim counters & GPU utilisation
 * adds CPU / mem / latency visibility for a convincing Valkey story
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
for sub in (
    "grafana/provisioning/datasources",
    "grafana/provisioning/dashboards",
    "grafana/dashboards",
):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────
#  Datasource
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
#  Helper
# ────────────────────────────────────────────────────

def panel(title, exprs, row, col, *, stack=False, unit=None):
    W, H = 12, 8
    x, y = col * W, row * H
    tgts = [{"expr": e, "refId": chr(65 + i)} for i, e in enumerate(exprs)]
    opts = {"legend": {"showLegend": stack}}
    if stack:
        opts["stacking"] = {"mode": "normal"}
    if unit:
        opts["standardOptions"] = {"unit": unit}
    return {
        "type": "timeseries",
        "title": title,
        "datasource": {"uid": "prom"},
        "targets": tgts,
        "gridPos": {"x": x, "y": y, "w": W, "h": H},
        "options": opts,
    }

# ────────────────────────────────────────────────────
#  Panels
# ────────────────────────────────────────────────────
panels = [
    panel("Producer msgs /\u202fs", ["sum(rate(producer_msgs_total[1m]))"], 0, 0),
    panel("news_raw backlog", ["news_raw_len"],                           0, 1, unit="none"),

    panel(
        "Enrich msgs /\u202fs",
        ["rate(enrich_in_total[1m])", "sum(rate(enrich_out_total[1m]))"],
        1,
        0,
    ),
    panel("Fan\u2011out backlog", ["sum(topic_stream_len)"], 1, 1, unit="none"),

    panel("Fan\u2011out msgs /\u202fs", ["sum(rate(fan_out_total[1m]))"], 2, 0),
    panel("Reader pops /\u202fs", ["rate(reader_pops_total[1m])"], 2, 1),

    panel("Feeds backlog", ["feed_backlog"],             3, 1),

    #  Valkey exporter metrics – names fixed (redis 1.x‑style)
    panel("Valkey ops /\u202fs", ["rate(redis_commands_processed_total[1m])"], 4, 0),
    panel("Valkey memory MB", ["redis_memory_used_bytes/1024/1024"],     4, 1, unit="bytes"),

    #  Latency (p99) – fixed histogram query
    panel(
        "Valkey p99\u202f\u00b5s",
        [
            "histogram_quantile(0.99, rate(redis_command_call_duration_seconds_bucket[2m])) * 1e6"
        ],
        5,
        0,
        unit="\u00b5s",
    ),

    #  GPU utilisation flag published by enrich services
    panel("Enrich replicas on GPU", ["sum(enrich_gpu)"], 5, 1, unit="none"),

    #  Stream trimming diagnostics
    panel("news_raw trim ops", ["irate(news_raw_trim_ops_total[5m])"], 6, 0),
    panel("topic trim ops",    ["irate(topic_stream_trim_ops_total[5m])"], 6, 1),
]

dashboard = {
    "uid": "agent-overview",
    "title": "Agent Overview",
    "schemaVersion": 38,
    "version": 4,
    "refresh": "5s",
    "panels": panels,
}
(ROOT / "grafana/dashboards/agent_overview.json").write_text(
    json.dumps(dashboard, indent=2)
)

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

print("\u2713 Grafana provisioning updated")
