import os
import json
import time
import random

import streamlit as st
import redis

# Backward-compatible rerun function
rerun = getattr(st, "rerun", getattr(st, "experimental_rerun"))

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
FEED_LEN = int(os.getenv("FEED_LEN", "100"))

def rconn():
    """Return a connected Redis client."""
    while True:
        try:
            r = redis.from_url(VALKEY_URL, decode_responses=True)
            r.ping()
            return r
        except Exception:
            time.sleep(1)

def latest_uid(r: redis.Redis) -> int:
    val = r.get("latest_uid")
    return int(val) if val is not None else 0

def user_data(r: redis.Redis, uid: int):
    pipe = r.pipeline()
    pipe.json().get(f"user:{uid}")
    pipe.lrange(f"feed:{uid}", 0, FEED_LEN - 1)
    user_json, feed_raw = pipe.execute()
    interests = user_json.get("interests", []) if isinstance(user_json, dict) else []
    items = []
    for raw in feed_raw:
        try:
            items.append(json.loads(raw))
        except Exception:
            items.append({"summary": raw})
    return interests, items

# ------------------------ Streamlit UI -------------------------------------

st.set_page_config(page_title="User Timeline", layout="centered")
st.markdown(
    """
    <style>
    .tag-int {background:#ffeb3b;color:#000;border-radius:4px;padding:2px 6px;margin-right:4px}
    .tag-topic {background:#eee;border-radius:4px;padding:2px 6px;margin-right:4px}
    </style>
    """,
    unsafe_allow_html=True,
)

r = rconn()
lu = latest_uid(r)
if lu == 0:
    st.warning("Seeder not running…")
if "uid" not in st.session_state:
    st.session_state.uid = lu or 0
uid = st.number_input("User ID", key="uid", step=1, min_value=0)

refresh = st.button("Refresh")
if lu > 0:
    random_btn = st.button("Random user")
    if random_btn:
        st.session_state.uid = random.randint(0, lu)
        rerun()

interests, feed = user_data(r, uid)

st.subheader("Interests")
if interests:
    tags = " ".join(
        f"<span class='tag-int'>[{t}](?page=Topic&name={t})</span>" for t in interests
    )
    st.markdown(tags, unsafe_allow_html=True)
else:
    st.write("No interests found")

st.subheader("Timeline")
if feed:
    st.markdown("<div style='max-height:400px;overflow-y:auto'>", unsafe_allow_html=True)
    for item in feed:
        text = item.get("summary") or item.get("title") or str(item)
        topic = item.get("topic", "")
        ts = item.get("id", "")
        st.markdown(
            f"**{text}**\n\n"
            f"<span class='tag-topic'>{topic}</span> {ts}",
            unsafe_allow_html=True,
        )
        st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No articles yet – try another uid or wait a bit…")

if refresh:
    rerun()
else:
    time.sleep(5)
    rerun()
