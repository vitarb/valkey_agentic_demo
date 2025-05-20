import argparse
import os
import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-id", default=os.getenv("AMI_ID", "ami-test"))
    parser.add_argument("--instance-type", default="t3.micro")
    parser.add_argument("--outfile", default="instance_id.txt")
    args = parser.parse_args()

    if not os.getenv("AWS_ENDPOINT_URL") and args.image_id == "ami-test":
        parser.error("--image-id required when talking to AWS; use LocalStack or pass a valid AMI")

    ec2 = boto3.client(
        "ec2",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION"),
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
