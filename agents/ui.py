import os
import json
import random
import pathlib
import time
import sys
from html import escape

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.utils import reltime

import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover – tests may miss optional extra
    def st_autorefresh(*_a, **_k):
        pass

import redis

# ---------------------------------------------------------------------------

VALKEY_URL = os.getenv("VALKEY_URL", "redis://valkey:6379")
FEED_LEN   = int(os.getenv("FEED_LEN", "100"))

# ---------------------------------------------------------------------------
# Redis helpers
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

def latest_uid(r: redis.Redis) -> int:
    val = r.get("latest_uid")
    return int(val) if val is not None else 0

def user_data(r: redis.Redis, uid: int):
    pipe = r.pipeline()
    pipe.json().get(f"user:{uid}")
    pipe.lrange(f"feed:{uid}", 0, FEED_LEN - 1)
    user_json, feed_raw = pipe.execute()

    interests = (
        user_json.get("interests", []) if isinstance(user_json, dict) else []
    )
    items = []
    for raw in feed_raw:
        try:
            items.append(json.loads(raw))
        except Exception:
            items.append({"summary": raw})
    return interests, items

# ---------------------------------------------------------------------------
#                                Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="User Timeline", layout="centered")

# shared CSS (cards, tags)
css_path = pathlib.Path("assets/style.css")
if css_path.exists():
    st.markdown(css_path.read_text(), unsafe_allow_html=True)

# refresh setup --------------------------------------------------------------
# ---------------------------------------------------------------------------
r   = rconn()
lu  = latest_uid(r)
if lu == 0:
    st.warning("Seeder not running…")

if "uid" not in st.session_state:
    st.session_state.uid = lu or 0

# input/refresh controls ----------------------------------------------------
cols = st.columns(4)

uid = cols[0].number_input("User ID", key="uid", step=1, min_value=0)

def _set_random_uid():
    st.session_state.uid = random.randint(0, lu) if lu else 0

if lu:
    cols[1].button("Random user", on_click=_set_random_uid)
else:
    cols[1].markdown("&nbsp;")

cols[2].button("Refresh", on_click=st.rerun)
interval = cols[3].slider("Refresh (sec)", 1, 15, 5)
st_autorefresh(interval * 1000, key="auto_refresh")

# ---------------------------------------------------------------------------
interests, feed = user_data(r, uid)

st.subheader("Interests")
if interests:
    tag_html = " ".join(
        f"<span><a href='?page=Topic&name={t}' target='_self'>{t}</a></span>"
        for t in interests
    )
    st.markdown(f"<div class='tags'>{tag_html}</div>", unsafe_allow_html=True)
else:
    st.info("No interests found")

# ---------------------------------------------------------------------------
st.subheader("Timeline")
if feed:
    st.markdown(
        "<div style='max-height:400px;overflow-y:auto'>",
        unsafe_allow_html=True
    )
    for itm in feed:
        title   = itm.get("title", "")
        summary = itm.get("summary")
        body    = itm.get("body", "")
        tags    = itm.get("tags") or ([itm.get("topic")] if itm.get("topic") else [])
        if not summary:
            summary = (body[:250] + "…") if body else ""

        ts = reltime(itm.get("id", ""))
        tag_html = " ".join(
            f"<span class='tag-topic'><a href='?page=Topic&name={t}' target='_self'>{t}</a></span>"
            for t in tags
        )

        row_id = f"row_{itm['id'].translate(str.maketrans({'-':'','.' :''}))}"
        html = (
            f"<input type='checkbox' id='{row_id}' hidden>"
            f"<label for='{row_id}' class='row'>"
                f"<div class='row-l'><h4>{escape(title)}</h4><p>{escape(summary)}</p></div>"
                f"<div class='row-r'>{tag_html}<br><small>{ts}</small></div>"
            f"</label>"
            f"<div class='row-body' style='display:none' markdown='1'>{body}</div>"
        )
        st.markdown(html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No articles yet – try another UID or wait a bit…")
