import os
import json
import time

import streamlit as st
import redis

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
params = st.experimental_get_query_params()
def_topic = TOPICS[0]
slug = params.get("name", [def_topic])[0]
idx = TOPICS.index(slug) if slug in TOPICS else 0
selection = st.selectbox("Topic", TOPICS, index=idx)
if selection != slug:
    st.experimental_set_query_params(name=selection)
    rerun()

st.markdown("[Back to user view](/)")

items = topic_data(r, selection)

st.subheader(f"{selection} stream")
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
