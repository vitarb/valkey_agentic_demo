import argparse
import os
import subprocess
from pathlib import Path
from valkey_agentic_demo import boto3shim as boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", default="instance_id.txt")
    parser.add_argument("--sg-file", default="sg_id.txt")
    parser.add_argument("--subnet-file", default="subnet_id.txt")
    parser.add_argument("--eni-file", default="eni_id.txt")
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
    sg_id = Path(args.sg_file).read_text().strip()
    subnet_id = Path(args.subnet_file).read_text().strip()
    eni_path = Path(args.eni_file)
    eni_id = eni_path.read_text().strip() if eni_path.exists() else None

    ec2 = boto3.client(
        "ec2",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION"),
    )
    ec2.terminate_instances(InstanceIds=[iid])
    if eni_id and hasattr(ec2, "delete_network_interface"):
        ec2.delete_network_interface(NetworkInterfaceId=eni_id)
    ec2.delete_security_group(GroupId=sg_id)
    if hasattr(ec2, "delete_subnet"):
        ec2.delete_subnet(SubnetId=subnet_id)
    print(iid)


if __name__ == "__main__":
    main()
