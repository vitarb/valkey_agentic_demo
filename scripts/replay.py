"""Replay a CSV of articles into the `news_raw` stream at a given rate."""
import csv
import asyncio
import argparse
import time
import os
import redis.asyncio as redis

async def pump(rows, rate):
    r = redis.Redis(host=os.getenv("VALKEY_HOST", "localhost"), decode_responses=True)
    interval = 1.0 / rate
    for row in rows:
        start = time.perf_counter()
        await r.xadd("news_raw", row, id="*")
        await asyncio.sleep(max(0, interval - (time.perf_counter() - start)))

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="CSV file containing articles with a 'title' column")
    parser.add_argument("--rate", type=int, default=1000)
    args = parser.parse_args()
    with open(args.csv) as fh:
        rows = [dict(rec) for rec in csv.DictReader(fh)]
    await pump(rows, args.rate)

if __name__ == "__main__":
    asyncio.run(main())
