"""Live checks of the Claude set-up: verdict "No Claude" (decisions.md, 2026-11-26). Only a person runs them: STACK_TESTS=1."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("STACK_TESTS") != "1", reason="stack suite: set STACK_TESTS=1"
)

TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"


def test_claude_setup_matches_the_verdict(stack_up, secrets, chat):
    statuses = {a: chat(a, secrets["LITELLM_MASTER_KEY"])[0] for a in ("opus", "sonnet", "haiku")}
    assert all(s != 200 for s in statuses.values()), statuses


def test_subscription_token_presence_matches_the_verdict(stack_up, secrets, container_env_names):
    names = container_env_names("litellm")
    present = {
        "container token": TOKEN in names,
        "container authorization": "CLAUDE_UPSTREAM_AUTHORIZATION" in names,
        "env file token": TOKEN in secrets,
    }
    assert not any(present.values()), [k for k, v in present.items() if v]


def test_env_file_defines_no_anthropic_api_key(secrets):
    assert "ANTHROPIC_API_KEY" not in secrets


def test_proxy_container_has_no_anthropic_api_key(stack_up, container_env_names):
    assert "ANTHROPIC_API_KEY" not in container_env_names("litellm")
