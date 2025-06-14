# Contributing

## How the cache works

The CI builds use BuildKit layer caching via GitHub Actions. Layers are stored under the `dev-img` scope so repeated runs can reuse them. When the Dockerfile or dependencies change, the cache automatically invalidates and the image rebuilds. Otherwise, jobs start much faster because the cached layers are restored.

To run the development container with your local tool cache mounted:

```bash
docker run --rm --platform=linux/amd64 \
  -v "$PWD/.tools:/usr/local/.tools:ro" \
  -e PATH=/usr/local/.tools/bin:$PATH \
  vomu-dev-amd64 task ci:core
```
