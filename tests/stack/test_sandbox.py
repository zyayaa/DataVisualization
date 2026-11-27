"""Live checks of the sandbox. Only a person runs them: STACK_TESTS=1."""

import os
import subprocess
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("STACK_TESTS") != "1", reason="stack suite: set STACK_TESTS=1"
)

PROJECT = "data-visualization-agent"
DATASET = "dataset.parquet"
LABELS = ("--filter", f"label=com.docker.compose.project={PROJECT}", "--filter", "label=com.docker.compose.service=sandbox")


def _sandbox_ids():
    out = subprocess.run(["docker", "ps", "-q", *LABELS], capture_output=True, text=True, timeout=60).stdout
    return out.split()


def _exec(*cmd):
    ids = _sandbox_ids()
    assert len(ids) == 1, "expected exactly one sandbox container"
    return subprocess.run(
        ["docker", "exec", "-u", "sandboxuser", "-w", "/workspace", ids[0], *cmd],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _python(code):
    return _exec("python", "-c", code)


def test_all_three_services_are_running(stack_up, docker_compose):
    running = docker_compose("ps", "--status", "running", "--services").stdout.split()
    assert {"sandbox", "litellm", "db"} <= set(running)


def test_sandbox_is_found_by_compose_labels(stack_up):
    assert len(_sandbox_ids()) == 1


def test_workspace_lists_the_dataset(stack_up):
    assert DATASET in _exec("ls", "/workspace").stdout.split()


def test_file_written_in_sandbox_appears_on_host(stack_up, repo_root):
    name = f"sandbox-test-{uuid.uuid4().hex}.txt"
    host_file = repo_root / "workspace" / name
    try:
        assert _exec("whoami").stdout.strip() == "sandboxuser"
        assert _exec("touch", name).returncode == 0
        assert host_file.exists()
    finally:
        host_file.unlink(missing_ok=True)


def test_outbound_connection_to_public_ip_fails(stack_up):
    code = "import socket,sys\ntry:\n socket.create_connection(('1.1.1.1',443),timeout=3)\nexcept OSError:\n sys.exit(0)\nsys.exit(1)"
    assert _python(code).returncode == 0


def test_host_name_lookup_fails(stack_up):
    code = "import socket,sys\ntry:\n socket.getaddrinfo('example.com',443)\nexcept OSError:\n sys.exit(0)\nsys.exit(1)"
    assert _python(code).returncode == 0


def test_proxy_is_unreachable_from_sandbox(stack_up):
    code = "import socket,sys\ntry:\n socket.create_connection(('litellm',4000),timeout=3)\nexcept OSError:\n sys.exit(0)\nsys.exit(1)"
    assert _python(code).returncode == 0


def test_sandbox_sees_no_secret_names(stack_up, container_env_names, example_env_names):
    ids = _sandbox_ids()
    assert len(ids) == 1
    out = subprocess.run(["docker", "exec", ids[0], "env"], capture_output=True, text=True, timeout=60).stdout
    names = {line.partition("=")[0] for line in out.splitlines()}
    assert names & example_env_names == set()
