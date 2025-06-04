FROM valkey/valkey:8.1-bookworm AS builder
ENV HF_HUB_DISABLE_XET=1
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential clang cmake git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone --recursive --depth 1 https://github.com/valkey-io/valkey-json.git /tmp/vj && \
    mkdir /tmp/vj/build && cd /tmp/vj/build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DVALKEY_VERSION=8.1 && \
    make -j$(nproc) valkey json && \
    cp $(find . -name libjson.so | head -n1) libjson.so && \
    strip libjson.so

FROM valkey/valkey:8.1-bookworm
COPY --from=builder /tmp/vj/build/libjson.so /opt/valkey/modules/valkeyjson.so
COPY redis.conf /etc/valkey/valkey.conf
CMD ["valkey-server","/etc/valkey/valkey.conf","--loadmodule","/opt/valkey/modules/valkeyjson.so"]
