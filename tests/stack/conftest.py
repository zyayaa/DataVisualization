"""Fixtures of the stack suite. Run only by a person: STACK_TESTS=1.

Nothing here touches Docker at import or collection time. Secrets exist only
inside the test process and are never printed.
"""

import json
import subprocess
import time
import urllib.error
import urllib.request

import pytest
from dotenv import dotenv_values

PROXY_URL = "http://127.0.0.1:4000"
PROJECT = "data-visualization-agent"


@pytest.fixture(scope="session")
def docker_compose(repo_root):
    def run(*args, timeout=60, env=None, check=False):
        return subprocess.run(
            ["docker", "compose", "-p", PROJECT, *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=check,
        )

    return run


class _Secrets(dict):
    """The values of .env. The repr hides them, so a failure report never prints them."""

    def __repr__(self):
        return "<secrets hidden>"

    __str__ = __repr__


@pytest.fixture(scope="session")
def secrets(repo_root):
    return _Secrets(dotenv_values(repo_root / ".env"))


@pytest.fixture(scope="session")
def stack_up(docker_compose):
    result = docker_compose("up", "-d", timeout=15 * 60)
    started = result.returncode == 0
    assert started, "docker compose up -d failed"
    deadline = time.monotonic() + 300
    status = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{PROXY_URL}/health/readiness", timeout=5) as r:
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
        except OSError:
            status = None
        if status == 200:
            return
        time.sleep(3)
    pytest.fail(f"readiness did not return 200 in time (last status {status})")


@pytest.fixture(scope="session")
def chat():
    def call(alias, bearer=None):
        headers = {"Content-Type": "application/json"}
        if bearer is not None:
            headers["Authorization"] = f"Bearer {bearer}"
        body = json.dumps({"model": alias, "messages": [{"role": "user", "content": "ping"}]})
        req = urllib.request.Request(
            f"{PROXY_URL}/v1/chat/completions", data=body.encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read()
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = {}
        return status, parsed if isinstance(parsed, dict) else {}

    return call


@pytest.fixture(scope="session")
def container_env_names(docker_compose):
    def names(service):
        ids = docker_compose("ps", "-q", service).stdout.split()
        assert ids, "no container for the service"
        out = subprocess.run(
            ["docker", "inspect", "--format", "{{range .Config.Env}}{{println .}}{{end}}", ids[0]],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        return {line.partition("=")[0] for line in out.splitlines() if line}

    return names
