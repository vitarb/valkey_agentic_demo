import os
import json
import time
import pathlib
import datetime

import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover – keep tests happy if extra not installed
    def st_autorefresh(*_a, **_k):
        pass

import redis

# ---------------------------------------------------------------------------

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
FEED_LEN   = int(os.getenv("FEED_LEN", "100"))
TOPICS = [
    "politics", "business", "technology", "sports", "health",
    "climate", "science", "education", "entertainment", "finance",
]

# ---------------------------------------------------------------------------
def rconn() -> redis.Redis:
    """Block-until-ready Redis connection."""
    while True:
        try:
            r = redis.from_url(VALKEY_URL, decode_responses=True)
            r.ping()
            return r
        except Exception:
            time.sleep(1)

def topic_data(r: redis.Redis, slug: str):
    """Return latest items for *slug* topic."""
    raw = r.xrevrange(f"topic:{slug}", count=FEED_LEN)
    out = []
    for mid, fields in raw:
        # payload is JSON-encoded under "data"
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

# ---------------------------------------------------------------------------
#                                Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Topic Timeline", layout="centered")

# load shared CSS if present
css_path = pathlib.Path("assets/style.css")
if css_path.exists():
    st.markdown(css_path.read_text(), unsafe_allow_html=True)

# refresh slider ------------------------------------------------------------

r = rconn()

# --- query-string helpers ---------------------------------------------------
try:                                    # Streamlit ≥1.32
    qp = st.query_params
    get_q = lambda k, d: qp.get(k, d)
    set_q = lambda **kw: qp.update(kw)
except AttributeError:                  # older fallback
    qp = st.experimental_get_query_params()
    get_q = lambda k, d: qp.get(k, d)[0] if k in qp else d
    set_q = lambda **kw: st.experimental_set_query_params(**kw)

slug = get_q("name", TOPICS[0])

# topic selector and refresh slider ----------------------------------------
if hasattr(st, "columns"):
    col_sel, col_slide = st.columns([3, 1])
else:
    col_sel = col_slide = st

changed = col_sel.selectbox(
    "Topic", TOPICS, index=TOPICS.index(slug), key="topic_sel"
)
slider = getattr(col_slide, "slider", None)
interval = slider("Refresh (sec)", 1, 15, 5) if slider else 5
st_autorefresh(interval * 1000, key="auto_refresh")

if changed != slug:
    set_q(name=changed)
    st.rerun()

st.markdown("[Back to user view](/)")

items = topic_data(r, slug)

# ---------------------------------------------------------------------------
st.subheader(f"{slug} stream")

if items:
    st.markdown(
        "<div style='max-height:400px;overflow-y:auto'>",
        unsafe_allow_html=True
    )
    for itm in items:
        title   = itm.get("title", "")
        summary = itm.get("summary")
        body    = itm.get("body", "")
        tags    = itm.get("tags") or ([itm.get("topic")] if itm.get("topic") else [])
        ts_raw  = itm.get("id")
        ts = ""
        if ts_raw:
            try:
                ts_part = ts_raw.split("-")[0]
                ts_dt = datetime.datetime.utcfromtimestamp(int(ts_part) / 1000)
                ts = ts_dt.isoformat() + "Z"
            except Exception:
                ts = ""

        if not summary:
            summary = (body[:250] + "…") if body else ""

        tag_html = " ".join(
            f"<span><a href='?page=Topic&name={t}' target='_self'>{t}</a></span>"
            for t in tags
        )

        # ---------- card rendering -----------------------------------------
        with st.container():
            card  = f"<div class='card'><h4>{title}</h4>"
            if summary:
                card += f"<p>{summary}</p>"
            if body:
                card += f"<details><summary>Read more</summary>{body}</details>"
            card += f"<div class='tags'>{tag_html}</div>"
            if ts:
                card += f"<small>{ts}</small>"
            card += "</div>"
            st.markdown(card, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No items yet")
