FROM python:3.12-slim
ENV HF_HUB_DISABLE_XET=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG USE_CUDA=0
RUN if [ "$USE_CUDA" = "1" ]; then \
        pip install --no-cache-dir torch==2.2.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html ; \
    else \
        pip install --no-cache-dir torch==2.2.1 ; \
    fi
COPY agents ./agents
COPY fanout.lua ./fanout.lua
CMD ["python","-m","pip","--version"]
