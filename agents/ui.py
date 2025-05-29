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
st.sidebar.page_link("agents/ui.py", label="📰 User feed")
st.sidebar.page_link("agents/pages/Topic.py", label="🏷️ Topic stream")
st.markdown(
    """
    <style>
    .tag-int {background:#ffeb3b;color:#000;border-radius:4px;padding:2px 6px;margin-right:4px}
    .tag-topic {background:#ffeb3b;color:#000;border-radius:4px;padding:2px 6px;margin-right:4px}
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
    def _set_random_uid(lu=lu):
        st.session_state["uid"] = random.randint(0, lu)
    st.button("Random user", on_click=_set_random_uid)

interests, feed = user_data(r, uid)

st.subheader("Interests")
if interests:
    tags = " ".join(
        f"<span class='tag-int'><a href='?page=Topic&name={t}' target='_self'>{t}</a></span>"
        for t in interests
    )
    st.markdown(tags, unsafe_allow_html=True)
else:
    st.write("No interests found")

st.subheader("Timeline")
if feed:
    st.markdown("<div style='max-height:400px;overflow-y:auto'>", unsafe_allow_html=True)
    for item in feed:
        title = item.get("title", "")
        summary = item.get("summary", "")
        body = item.get("body", "")
        tags = item.get("tags") or ([item.get("topic")] if item.get("topic") else [])
        ts = item.get("id", "")

        title_line = f"**{title}**"
        with st.expander(title_line):
            st.markdown(body)

        tag_html = " ".join(f"<span class='tag-topic'>{t}</span>" for t in tags)
        st.markdown(tag_html, unsafe_allow_html=True)
        if summary:
            st.markdown(summary)
        if ts:
            st.markdown(ts)
        st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No articles yet – try another uid or wait a bit…")

if refresh:
    rerun()
else:
    time.sleep(5)
    rerun()
