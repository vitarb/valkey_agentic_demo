#!/bin/bash
set -e
if [ "${USE_MOCK_BOTO3}" = "1" ]; then
  localstack start -d
  until awslocal sts get-caller-identity >/dev/null 2>&1; do
    sleep 1
  done
fi
exec "$@"

