"""Static tests for item 001/02: the proxy's Claude set-up matches the token verdict.

The arm is selected by the newest probe verdict record in the epic's
`decisions.md`, the entry dated 2026-11-26, which reads:

    Verdict: No Claude
    Tag: v1.108.18
    Wiring: none

So these tests guard the "No Claude" arm only: no model, no token, no
`os.environ/` reference. The "Build with Claude" arm is deliberately not
written; a newer verdict record makes every arm test fail until a replan.

They read committed files and run pytest in a subprocess. They never touch
Docker or `.env`. Each test names the acceptance criterion it checks.
"""

import os
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

DECISIONS = pathlib.Path(
    "docs/epics/001-docker-compose-stack-with-sandbox-and-li/decisions.md"
)
TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
BASE_SECRET_NAMES = {
    "LITELLM_MASTER_KEY",
    "LITELLM_SALT_KEY",
    "UI_USERNAME",
    "UI_PASSWORD",
    "POSTGRES_PASSWORD",
}
BASE_LITELLM_KEYS = {
    "LITELLM_MASTER_KEY",
    "LITELLM_SALT_KEY",
    "UI_USERNAME",
    "UI_PASSWORD",
    "DATABASE_URL",
}
STACK_CLAUDE_TESTS = {
    "test_claude_setup_matches_the_verdict",
    "test_subscription_token_presence_matches_the_verdict",
    "test_env_file_defines_no_anthropic_api_key",
    "test_proxy_container_has_no_anthropic_api_key",
}
_VERDICT_RECORD = re.compile(
    r"^Verdict:[ \t]*(.+?)[ \t]*\nTag:[ \t]*(\S+)[ \t]*\nWiring:[ \t]*(.+?)[ \t]*$",
    re.MULTILINE,
)
_INTERPOLATION_NAME = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")


@pytest.fixture(scope="module")
def no_claude_verdict(repo_root):
    """Fail unless the newest verdict record still selects the arm written here."""
    path = repo_root / DECISIONS
    assert path.is_file(), f"{DECISIONS} does not exist"
    records = _VERDICT_RECORD.findall(path.read_text(encoding="utf-8"))
    if not records:
        pytest.fail(
            "decisions.md holds no probe verdict record (BLOCKED: the arm is never guessed)"
        )
    verdict, _, wiring = records[-1]
    assert (verdict, wiring) == ("No Claude", "none"), (
        f"the newest verdict is {verdict!r} with wiring {wiring!r}; "
        "these tests cover only 'No Claude' and need a replan"
    )


def _environment(service) -> dict:
    env = (service or {}).get("environment") or {}
    if isinstance(env, dict):
        return dict(env)
    result = {}
    for entry in env:
        name, sep, value = str(entry).partition("=")
        result[name] = value if sep else None
    return result


def _string_values(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _string_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _string_values(item)
    elif isinstance(node, str):
        yield node


def test_ac1_config_defines_no_model(no_claude_verdict, proxy_config):
    """AC1 (No Claude): `litellm/config.yaml` defines no model."""
    assert not proxy_config.get("model_list"), "litellm/config.yaml defines a model"


def test_ac2_env_example_holds_the_base_five_and_no_token(
    no_claude_verdict, example_env_names, repo_root
):
    """AC2 (No Claude): `env.example` names exactly the base five and never mentions the token."""
    assert example_env_names == BASE_SECRET_NAMES
    text = (repo_root / "env.example").read_text(encoding="utf-8").lower()
    mentioned = [
        word for word in (TOKEN.lower(), "setup-token", "oauth") if word in text
    ]
    assert mentioned == [], f"env.example mentions the token: {mentioned}"


def test_ac3_litellm_environment_is_the_base_keys_and_no_service_interpolates_the_token(
    no_claude_verdict, compose
):
    """AC3 (No Claude): `litellm` has exactly the five base keys; no service interpolates the token."""
    services = compose.get("services")
    assert isinstance(services, dict) and "litellm" in services, (
        "compose.yaml defines no litellm service"
    )
    assert set(_environment(services["litellm"])) == BASE_LITELLM_KEYS
    interpolating = sorted(
        name
        for name, service in services.items()
        if any(
            TOKEN in _INTERPOLATION_NAME.findall(v.replace("$$", ""))
            for v in _string_values(service)
        )
    )
    assert interpolating == [], f"services interpolating {TOKEN}: {interpolating}"


def test_ac4_config_holds_no_os_environ_reference(no_claude_verdict, repo_root):
    """AC4 (No Claude): `litellm/config.yaml` holds no `os.environ/` reference."""
    path = repo_root / "litellm" / "config.yaml"
    assert path.is_file(), "litellm/config.yaml does not exist"
    assert "os.environ/" not in path.read_text(encoding="utf-8")


def test_ac5_stack_claude_tests_are_skipped_without_stack_tests(repo_root, tmp_path):
    """AC5: without `STACK_TESTS`, `tests/stack/test_claude.py` exits 0, runs nothing, skips the four tests."""
    module = repo_root / "tests" / "stack" / "test_claude.py"
    assert module.is_file(), "tests/stack/test_claude.py does not exist"
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
            "tests/stack/test_claude.py",
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
    missing = sorted(STACK_CLAUDE_TESTS - set(outcomes))
    assert missing == [], f"contract tests not reported as skipped: {missing}"


def test_edge_no_committed_file_holds_a_token_value(repo_root):
    """Edge case: the token's value never appears in a committed file, only its name does."""
    # A subscription token starts `sk-ant-oat` and a two-digit version (fact-sheet row 11).
    result = subprocess.run(
        ["git", "grep", "-I", "-l", "-E", r"sk-ant-oat[0-9]{2}-[A-Za-z0-9_-]{8,}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode in (0, 1), "git grep failed"
    assert result.stdout.split() == [], (
        f"committed files holding a token value: {result.stdout.split()}"
    )
