#!/usr/bin/env python3
"""Manage the Valkey agentic demo EC2 host (Python replacement for demo.sh)."""

import argparse, base64, datetime as _dt, json, os, pathlib, sys
from typing import Optional

RUNS_DIR = pathlib.Path('.demo_runs')
RUNS_DIR.mkdir(exist_ok=True)

TAG_KEY = 'valkey-demo'
TAG_VAL = 'agentic'
KEY_NAME = 'demo-key'
SG_NAME = 'valkey-demo-sg'
PEM_FILE = pathlib.Path(f"{KEY_NAME}.pem")

USER_DATA = r"""#!/bin/bash
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
set -eux
# --- packages: newer Python 3.11 + docker -------------------------------------
amazon-linux-extras enable python3.11 epel
yum -y install python3.11 python3.11-devel git docker curl
alternatives --set python3 /usr/bin/python3.11
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

systemctl enable --now docker
# Docker Compose v2 plugin
mkdir -p /usr/libexec/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
     -o /usr/libexec/docker/cli-plugins/docker-compose
chmod +x /usr/libexec/docker/cli-plugins/docker-compose
ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# NVIDIA runtime for GPU
curl -fsSL https://nvidia.github.io/nvidia-docker/amzn2/nvidia-docker.repo \
 | tee /etc/yum.repos.d/nvidia-docker.repo
yum -y install nvidia-driver-latest-dkms nvidia-container-toolkit
systemctl restart docker
usermod -aG docker ec2-user

# --- demo setup (as ec2-user) ------------------------------------------------
sudo -u ec2-user bash <<'EOSU'
set -eux
cd ~
git clone --depth=1 https://github.com/vitarb/valkey_agentic_demo.git
cd valkey_agentic_demo
python3 -m pip install -r requirements.txt
python3 tools/make_cc_csv.py 50000 data/news_sample.csv
python3 tools/bootstrap_grafana.py
docker-compose pull 2>&1 | tee docker-compose.log
docker-compose up -d   2>&1 | tee -a docker-compose.log
EOSU
"""


def _boto3_client(service: str, region: str, profile: Optional[str]):
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 not available – install to run live")
    session = boto3.Session(region_name=region, profile_name=profile) if profile else boto3.Session(region_name=region)
    return session.client(service)


def _find_instance(region: str, profile: Optional[str]) -> Optional[str]:
    ec2 = _boto3_client('ec2', region, profile)
    resp = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']},
            {'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VAL]},
        ]
    )
    for res in resp.get('Reservations', []):
        for inst in res.get('Instances', []):
            return inst['InstanceId']
    return None


def _public_ip(iid: str, region: str, profile: Optional[str]) -> str:
    ec2 = _boto3_client('ec2', region, profile)
    resp = ec2.describe_instances(InstanceIds=[iid])
    return resp['Reservations'][0]['Instances'][0].get('PublicIpAddress', '')


def _latest_amzn2(region: str, profile: Optional[str]) -> str:
    ec2 = _boto3_client('ec2', region, profile)
    resp = ec2.describe_images(
        Owners=['amazon'],
        Filters=[
            {'Name': 'name', 'Values': ['amzn2-ami-hvm-*-gp2']},
            {'Name': 'architecture', 'Values': ['x86_64']},
        ]
    )
    imgs = sorted(resp['Images'], key=lambda i: i['CreationDate'])
    return imgs[-1]['ImageId']


def _ensure_key_pair(region: str, profile: Optional[str]):
    ec2 = _boto3_client('ec2', region, profile)
    file_ok = PEM_FILE.exists()
    try:
        ec2.describe_key_pairs(KeyNames=[KEY_NAME])
        key_ok = True
    except Exception:
        key_ok = False
    if key_ok and not file_ok:
        print(f"⚠  {PEM_FILE} missing locally – recreating key-pair")
        ec2.delete_key_pair(KeyName=KEY_NAME)
        key_ok = False
    if not key_ok:
        print(f"⤵  creating key-pair {KEY_NAME}")
        km = ec2.create_key_pair(KeyName=KEY_NAME)['KeyMaterial']
        with open(PEM_FILE, 'w') as fh:
            fh.write(km)
        PEM_FILE.chmod(0o600)


def _ensure_security_group(region: str, profile: Optional[str], my_ip: str, use_ssh: bool) -> str:
    ec2 = _boto3_client('ec2', region, profile)
    resp = ec2.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [SG_NAME]}])
    groups = resp.get('SecurityGroups')
    sg_id = groups[0]['GroupId'] if groups else None
    if not sg_id:
        print(f"⤵  creating security group {SG_NAME}")
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}]).get('Vpcs')
        vpc = vpcs[0]['VpcId'] if vpcs else ec2.describe_vpcs()['Vpcs'][0]['VpcId']
        sg_id = ec2.create_security_group(GroupName=SG_NAME, Description='Valkey demo SG', VpcId=vpc)['GroupId']
    ports = [3000, 9090]
    if use_ssh:
        try:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}]
            )
        except Exception:
            pass
    for p in ports:
        try:
            ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{'IpProtocol': 'tcp', 'FromPort': p, 'ToPort': p, 'IpRanges': [{'CidrIp': my_ip}]}]
            )
        except Exception:
            pass
    return sg_id


