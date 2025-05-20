from contextlib import contextmanager

import boto3


@contextmanager
def mock_ec2():
    boto3.reset()
    yield
    boto3.reset()
