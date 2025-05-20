import boto3
from moto import mock_ec2
from valkey_agentic_demo.launcher.aws_helpers import (
    ensure_key,
    ensure_sg,
    launch_instance,
)


@mock_ec2()
def test_dry_run_prevents_launch():
    ec2 = boto3.client("ec2")
    ensure_key(ec2, "k")
    sg = ensure_sg(ec2, "sg", "0.0.0.0/0")
    try:
        launch_instance(ec2, "ami", "t", "k", sg, dry_run=True)
    except Exception:
        pass
    assert boto3._state["calls"]["run_instances"] == 0


@mock_ec2()
def test_spot_fallback(monkeypatch):
    ec2 = boto3.client("ec2")
    ensure_key(ec2, "k")
    sg = ensure_sg(ec2, "sg", "0.0.0.0/0")

    called = {"n": 0}

    real_run = ec2.run_instances

    def fail_once(**kw):
        called["n"] += 1
        if called["n"] == 1:
            raise Exception("spot failed")
        return real_run(**kw)

    monkeypatch.setattr(ec2, "run_instances", fail_once)
    iid = launch_instance(ec2, "ami", "t", "k", sg, spot=True)
    assert iid
    assert called["n"] == 2

@mock_ec2()
def test_ssm_skips_key(monkeypatch):
    ec2 = boto3.client("ec2")
    monkeypatch.setattr(ec2, "create_key_pair", lambda KeyName: (_ for _ in ()).throw(AssertionError("should not")))
    ensure_key(ec2, "k", skip=True)
