import json
import uuid
from pathlib import Path
from typing import Dict, List

STATE_FILE = Path("boto3_state.json")


def _load() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "keys": {},
        "sgs": {},
        "instances": {},
        "calls": {"run_instances": 0},
        "enis": {},
        "subnets": {},
    }


_state = _load()


def _save() -> None:
    STATE_FILE.write_text(json.dumps(_state))


class EC2Client:
    def __init__(self, state):
        self.state = state

    def describe_key_pairs(self, KeyNames=None):
        self.state.update(_load())
        return {
            'KeyPairs': [
                {'KeyName': n} for n in KeyNames or [] if n in self.state['keys']
            ]
        }

    def create_key_pair(self, KeyName):
        self.state.update(_load())
        self.state['keys'][KeyName] = {'KeyName': KeyName, 'KeyMaterial': 'k'}
        _save()
        return {'KeyMaterial': 'k'}

    def delete_key_pair(self, KeyName):
        self.state.update(_load())
        self.state['keys'].pop(KeyName, None)
        _save()
        return {}

    def describe_security_groups(self, Filters=None):
        self.state.update(_load())
        name = Filters[0]['Values'][0]
        groups = [v for v in self.state['sgs'].values() if v['GroupName'] == name]
        return {'SecurityGroups': groups}

    def create_security_group(self, GroupName, Description, VpcId):
        self.state.update(_load())
        gid = f'sg-{uuid.uuid4().hex[:8]}'
        self.state['sgs'][gid] = {'GroupId': gid, 'GroupName': GroupName}
        _save()
        return {'GroupId': gid}

    def authorize_security_group_ingress(self, GroupId, IpPermissions):
        return {}

    def describe_vpcs(self, Filters=None):
        self.state.update(_load())
        return {'Vpcs': [{'VpcId': 'vpc-1'}]}

    def describe_subnets(self):
        self.state.update(_load())
        subs = [
            {"SubnetId": sid, **data}
            for sid, data in self.state.get("subnets", {}).items()
        ]
        if not subs:
            subs = [{"SubnetId": "subnet-1"}]
        return {"Subnets": subs}

    def create_subnet(self, VpcId, CidrBlock):
        self.state.update(_load())
        sid = f"subnet-{uuid.uuid4().hex[:8]}"
        self.state.setdefault("subnets", {})[sid] = {
            "VpcId": VpcId,
            "CidrBlock": CidrBlock,
        }
        _save()
        return {"Subnet": {"SubnetId": sid}}

    def delete_subnet(self, SubnetId):
        self.state.update(_load())
        self.state.get("subnets", {}).pop(SubnetId, None)
        _save()
        return {}

    def create_network_interface(self, SubnetId, Groups=None):
        self.state.update(_load())
        eni_id = f'eni-{uuid.uuid4().hex[:8]}'
        self.state.setdefault('enis', {})[eni_id] = {
            'NetworkInterfaceId': eni_id,
            'SubnetId': SubnetId,
            'Groups': Groups or [],
        }
        _save()
        return {'NetworkInterface': {'NetworkInterfaceId': eni_id}}

    def delete_network_interface(self, NetworkInterfaceId):
        self.state.update(_load())
        self.state.get('enis', {}).pop(NetworkInterfaceId, None)
        _save()
        return {}

    def describe_instance_status(self, InstanceIds):
        """
        Stub health-check API used by scripts/ec2_up.py.
        Always returns an 'ok' status for the first InstanceId.
        """
        return {
            "InstanceStatuses": [
                {
                    "InstanceId": InstanceIds[0],
                    "InstanceStatus": {"Status": "ok"},
                    "SystemStatus": {"Status": "ok"},
                }
            ]
        }

    def run_instances(self, **kwargs):
        self.state.update(_load())
        if kwargs.get('DryRun'):
            raise Exception('DryRun')
        self.state['calls']['run_instances'] += 1
        iid = f'i-{uuid.uuid4().hex[:8]}'
        self.state['instances'][iid] = {'InstanceId': iid}
        _save()
        return {'Instances': [{'InstanceId': iid}]}

    def describe_instances(self, InstanceIds=None, Filters=None):
        self.state.update(_load())
        insts = [
            self.state['instances'][iid]
            for iid in InstanceIds or self.state['instances'].keys()
            if iid in self.state['instances']
        ]
        return {'Reservations': [{'Instances': insts}]}

    def terminate_instances(self, InstanceIds=None):
        self.state.update(_load())
        for iid in InstanceIds or []:
            self.state['instances'].pop(iid, None)
        _save()
        return {}

    def delete_security_group(self, GroupId):
        self.state.update(_load())
        self.state.get('sgs', {}).pop(GroupId, None)
        _save()
        return {}


def client(service_name, region_name=None, **kwargs):
    if service_name == 'ec2':
        return EC2Client(_state)
    raise NotImplementedError


def reset():
    _state['keys'].clear()
    _state['sgs'].clear()
    _state['instances'].clear()
    _state['enis'].clear()
    _state['subnets'].clear()
    _state['calls']['run_instances'] = 0
    _save()
