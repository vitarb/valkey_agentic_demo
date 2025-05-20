#!/bin/bash
set -e
localstack start -d
until awslocal sts get-caller-identity >/dev/null 2>&1; do
  sleep 1
done
exec "$@"

