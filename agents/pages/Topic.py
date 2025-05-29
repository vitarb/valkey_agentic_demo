import os
import json
import time

import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover - fallback for tests without dependency
    def st_autorefresh(*a, **k):
        pass
import redis
import pathlib

rerun = getattr(st, "rerun", getattr(st, "experimental_rerun"))

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
FEED_LEN = int(os.getenv("FEED_LEN", "100"))
TOPICS = [
    "politics", "business", "technology", "sports", "health",
    "climate", "science", "education", "entertainment", "finance",
]


def rconn():
    while True:
        try:
            r = redis.from_url(VALKEY_URL, decode_responses=True)
            r.ping()
            return r
        except Exception:
            time.sleep(1)


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

st.set_page_config(page_title="Topic Timeline", layout="centered")

st.markdown(pathlib.Path("assets/style.css").read_text(), unsafe_allow_html=True)

sidebar = getattr(st, "sidebar", st)
slider = getattr(sidebar, "slider", None)
interval = slider("Refresh (sec)", 1, 15, 5) if slider else 5
st_autorefresh(interval * 1000, key="auto_refresh")

r = rconn()

# --- query-string helper -------------------------------------------------
try:
    qp = st.query_params            # Streamlit ≥1.32
    get_q = lambda k, d: qp.get(k, d)
    set_q = lambda **kw: qp.update(kw)
except AttributeError:
    qp = st.experimental_get_query_params()   # fallback
    get_q = lambda k, d: qp.get(k, d)[0] if k in qp else d
    set_q = lambda **kw: st.experimental_set_query_params(**kw)

slug = get_q("name", TOPICS[0])

changed = st.selectbox("Topic", TOPICS, index=TOPICS.index(slug), key="topic_sel")
if changed != slug:
    set_q(name=changed)
    st.rerun()

st.markdown("[Back to user view](/)")

items = topic_data(r, slug)

st.subheader(f"{slug} stream")
if items:
    st.markdown("<div style='max-height:400px;overflow-y:auto'>", unsafe_allow_html=True)
    for item in items:
        title = item.get("title", "")
        summary = item.get("summary") or (item.get("body", "")[:300] + "…")
        body = item.get("body", "")
        tags = item.get("tags") or ([item.get("topic")] if item.get("topic") else [])
        ts = item.get("id", "")

        tag_html = " ".join(f"<span>{t}</span>" for t in tags)

        with st.container():
            card = f"<div class='card'><h4>{title}</h4><p>{summary}</p>"
            if body:
                card += f"<details><summary>Read more</summary>{body}</details>"
            card += f"<div class='tags'>{tag_html}</div></div>"
            st.markdown(card, unsafe_allow_html=True)
            if ts:
                st.markdown(ts)
            st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No items yet")
