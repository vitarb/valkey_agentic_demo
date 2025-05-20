# Valkey Agentic Demo 🚀

Scaffolding generated **2025-05-08T20:34:10Z**.

```bash
# spin everything up
make dev
```

## Local EC2 Dev/Test

Build the container and run the EC2 helper scripts against LocalStack:

```bash
docker build -t valkey-demo .
docker run --rm valkey-demo \
  /bin/bash -c "make ec2-up && sleep 5 && make ec2-down && pytest -q"
```

If you'd rather run the helper scripts on your host with LocalStack, start it
first and export the environment variables that the scripts expect:

```bash
localstack start -d
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_REGION=us-east-1
make ec2-up
```

When running `make ec2-up` directly against AWS, specify a valid AMI ID:

```bash
make ec2-up ARGS="--image-id ami-xxxxxxxxxxxx"
```
