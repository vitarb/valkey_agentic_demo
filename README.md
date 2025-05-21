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
  /bin/bash -c "make MOCK=1 ec2-up && sleep 5 && make MOCK=1 ec2-down && pytest -q"
```

If you'd rather run the helper scripts on your host with LocalStack, start it
first and export the environment variables that the scripts expect:

```bash
localstack start -d
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_REGION=us-west-2
make MOCK=1 ec2-up
```
The helper defaults to a GPU-enabled AMI so you can simply run `make ec2-up`
against AWS. Pass `--image-id` to override if needed.

`make ec2-up` automatically creates a key-pair `demo-key`, a subnet, a network
interface and a security group `valkey-demo-sg` if they don't already exist.
The resulting resource IDs are written to `instance_id.txt`, `sg_id.txt`,
`subnet_id.txt` and `eni_id.txt`.

To use the helper scripts with real AWS, install the `boto3` package and run:

```bash
pip install boto3
make ec2-up
```
