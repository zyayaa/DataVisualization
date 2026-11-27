"""Live checks of the proxy and its database. Only a person runs them: STACK_TESTS=1."""

import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("STACK_TESTS") != "1", reason="stack suite: set STACK_TESTS=1"
)

PROXY_URL = "http://127.0.0.1:4000"


def _container_id(docker_compose, service):
    ids = docker_compose("ps", "-q", service).stdout.split()
    return ids[0] if ids else None


def _inspect(container_id, template):
    return subprocess.run(
        ["docker", "inspect", "--format", template, container_id],
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout.strip()


def test_litellm_and_db_are_running(stack_up, docker_compose):
    states = {}
    for service in ("litellm", "db"):
        cid = _container_id(docker_compose, service)
        states[service] = bool(cid) and _inspect(cid, "{{.State.Status}}") == "running"
    assert states == {"litellm": True, "db": True}


def test_db_is_healthy(stack_up, docker_compose):
    cid = _container_id(docker_compose, "db")
    healthy = bool(cid) and _inspect(cid, "{{.State.Health.Status}}") == "healthy"
    assert healthy


def test_proxy_reports_ready(stack_up):
    with urllib.request.urlopen(f"{PROXY_URL}/health/readiness", timeout=30) as response:
        status = response.status
    assert status == 200


def test_missing_key_gets_401(stack_up, chat):
    status, _ = chat("any", None)
    assert status == 401


def test_wrong_key_gets_401(stack_up, chat):
    status, _ = chat("any", "sk-not-the-master-key")
    assert status == 401


def test_master_key_is_not_refused(stack_up, chat, secrets):
    status, _ = chat("any", secrets.get("LITELLM_MASTER_KEY"))
    assert status != 401


def test_master_key_has_sk_prefix(secrets):
    key = secrets.get("LITELLM_MASTER_KEY") or ""
    has_prefix = key.startswith("sk-")
    assert has_prefix


def test_ui_page_is_served(stack_up):
    with urllib.request.urlopen(f"{PROXY_URL}/ui", timeout=30) as response:
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        body = response.read(4096).lower()
    is_html = "text/html" in content_type or b"<html" in body or b"<!doctype html" in body
    assert status == 200
    assert is_html


def test_proxy_port_is_loopback_only(stack_up, docker_compose):
    cid = _container_id(docker_compose, "litellm")
    assert cid
    raw = _inspect(cid, "{{json .NetworkSettings.Ports}}")
    bindings = json.loads(raw).get("4000/tcp") or []
    hosts = {b.get("HostIp") for b in bindings}
    loopback_only = bool(bindings) and hosts <= {"127.0.0.1"}
    assert loopback_only


def test_compose_refuses_an_empty_env(docker_compose):
    with tempfile.NamedTemporaryFile("w", suffix=".env") as empty:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")}
        result = docker_compose("--env-file", empty.name, "config", env=env)
    names_missing_variable = any(
        name in result.stderr
        for name in ("LITELLM_MASTER_KEY", "LITELLM_SALT_KEY", "UI_USERNAME", "UI_PASSWORD", "POSTGRES_PASSWORD")
    )
    refused = result.returncode != 0
    assert refused
    assert names_missing_variable
