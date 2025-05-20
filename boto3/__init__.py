import json
import uuid
from pathlib import Path
from typing import Dict, List

STATE_FILE = Path("boto3_state.json")


def _load() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"keys": {}, "sgs": {}, "instances": {}, "calls": {"run_instances": 0}}


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


def client(service_name, region_name=None, **kwargs):
    if service_name == 'ec2':
        return EC2Client(_state)
    raise NotImplementedError


def reset():
    _state['keys'].clear()
    _state['sgs'].clear()
    _state['instances'].clear()
    _state['calls']['run_instances'] = 0
    _save()
