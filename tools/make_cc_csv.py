#!/usr/bin/env python3
import sys, csv, itertools, pathlib, os, datasets, tqdm, warnings
N = int(sys.argv[1]) if len(sys.argv)>1 else 50000
OUT = pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "data/news_sample.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)
ds = datasets.load_dataset("cc_news", split="train", streaming=True)
with OUT.open("w", newline="", encoding="utf-8") as fp:
    w = csv.writer(fp); w.writerow(["id","title","text"])
    for ex in tqdm.tqdm(itertools.islice(ds,N), total=N, desc="Writing"):
        w.writerow([ex.get("id",""),
                    (ex.get("title") or "").replace("\n"," ").strip(),
                    (ex.get("text")  or "").replace("\n"," ").strip()])
print(f"✓ wrote {N:,} rows → {OUT}")
warnings.filterwarnings("ignore", message="resource_tracker")
os._exit(0)
