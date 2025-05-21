import argparse
import os
import subprocess
from pathlib import Path
from valkey_agentic_demo import boto3shim as boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", default="instance_id.txt")
    args = parser.parse_args()

    if not os.getenv("USE_MOCK_BOTO3"):
        try:
            subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            print("aws CLI not found")
            raise
        except subprocess.CalledProcessError as e:
            print(f"aws CLI failed: {e.stderr.decode().strip()}")
            raise

    iid = Path(args.infile).read_text().strip()

    ec2 = boto3.client(
        "ec2",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION"),
    )
    ec2.terminate_instances(InstanceIds=[iid])
    print(iid)


if __name__ == "__main__":
    main()
