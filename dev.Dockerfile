ARG ORG
FROM ghcr.io/${ORG}/vomu-tools:${{ github.date }}
ENV PATH=/usr/local/.tools/bin:$PATH
WORKDIR /app
COPY . /app
