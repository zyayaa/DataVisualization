"""Shared fixtures for the static tests of the Docker Compose stack.

Locked once written: items 02 and 03 reuse these fixtures unchanged.
Every fixture reads a committed file. None touches Docker or `.env`.
"""

import pathlib
import re

import pytest
import yaml

# `$$` is Compose's escape for a literal `$`; it is never an interpolation.
_INTERPOLATION_NAME = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")


def _read_text(path: pathlib.Path) -> str:
    if not path.is_file():
        pytest.fail(f"{path} does not exist")
    return path.read_text(encoding="utf-8")


def _string_values(node):
    """Yield every string value (never a mapping key) in a parsed YAML tree."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _string_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _string_values(item)
    elif isinstance(node, str):
        yield node


@pytest.fixture(scope="session")
def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def compose(repo_root) -> dict:
    """`compose.yaml` through `yaml.safe_load`."""
    data = yaml.safe_load(_read_text(repo_root / "compose.yaml"))
    if not isinstance(data, dict):
        pytest.fail("compose.yaml does not hold a mapping")
    return data


@pytest.fixture(scope="session")
def proxy_config(repo_root) -> dict:
    """`litellm/config.yaml` through `yaml.safe_load`; `{}` when it holds no mapping."""
    data = yaml.safe_load(_read_text(repo_root / "litellm" / "config.yaml"))
    return data if isinstance(data, dict) else {}


@pytest.fixture(scope="session")
def interpolated_names(repo_root) -> set[str]:
    """NAME of every `${NAME...}` interpolation in the values of `compose.yaml`.

    Comments are not interpolated by Compose, so the parsed values are read,
    not the raw text. `$$` (a literal dollar sign) is dropped first.
    """
    data = yaml.safe_load(_read_text(repo_root / "compose.yaml"))
    names: set[str] = set()
    for value in _string_values(data):
        names.update(_INTERPOLATION_NAME.findall(value.replace("$$", "")))
    return names


@pytest.fixture(scope="session")
def example_env_names(repo_root) -> set[str]:
    """Names defined (`NAME=value`) in `env.example`; comments and blank lines are skipped."""
    names: set[str] = set()
    for raw in _read_text(repo_root / "env.example").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        name, sep, _ = line.partition("=")
        if sep:
            names.add(name.strip())
    return names
