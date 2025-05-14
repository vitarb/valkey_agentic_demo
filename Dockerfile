FROM python:3.12-slim
ENV HF_HUB_DISABLE_XET=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agents ./agents
COPY fanout.lua ./fanout.lua
CMD ["python","-m","pip","--version"]
