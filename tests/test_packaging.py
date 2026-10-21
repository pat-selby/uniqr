"""The installed commands must point at code that the install actually includes.

`uniqr` pointed at app.py, which sat outside the package and was never installed,
so the command failed with "No module named 'app'" for anyone who installed
UniQR instead of running it from the source folder.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def config():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def installed_top_level() -> set[str]:
    setuptools = config()["tool"]["setuptools"]
    modules = set(setuptools.get("py-modules", []))
    packages = {p.rstrip("*").split(".")[0] for p in setuptools["packages"]["find"]["include"]}
    return modules | packages


def test_every_command_points_at_installed_code():
    for name, target in config()["project"]["scripts"].items():
        module, _, func = target.partition(":")
        assert module.split(".")[0] in installed_top_level(), f"{name} -> {module} is not installed"
        assert func, f"{name} names no function"


def test_every_listed_module_exists():
    for module in config()["tool"]["setuptools"].get("py-modules", []):
        assert (ROOT / f"{module}.py").is_file()
