# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder
ENV HF_HOME=/opt/hf_cache \
    HF_HUB_DISABLE_XET=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
ENV PYTHONPATH=/install/lib/python3.12/site-packages

ARG USE_CUDA=0
RUN if [ "$USE_CUDA" = "1" ]; then \
        pip install --no-cache-dir --prefix=/install torch==2.2.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html ; \
    else \
        pip install --no-cache-dir --prefix=/install torch==2.2.1 ; \
    fi

# Pre-download HF models
RUN python - <<'PY'
from transformers import pipeline
pipeline('zero-shot-classification', model='typeform/distilbert-base-uncased-mnli')
PY

FROM python:3.12-slim
ENV HF_HOME=/opt/hf_cache \
    HF_HUB_DISABLE_XET=1
WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /opt/hf_cache /opt/hf_cache
COPY agents ./agents
COPY fanout.lua ./fanout.lua
CMD ["python","-m","pip","--version"]
