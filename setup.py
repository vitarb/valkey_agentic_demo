from setuptools import find_packages, setup

setup(
    name="valkey_agentic_demo",
    version="0.1.0",
    packages=find_packages(
        include=[
            "valkey_agentic_demo",
            "valkey_agentic_demo.*",
            "typer",
            "jinja2",
            "tenacity",
            "flake8",
        ]
    ),
    entry_points={
        "console_scripts": ["valkey-demo=valkey_agentic_demo.launcher.cli:app"]
    },
)
