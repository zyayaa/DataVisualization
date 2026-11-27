"""Live checks of the Claude set-up. Only a person runs them: STACK_TESTS=1 (each call costs a few tokens)."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("STACK_TESTS") != "1", reason="stack suite: set STACK_TESTS=1"
)


def test_proxy_container_has_the_api_key(stack_up, container_env_names):
    assert "ANTHROPIC_API_KEY" in container_env_names("litellm")


@pytest.mark.parametrize("alias", ["haiku"])
def test_alias_answers(stack_up, secrets, chat, alias):
    status, body = chat(alias, secrets["LITELLM_MASTER_KEY"])
    assert status == 200, body.get("error")
    assert body["choices"][0]["message"]["content"]
