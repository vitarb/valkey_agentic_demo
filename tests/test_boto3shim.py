from valkey_agentic_demo import boto3shim


def test_ec2_describe_instance_status_passthrough():
    ec2 = boto3shim.client("ec2", region_name="us-west-2")
    try:
        _ = getattr(ec2, "describe_instance_status")
        print("PASS: describe_instance_status is accessible")
    except AttributeError:
        print("FAIL: describe_instance_status is not accessible")


if __name__ == "__main__":
    test_ec2_describe_instance_status_passthrough()
