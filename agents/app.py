import os
import json
import time

from agents.utils import reltime
import random
import pathlib

import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    def st_autorefresh(*_a, **_k):
        pass
import redis

# Backward-compatible rerun helper
rerun = getattr(st, "rerun", getattr(st, "experimental_rerun"))

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
FEED_LEN   = int(os.getenv("FEED_LEN", "100"))
TOPICS = [
    "politics", "business", "technology", "sports", "health",
    "climate", "science", "education", "entertainment", "finance",
]

# ────────── Redis helpers ─────────────────────────────────────────
def rconn() -> redis.Redis:
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
    out = []
    for mid, fields in raw:
        if "data" in fields:
            try:
                doc = json.loads(fields["data"])
            except Exception:
                doc = {"title": fields["data"]}
        else:
            doc = fields
        doc.setdefault("id", mid)
        out.append(doc)
    return out

# ────────── Streamlit UI setup ────────────────────────────────────
st.set_page_config(page_title="Valkey Demo", layout="centered")

css_path = pathlib.Path("assets/style.css")
if css_path.exists():
    st.markdown(css_path.read_text(), unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .tag-int   {background:#ffeb3b;color:#000;border-radius:4px;padding:2px 6px;margin-right:4px}
    .tag-topic {background:#ffeb3b;color:#000;border-radius:4px;padding:2px 6px;margin-right:4px}
    </style>
    """,
    unsafe_allow_html=True,
)

r = rconn()
tab_user, tab_topic = st.tabs(["User", "Topic"])

# ────────── User tab ─────────────────────────────────────────────
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
        tags_html = " ".join(
            f"<span class='tag-int'><a href='?page=Topic&name={t}' target='_self'>{t}</a></span>"
            for t in interests
        )
        st.markdown(tags_html, unsafe_allow_html=True)
    else:
        st.write("No interests found")

    # ------------- Timeline -------------------------------------------------
    st.subheader("Timeline")
    if feed:
        st.markdown("<div style='max-height:400px;overflow-y:auto'>", unsafe_allow_html=True)
        for item in feed:
            title   = item.get("title", "")
            summary = item.get("summary")
            body    = item.get("body", "")
            tags    = item.get("tags") or ([item.get("topic")] if item.get("topic") else [])
            ts = reltime(item.get("id", ""))

            if not summary:
                summary = (body[:250] + "…") if body else ""

            # clickable tags
            tag_html = " ".join(
                f"<span class='tag-topic'><a href='?page=Topic&name={t}' target='_self'>{t}</a></span>"
                for t in tags
            )

            # card rendering
            with st.container():
                card  = (
                    "<div class='card'><details open>"
                    f"<summary><h4>{title}</h4></summary>"
                )
                if summary:
                    card += f"<p>{summary}</p>"
                if body:
                    card += f"<details><summary>Read more</summary>{body}</details>"
                card += f"<div class='tags'>{tag_html}</div>"
                if ts:
                    card += f"<small>{ts}</small>"
                card += "</details></div>"
                st.markdown(card, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No articles yet – try another uid or wait a bit…")

# ────────── Topic tab ────────────────────────────────────────────
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
            title   = item.get("title", "")
            summary = item.get("summary")
            body    = item.get("body", "")
            tags    = item.get("tags") or ([item.get("topic")] if item.get("topic") else [])
            ts = reltime(item.get("id", ""))

            if not summary:
                summary = (body[:250] + "…") if body else ""

            tag_html = " ".join(
                f"<span class='tag-topic'><a href='?page=Topic&name={t}' target='_self'>{t}</a></span>"
                for t in tags
            )

            with st.container():
                card = (
                    "<div class='card'><details open>"
                    f"<summary><h4>{title}</h4></summary>"
                )
                if summary:
                    card += f"<p>{summary}</p>"
                if body:
                    card += f"<details><summary>Read more</summary>{body}</details>"
                card += f"<div class='tags'>{tag_html}</div>"
                if ts:
                    card += f"<small>{ts}</small>"
                card += "</details></div>"
                st.markdown(card, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No items yet")

# auto-refresh every 5 seconds
st_autorefresh(interval=5000, key="refresh")
