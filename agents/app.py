import os
import json
import time
import random
import pathlib

import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    def st_autorefresh(*_a, **_k):
        pass
import redis

# Backward-compatible rerun function
rerun = getattr(st, "rerun", getattr(st, "experimental_rerun"))

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
FEED_LEN = int(os.getenv("FEED_LEN", "100"))
TOPICS = [
    "politics", "business", "technology", "sports", "health",
    "climate", "science", "education", "entertainment", "finance",
]


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


def topic_data(r: redis.Redis, slug: str):
    raw = r.xrevrange(f"topic:{slug}", count=FEED_LEN)
    items = []
    for mid, fields in raw:
        if "data" in fields:
            try:
                item = json.loads(fields["data"])
            except Exception:
                item = {"title": fields["data"]}
        else:
            item = fields
        item.setdefault("id", mid)
        items.append(item)
    return items


# ------------------------ Streamlit UI -------------------------------------

st.set_page_config(page_title="Valkey Demo", layout="centered")

css_path = pathlib.Path("assets/style.css")
if css_path.exists():
    st.markdown(css_path.read_text(), unsafe_allow_html=True)

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
tab_user, tab_topic = st.tabs(["User", "Topic"])

with tab_user:
    lu = latest_uid(r)
    if lu == 0:
        st.warning("Seeder not running…")
    if "uid" not in st.session_state:
        st.session_state.uid = lu or 0
    uid = st.number_input("User ID", key="uid", step=1, min_value=0)

    if lu > 0:
        def _set_random_uid(lu=lu):
            st.session_state["uid"] = random.randint(0, lu)
        st.button("Random user", on_click=_set_random_uid)
    st.button("Refresh", on_click=st.rerun)

    interests, feed = user_data(r, uid)

    st.subheader("Interests")
    if interests:
        tags = " ".join(
            f"<span class='tag-int'>{t}</span>" for t in interests
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

with tab_topic:
    if "topic" not in st.session_state:
        st.session_state.topic = TOPICS[0]
    slug = st.selectbox("Topic", TOPICS, index=TOPICS.index(st.session_state.topic), key="topic_sel")
    if slug != st.session_state.topic:
        st.session_state.topic = slug
        rerun()

    items = topic_data(r, st.session_state.topic)

    st.subheader(f"{st.session_state.topic} stream")
    if items:
        st.markdown("<div style='max-height:400px;overflow-y:auto'>", unsafe_allow_html=True)
        for item in items:
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
        st.info("No items yet")

# auto refresh every 5 seconds
st_autorefresh(interval=5000, key="refresh")
