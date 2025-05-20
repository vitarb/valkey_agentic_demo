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
