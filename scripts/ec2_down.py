import argparse
import os
from pathlib import Path
import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", default="instance_id.txt")
    args = parser.parse_args()

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
