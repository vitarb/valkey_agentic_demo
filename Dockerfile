FROM python:3.12-slim

ENV AWS_REGION=us-west-2

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -e . \
    boto3 localstack localstack-client pytest pytest-localstack

COPY docker-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["bash"]
