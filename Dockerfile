# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS DEPS
ENV HF_HOME=/opt/hf_cache \
    HF_HUB_DISABLE_XET=1
WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

ARG USE_CUDA=0
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$USE_CUDA" = "1" ]; then \
        pip install torch==2.2.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html ; \
    else \
        pip install torch==2.2.1 ; \
    fi

# Pre-download HF models
RUN --mount=type=cache,target=/opt/hf_cache \
    python - <<'PY'
from transformers import pipeline
pipeline('zero-shot-classification', model='typeform/distilbert-base-uncased-mnli')
PY

FROM python:3.12-slim
ENV HF_HOME=/opt/hf_cache \
    HF_HUB_DISABLE_XET=1
WORKDIR /app

COPY --from=DEPS /usr/local /usr/local
COPY agents ./agents
COPY fanout.lua ./fanout.lua
CMD ["python","-m","pip","--version"]
