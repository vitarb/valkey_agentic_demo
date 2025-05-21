import os
from typing import Optional

from valkey_agentic_demo import boto3shim as boto3
from tenacity import retry


def ensure_key(ec2, key_name: str, skip: bool = False) -> Optional[str]:
    if skip:
        return None
    existing = ec2.describe_key_pairs(KeyNames=[key_name]).get("KeyPairs")
    if not existing:
        ec2.create_key_pair(KeyName=key_name)
    return key_name


def ensure_sg(ec2, sg_name: str, my_ip: str) -> str:
    groups = ec2.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [sg_name]}]
    ).get("SecurityGroups")
    if groups:
        gid = groups[0]["GroupId"]
    else:
        vpc_id = ec2.describe_vpcs()["Vpcs"][0]["VpcId"]
        gid = ec2.create_security_group(
            GroupName=sg_name, Description="demo", VpcId=vpc_id
        )["GroupId"]
    ec2.authorize_security_group_ingress(
        GroupId=gid,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": my_ip}],
            }
        ],
    )
    return gid


@retry
def launch_instance(
    ec2,
    image_id: str,
    instance_type: str,
    key_name: str,
    sg_id: str,
    spot: bool = False,
    dry_run: bool = False,
) -> str:
    opts = {}
    if spot:
        opts["InstanceMarketOptions"] = {"MarketType": "spot"}
    result = ec2.run_instances(
        ImageId=image_id,
        InstanceType=instance_type,
        KeyName=key_name,
        SecurityGroupIds=[sg_id],
        MinCount=1,
        MaxCount=1,
        DryRun=dry_run,
        **opts,
    )
    return result["Instances"][0]["InstanceId"]
