#!/usr/bin/env python3
"""Generate a small CSV corpus for local testing.

This script originally relied on the HuggingFace ``datasets`` library to
stream the ``cc_news`` dataset.  That dependency can be problematic on
systems without network access or with an older OpenSSL build.  To keep the
demo self contained, the script now falls back to generating a tiny synthetic
dataset when ``datasets`` cannot be imported.
"""

import csv
import itertools
import os
import pathlib
import random
import sys
import warnings

try:  # optional dependency
    import datasets
    import tqdm
except Exception:  # pragma: no cover - handled at runtime
    datasets = None
    tqdm = None

N = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
OUT = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "data/news_sample.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)


def iter_rows():
    """Yield news examples either from ``cc_news`` or synthetic data."""

    if datasets is None:
        titles = ["Breaking News", "Local Update", "Global Report"]
        texts = [
            "Lorem ipsum dolor sit amet.",
            "Consectetur adipiscing elit.",
            "Sed do eiusmod tempor incididunt ut labore.",
        ]
        for i in range(N):
            yield {
                "id": i,
                "title": random.choice(titles),
                "text": random.choice(texts),
            }
    else:
        ds = datasets.load_dataset("cc_news", split="train", streaming=True)
        for ex in itertools.islice(ds, N):
            yield {
                "id": ex.get("id", ""),
                "title": (ex.get("title") or "").replace("\n", " ").strip(),
                "text": (ex.get("text") or "").replace("\n", " ").strip(),
            }


rows = iter_rows()
with OUT.open("w", newline="", encoding="utf-8") as fp:
    writer = csv.writer(fp)
    writer.writerow(["id", "title", "text"])
    if tqdm is not None:
        rows = tqdm.tqdm(rows, total=N, desc="Writing")
    for i, ex in enumerate(rows):
        if i >= N:
            break
        writer.writerow([ex["id"], ex["title"], ex["text"]])

print(f"✓ wrote {N:,} rows → {OUT}")
warnings.filterwarnings("ignore", message="resource_tracker")
os._exit(0)
