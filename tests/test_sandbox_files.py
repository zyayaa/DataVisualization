"""Static tests for item 001/03: the `sandbox` service in `compose.yaml`.

They read `compose.yaml` and run pytest in a subprocess on the stack module.
They never touch Docker or `.env`. Each test names the acceptance criterion it checks.
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET

STACK_SANDBOX_TESTS = {
    "test_all_three_services_are_running",
    "test_sandbox_is_found_by_compose_labels",
    "test_workspace_lists_the_dataset",
    "test_file_written_in_sandbox_appears_on_host",
    "test_outbound_connection_to_public_ip_fails",
    "test_host_name_lookup_fails",
    "test_proxy_is_unreachable_from_sandbox",
    "test_sandbox_sees_no_secret_names",
}
FORBIDDEN_KEYS = (
    "ports",
    "networks",
    "environment",
    "env_file",
    "user",
    "container_name",
    "deploy",
    "mem_limit",
    "cpus",
    "cap_drop",
    "read_only",
)


def _sandbox(compose) -> dict:
    services = compose.get("services")
    assert isinstance(services, dict), "compose.yaml has no services mapping"
    assert "sandbox" in services, "compose.yaml defines no service 'sandbox'"
    service = services["sandbox"]
    return service if isinstance(service, dict) else {}


def _volume_mounts(service):
    """Yield (source, target, read_only) for each entry of a service's `volumes`."""
    for entry in service.get("volumes") or []:
        if isinstance(entry, dict):
            yield (
                str(entry.get("source", "")),
                str(entry.get("target", "")),
                bool(entry.get("read_only", False)),
            )
        else:
            parts = str(entry).split(":")
            if len(parts) == 1:
                yield ("", parts[0], False)
            else:
                mode = parts[2] if len(parts) > 2 else ""
                yield (parts[0], parts[1], "ro" in mode.split(","))


def test_ac1_sandbox_build_context_is_sandbox_dir(compose, repo_root):
    """AC1: the `sandbox` build context is `./sandbox` (short or long `build` form)."""
    build = _sandbox(compose).get("build")
    context = build.get("context") if isinstance(build, dict) else build
    assert isinstance(context, str) and context, "sandbox has no build context"
    assert (repo_root / context).resolve() == (repo_root / "sandbox").resolve(), (
        f"sandbox build context is {context!r}, expected ./sandbox"
    )


def test_ac2_sandbox_has_no_network(compose):
    """AC2: `sandbox` has `network_mode: none`."""
    assert _sandbox(compose).get("network_mode") == "none"


def test_ac3_sandbox_has_init(compose):
    """AC3: `sandbox` has `init: true`."""
    assert _sandbox(compose).get("init") is True


def test_ac4_sandbox_has_none_of_the_forbidden_keys(compose):
    """AC4: `sandbox` has none of the keys ports, networks, environment, env_file, user, ... read_only."""
    service = _sandbox(compose)
    assert service, "the sandbox service is empty"
    present = [key for key in FORBIDDEN_KEYS if key in service]
    assert present == [], f"sandbox has forbidden keys: {present}"


def test_ac5_sandbox_mounts_only_the_workspace_read_write(compose, repo_root):
    """AC5: `sandbox` mounts exactly one volume, `./workspace` at `/workspace`, read-write."""
    mounts = [
        ((repo_root / os.path.expanduser(source)).resolve() if source else None, target, read_only)
        for source, target, read_only in _volume_mounts(_sandbox(compose))
    ]
    expected = [((repo_root / "workspace").resolve(), "/workspace", False)]
    assert mounts == expected, f"sandbox mounts {mounts}, expected only ./workspace:/workspace read-write"


def test_ac14_stack_sandbox_tests_are_skipped_without_stack_tests(repo_root, tmp_path):
    """AC14: without `STACK_TESTS`, `tests/stack/test_sandbox.py` exits 0, runs nothing, skips the eight tests."""
    module = repo_root / "tests" / "stack" / "test_sandbox.py"
    assert module.is_file(), "tests/stack/test_sandbox.py does not exist"
    env = {k: v for k, v in os.environ.items() if k != "STACK_TESTS"}
    report = tmp_path / "report.xml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report}",
            "tests/stack/test_sandbox.py",
        ],
        cwd=repo_root,
        check=False,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"pytest exited {result.returncode}"
    assert report.is_file(), "pytest wrote no report"
    outcomes = {}
    for case in ET.parse(report).getroot().iter("testcase"):
        children = {child.tag for child in case}
        outcomes[case.get("name")] = "skipped" if "skipped" in children else "ran"
    ran = sorted(name for name, outcome in outcomes.items() if outcome != "skipped")
    assert ran == [], f"tests that ran without STACK_TESTS: {ran}"
    missing = sorted(STACK_SANDBOX_TESTS - {n for n, o in outcomes.items() if o == "skipped"})
    assert missing == [], f"contract tests not reported as skipped: {missing}"
