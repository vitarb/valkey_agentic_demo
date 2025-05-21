from dataclasses import dataclass

@dataclass
class Localstack:
    endpoint_url: str = "http://localhost:4566"
    region_name: str = "us-west-2"

def localstack_fixture():
    return Localstack()
