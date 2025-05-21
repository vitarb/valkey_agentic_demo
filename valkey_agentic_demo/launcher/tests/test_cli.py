from pathlib import Path

from valkey_agentic_demo import boto3shim as boto3
from moto import mock_ec2
from typer.testing import CliRunner
from valkey_agentic_demo.launcher.cli import RUN_DIR, app


@mock_ec2()
def test_up_creates_metadata(tmp_path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr("valkey_agentic_demo.launcher.cli.RUN_DIR", tmp_path)
    result = runner.invoke(app, ["up", "test1"])
    assert result.exit_code == 0
    meta = tmp_path / "test1.env"
    assert meta.exists()
    data = meta.read_text()
    assert "KEY=" in data and "SG=" in data and "IID=" in data

