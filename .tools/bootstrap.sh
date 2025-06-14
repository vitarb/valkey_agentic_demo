#!/usr/bin/env bash
set -euo pipefail

command -v mockgen >/dev/null || go install github.com/golang/mock/mockgen@v1.6.0
