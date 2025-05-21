import argparse
import os
import subprocess
import time
from valkey_agentic_demo import boto3shim as boto3
from valkey_agentic_demo.launcher.aws_helpers import ensure_key, ensure_sg


DEFAULT_AMI = "ami-0f5c0fd7df464c253"  # Deep Learning AMI with GPU support


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-id", default=os.getenv("AMI_ID", DEFAULT_AMI))
    parser.add_argument("--instance-type", default=os.getenv("INSTANCE_TYPE", "g5.xlarge"))
    parser.add_argument("--outfile", default="instance_id.txt")
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

    ec2 = boto3.client(
        "ec2",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION", "us-west-2"),
    )
    key_name = ensure_key(ec2, "demo-key")
    sg_id = ensure_sg(ec2, "valkey-demo-sg", "0.0.0.0/0")
    subnet_id = ec2.describe_subnets()["Subnets"][0]["SubnetId"]

    resp = ec2.run_instances(
        ImageId=args.image_id,
        InstanceType=args.instance_type,
        KeyName=key_name,
        NetworkInterfaces=[
            {
                "DeviceIndex": 0,
                "SubnetId": subnet_id,
                "Groups": [sg_id],
                "AssociatePublicIpAddress": True,
            }
        ],
        MinCount=1,
        MaxCount=1,
    )
    iid = resp["Instances"][0]["InstanceId"]
    # wait until instance is reported healthy
    for _ in range(60):
        st = ec2.describe_instance_status(InstanceIds=[iid]).get("InstanceStatuses")
        if st and st[0].get("InstanceStatus", {}).get("Status") == "ok":
            break
        time.sleep(5)

    with open(args.outfile, "w") as fh:
        fh.write(iid)
    print(iid)


if __name__ == "__main__":
    main()
