from pathlib import Path

from valkey_agentic_demo.launcher.cli import _load_meta, _write_meta


def test_meta_roundtrip(tmp_path):
    run_dir = tmp_path / ".demo_runs"
    run_dir.mkdir()
    meta_file = run_dir / "abc.env"
    # patch RUN_DIR in cli
    import valkey_agentic_demo.launcher.cli as cli

    cli.RUN_DIR = run_dir

    _write_meta("abc", "k", "sg", "iid")
    data = _load_meta("abc")
    assert data == {"KEY": "k", "SG": "sg", "IID": "iid"}
