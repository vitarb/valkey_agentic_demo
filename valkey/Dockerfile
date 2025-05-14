FROM valkey/valkey:8.1-bookworm
ENV HF_HUB_DISABLE_XET=1
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends build-essential clang cmake git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone --recursive --depth 1 https://github.com/valkey-io/valkey-json.git /tmp/vj && \
    mkdir /tmp/vj/build && cd /tmp/vj/build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DVALKEY_VERSION=8.1 && \
    make -j$(nproc) valkey json && \
    mkdir -p /opt/valkey/modules && \
    cp $(find . -name libjson.so | head -n1) /opt/valkey/modules/valkeyjson.so && \
    strip /opt/valkey/modules/valkeyjson.so && rm -rf /tmp/vj
CMD ["valkey-server","--loadmodule","/opt/valkey/modules/valkeyjson.so"]
