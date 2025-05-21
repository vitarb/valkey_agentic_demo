import os
import time
from pathlib import Path

import boto3
import typer

from . import userdata
from .aws_helpers import ensure_key, ensure_sg, launch_instance

app = typer.Typer()
RUN_DIR = Path(".demo_runs")
RUN_DIR.mkdir(exist_ok=True)


def _meta_path(run_id: str) -> Path:
    return RUN_DIR / f"{run_id}.env"


def _write_meta(run_id: str, key: str | None, sg: str, iid: str) -> None:
    path = _meta_path(run_id)
    with open(path, "w") as f:
        f.write(f"KEY={key or ''}\nSG={sg}\nIID={iid}\n")


def _load_meta(run_id: str) -> dict:
    data = {}
    with open(_meta_path(run_id)) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                data[k] = v
    return data


@app.command()
def up(
    run_id: str = None,
    instance_type: str = "g5.xlarge",
    spot: bool = False,
    ssm: bool = False,
    dry_run: bool = False,
):
    run_id = run_id or str(int(time.time()))
    ec2 = boto3.client("ec2")
    key = ensure_key(ec2, "demo-key", skip=ssm)
    sg = ensure_sg(ec2, "valkey-demo-sg", "0.0.0.0/0")
    iid = launch_instance(
        ec2,
        "ami-0f5c0fd7df464c253",
        instance_type,
        key or "",
        sg,
        spot=spot,
        dry_run=dry_run,
    )
    _write_meta(run_id, key, sg, iid)
    return iid


@app.command()
def down(run_id: str):
    ec2 = boto3.client("ec2")
    ids = []
    if run_id == "all":
        for p in RUN_DIR.glob("*.env"):
            data = _load_meta(p.stem)
            ids.append(data.get("IID"))
            p.unlink()
    else:
        data = _load_meta(run_id)
        ids.append(data.get("IID"))
        _meta_path(run_id).unlink()
    if ids:
        ec2.terminate_instances(InstanceIds=ids)


@app.command()
def list():
    for p in RUN_DIR.glob("*.env"):
        print(p.stem)
