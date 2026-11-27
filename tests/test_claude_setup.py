"""Static tests of the proxy's Claude set-up: an Anthropic API key from `.env`.

They read committed files only. They never touch Docker or `.env`.
"""

import subprocess

ALIASES = {"haiku"}
KEY_REF = "os.environ/ANTHROPIC_API_KEY"


def test_config_maps_each_alias_to_an_anthropic_model_with_the_key(proxy_config):
    models = {m["model_name"]: m["litellm_params"] for m in proxy_config.get("model_list") or []}
    assert set(models) == ALIASES
    for alias, params in models.items():
        assert params["model"].startswith("anthropic/claude-"), alias
        assert params["api_key"] == KEY_REF, alias


def test_env_example_names_the_api_key(example_env_names):
    assert "ANTHROPIC_API_KEY" in example_env_names


def test_litellm_requires_the_api_key(compose):
    env = compose["services"]["litellm"]["environment"]
    assert env["ANTHROPIC_API_KEY"].startswith("${ANTHROPIC_API_KEY:?")


def test_no_committed_file_holds_an_anthropic_key_value(repo_root):
    result = subprocess.run(
        ["git", "grep", "-I", "-l", "-E", r"sk-ant-[a-z]{3}[0-9]{2}-[A-Za-z0-9_-]{8,}"],
        cwd=repo_root, capture_output=True, text=True, check=False,
    )
    assert result.returncode in (0, 1), "git grep failed"
    assert result.stdout.split() == [], f"files holding a key value: {result.stdout.split()}"
