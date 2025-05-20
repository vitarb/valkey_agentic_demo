import os
import subprocess
import boto3
from pytest_localstack import factories

localstack = factories.localstack_fixture()

def test_ec2_up_down(localstack, tmp_path):
    env = os.environ.copy()
    env.update({
        "AWS_ENDPOINT_URL": localstack.endpoint_url,
        "AWS_REGION": localstack.region_name,
        "PYTHONPATH": os.getcwd() + os.pathsep + env.get("PYTHONPATH", ""),
    })
    subprocess.check_call(["make", "ec2-up"], env=env)

    ec2 = boto3.client("ec2", endpoint_url=localstack.endpoint_url, region_name=localstack.region_name)
    res = ec2.describe_instances()
    instances = [i for r in res.get("Reservations", []) for i in r.get("Instances", [])]
    assert len(instances) == 1

    subprocess.check_call(["make", "ec2-down"], env=env)
    res = ec2.describe_instances()
    instances = [i for r in res.get("Reservations", []) for i in r.get("Instances", [])]
    assert len(instances) == 0