def _run_instance(region: str, profile: Optional[str], instance_type: str, spot: bool, sg_id: str) -> str:
    ec2 = _boto3_client('ec2', region, profile)
    ami = _latest_amzn2(region, profile)
    print(f"⤵  launching EC2 {instance_type}")
    opts = {
        'ImageId': ami,
        'InstanceType': instance_type,
        'KeyName': KEY_NAME,
        'SecurityGroupIds': [sg_id],
        'TagSpecifications': [{'ResourceType': 'instance', 'Tags': [{'Key': TAG_KEY, 'Value': TAG_VAL}]}],
        'BlockDeviceMappings': [{'DeviceName': '/dev/xvda', 'Ebs': {'VolumeSize': 100}}],
        'UserData': base64.b64encode(USER_DATA.encode()).decode(),
        'MinCount': 1,
        'MaxCount': 1,
    }
    if spot:
        opts['InstanceMarketOptions'] = {'MarketType': 'spot'}
    resp = ec2.run_instances(**opts)
    iid = resp['Instances'][0]['InstanceId']
    print("⌛ waiting for status OK…")
    ec2.get_waiter('instance_status_ok').wait(InstanceIds=[iid])
    return iid


def _terminate_instance(iid: str, region: str, profile: Optional[str]):
    ec2 = _boto3_client('ec2', region, profile)
    print(f"🗑  terminating {iid}")
    ec2.terminate_instances(InstanceIds=[iid])
    ec2.get_waiter('instance_terminated').wait(InstanceIds=[iid])


class _Namespace:
    pass


def cmd_up(args: argparse.Namespace):
    run_id = args.run_id or _dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    run_file = RUNS_DIR / f"{run_id}.json"
    if args.dry_run:
        plan = {
            'action': 'up',
            'instance_type': args.instance_type,
            'spot': args.spot,
            'ssm': args.ssm,
            'region': args.region,
        }
        with open(run_file, 'w') as fh:
            json.dump({'status': 'planned', 'plan': plan, 'region': args.region}, fh, indent=2)
        print(json.dumps(plan, indent=2))
        return

    my_ip = os.popen('curl -s https://checkip.amazonaws.com').read().strip() + '/32'
    inst_id = _find_instance(args.region, args.profile)
    if inst_id:
        print(f"✔  reusing instance {inst_id}")
        sg_id = _ensure_security_group(args.region, args.profile, my_ip, not args.ssm)
    else:
        _ensure_key_pair(args.region, args.profile)
        sg_id = _ensure_security_group(args.region, args.profile, my_ip, not args.ssm)
        inst_id = _run_instance(args.region, args.profile, args.instance_type, args.spot, sg_id)
    pub = _public_ip(inst_id, args.region, args.profile)
    with open(run_file, 'w') as fh:
        json.dump({'instance_id': inst_id, 'key_name': KEY_NAME, 'pem_path': str(PEM_FILE),
                   'sg_id': sg_id, 'region': args.region}, fh, indent=2)
    print(f"\n🚀 Instance ready: {inst_id}\nSSH with port-forward:\n\n  ssh -i {PEM_FILE} -L 3000:localhost:3000 -L 9090:localhost:9090 ec2-user@{pub}\n\nGrafana   → http://localhost:3000  (admin / admin)\nPrometheus→ http://localhost:9090\n\nWhen finished:  python manage.py down --run-id {run_id}\n")


def cmd_down(args: argparse.Namespace):
    run_id = args.run_id
    if not run_id:
        print("--run-id required for down")
        sys.exit(1)
    run_file = RUNS_DIR / f"{run_id}.json"
    data = json.load(open(run_file)) if run_file.exists() else {}
    iid = data.get('instance_id')
    if args.dry_run:
        plan = {'action': 'down', 'instance_id': iid, 'region': args.region}
        print(json.dumps(plan, indent=2))
        if run_file.exists():
            run_file.unlink()
        return
    if not iid:
        iid = _find_instance(args.region, args.profile)
    if not iid:
        print("No demo instance found.")
        if run_file.exists():
            run_file.unlink()
        return
    _terminate_instance(iid, args.region, args.profile)
    ans = input("Delete security-group and key-pair too? [y/N] ")
    if ans.lower().startswith('y'):
        sg_id = data.get('sg_id') or _ensure_security_group(args.region, args.profile, '0.0.0.0/32', True)
        ec2 = _boto3_client('ec2', args.region, args.profile)
        try:
            ec2.delete_security_group(GroupId=sg_id)
        except Exception:
            pass
        try:
            ec2.delete_key_pair(KeyName=KEY_NAME)
            PEM_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        print("✓ cleanup done")
    if run_file.exists():
        run_file.unlink()


def cmd_list(args: argparse.Namespace):
    for p in sorted(RUNS_DIR.glob('*.json')):
        print(p.stem)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Launch or destroy the Valkey GPU demo EC2 instance')
    ap.add_argument('--region', default='us-east-1', help='AWS region')
    ap.add_argument('--profile', help='AWS profile')
    ap.add_argument('--dry-run', action='store_true', help='Print actions, no AWS calls')
    ap.add_argument('--run-id', help='Tag / folder name (default: timestamp)')

    sp = ap.add_subparsers(dest='command', required=True)
    up_p = sp.add_parser('up', help='Launch or reuse an EC2 instance')
    up_p.add_argument('--instance-type', default='g5.2xlarge')
    up_p.add_argument('--spot', action='store_true')
    up_p.add_argument('--ssm', action='store_true', help="Don't open port 22")
    up_p.set_defaults(func=cmd_up)

    down_p = sp.add_parser('down', help='Terminate the demo instance')
    down_p.set_defaults(func=cmd_down)

    list_p = sp.add_parser('list', help='Show recorded run-ids')
    list_p.set_defaults(func=cmd_list)

    args = ap.parse_args(argv)
    args.func(args)

if __name__ == '__main__':
    main()
