import os, asyncio, time, json, random, warnings
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnError
from prometheus_client import Counter, start_http_server

VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379")

async def rconn(retries=30, delay=1.0):
    "Retry until Valkey answers PING."
    for _ in range(retries):
        try:
            r = await redis.from_url(VALKEY_URL, decode_responses=True)
            await r.ping()
            return r
        except Exception as e:
            print("[common] Valkey not ready:", e)
            await asyncio.sleep(delay)
    raise RuntimeError("Valkey never became available")

TOPICS = ["politics", "business", "technology", "sports", "health", "climate", "science", "education", "entertainment", "finance"]
RATE = float(os.getenv("SEED_RATE","0.5"))
USERS = Counter("seed_users_total","")

async def main():
    start_http_server(9113)
    r   = await rconn()
    uid   = 0
    total = 0
    while True:
        try:
            ints = random.sample(TOPICS, k=random.randint(2,4))
            await r.json().set(f"user:{uid}","$",{"interests":ints})
            for t in ints: await r.zadd(f"user:topic:{t}",{uid:1})
            await r.set("latest_uid", uid)
            USERS.inc(); uid += 1
            total += 1
            if total % 100 == 0:
                print(f"[+] {total} users seeded (latest uid = {uid-1})")
            await asyncio.sleep(1 / RATE)
        except RedisConnError as e:
            print("[seeder] reconnect:", e); r = await rconn()

if __name__=="__main__": asyncio.run(main())
