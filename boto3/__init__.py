import uuid
from typing import Dict, List

_state = {'keys': {}, 'sgs': {}, 'instances': {}, 'calls': {'run_instances': 0}}


class EC2Client:
    def __init__(self, state):
        self.state = state

    def describe_key_pairs(self, KeyNames=None):
        return {
            'KeyPairs': [
                {'KeyName': n} for n in KeyNames or [] if n in self.state['keys']
            ]
        }

    def create_key_pair(self, KeyName):
        self.state['keys'][KeyName] = {'KeyName': KeyName, 'KeyMaterial': 'k'}
        return {'KeyMaterial': 'k'}

    def delete_key_pair(self, KeyName):
        self.state['keys'].pop(KeyName, None)
        return {}

    def describe_security_groups(self, Filters=None):
        name = Filters[0]['Values'][0]
        groups = [v for v in self.state['sgs'].values() if v['GroupName'] == name]
        return {'SecurityGroups': groups}

    def create_security_group(self, GroupName, Description, VpcId):
        gid = f'sg-{uuid.uuid4().hex[:8]}'
        self.state['sgs'][gid] = {'GroupId': gid, 'GroupName': GroupName}
        return {'GroupId': gid}

    def authorize_security_group_ingress(self, GroupId, IpPermissions):
        return {}

    def describe_vpcs(self, Filters=None):
        return {'Vpcs': [{'VpcId': 'vpc-1'}]}

    def run_instances(self, **kwargs):
        if kwargs.get('DryRun'):
            raise Exception('DryRun')
        self.state['calls']['run_instances'] += 1
        iid = f'i-{uuid.uuid4().hex[:8]}'
        self.state['instances'][iid] = {'InstanceId': iid}
        return {'Instances': [{'InstanceId': iid}]}

    def describe_instances(self, InstanceIds=None, Filters=None):
        insts = [
            self.state['instances'][iid]
            for iid in InstanceIds or self.state['instances'].keys()
            if iid in self.state['instances']
        ]
        return {'Reservations': [{'Instances': insts}]}

    def terminate_instances(self, InstanceIds=None):
        for iid in InstanceIds or []:
            self.state['instances'].pop(iid, None)
        return {}


def client(service_name, region_name=None):
    if service_name == 'ec2':
        return EC2Client(_state)
    raise NotImplementedError


def reset():
    _state['keys'].clear()
    _state['sgs'].clear()
    _state['instances'].clear()
    _state['calls']['run_instances'] = 0
