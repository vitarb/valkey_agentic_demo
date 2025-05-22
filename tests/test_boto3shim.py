from valkey_agentic_demo import boto3shim


def test_ec2_describe_instance_status_passthrough():
    ec2 = boto3shim.client("ec2", region_name="us-west-2")
    resp = ec2.describe_instance_status(InstanceIds=["i-123"])
    assert (
        resp["InstanceStatuses"][0]["InstanceStatus"]["Status"] == "ok"
    )


if __name__ == "__main__":
    test_ec2_describe_instance_status_passthrough()
