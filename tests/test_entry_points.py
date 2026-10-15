"""The `uniqr` and `uniqr-scan` commands must point at something pip installs.

Both commands live in app.py and scan.py, which sit beside the package rather
than inside it. Setuptools only installs what it is told to, so a command whose
module is not listed installs fine and then fails the first time it is run,
with "No module named 'app'". Running from the repo folder hides it, because
Python finds the file in the current directory.
"""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _config() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _installed(module: str, config: dict) -> bool:
    setuptools = config["tool"]["setuptools"]
    top = module.split(".")[0]
    if top in setuptools.get("py-modules", []):
        return True
    patterns = setuptools.get("packages", {}).get("find", {}).get("include", [])
    return any(top == pattern.rstrip("*") for pattern in patterns)


def test_every_command_points_at_an_installed_module():
    config = _config()
    scripts = config["project"]["scripts"]
    assert scripts, "no commands declared"
    for command, target in scripts.items():
        module = target.split(":")[0]
        assert _installed(module, config), (
            f"`{command}` runs {target}, but {module} is not installed by pip"
        )


def test_every_command_points_at_a_real_function():
    for command, target in _config()["project"]["scripts"].items():
        module, function = target.split(":")
        source = (ROOT / f"{module.replace('.', '/')}.py").read_text(encoding="utf-8")
        assert f"def {function}(" in source, f"`{command}`: no {function}() in {module}.py"
