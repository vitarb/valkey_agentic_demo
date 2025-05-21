import argparse
import os
import boto3


DEFAULT_AMI = "ami-0f5c0fd7df464c253"  # Deep Learning AMI with GPU support


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-id", default=os.getenv("AMI_ID", DEFAULT_AMI))
    parser.add_argument("--instance-type", default=os.getenv("INSTANCE_TYPE", "g5.xlarge"))
    parser.add_argument("--outfile", default="instance_id.txt")
    args = parser.parse_args()

    ec2 = boto3.client(
        "ec2",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION", "us-west-2"),
    )
    resp = ec2.run_instances(
        ImageId=args.image_id,
        InstanceType=args.instance_type,
        MinCount=1,
        MaxCount=1,
    )
    iid = resp["Instances"][0]["InstanceId"]
    with open(args.outfile, "w") as fh:
        fh.write(iid)
    print(iid)


if __name__ == "__main__":
    main()
