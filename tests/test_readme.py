"""Static tests for item 001/03: what `README.md` tells a new contributor.

Statements are matched per README section (the text between
two Markdown headings), case-insensitively, with whitespace collapsed.
Each test names the acceptance criterion it checks.
"""

import pathlib
import re

import pytest

STACK_COMMAND = "STACK_TESTS=1 uv run --with pytest pytest tests/stack -v"
_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)


@pytest.fixture(scope="module")
def readme(repo_root) -> str:
    path = repo_root / "README.md"
    assert path.is_file(), "README.md does not exist"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sections(readme) -> list[str]:
    """README sections, lowercased, backticks dropped, whitespace collapsed."""
    return [" ".join(part.replace("`", "").lower().split()) for part in _HEADING.split(readme)]


def _section_with(sections, *patterns) -> bool:
    return any(all(re.search(p, s) for p in patterns) for s in sections)


def _adr_path(repo_root, number: str) -> str:
    found = sorted((repo_root / "docs" / "adr").glob(f"{number}-*.md"))
    assert found, f"docs/adr holds no ADR {number}"
    return f"docs/adr/{found[0].name}"


def test_ac6_setup_steps_in_order(readme):
    """AC6: copy `env.example` to `.env`, then fill it in, then `docker compose up -d`.

    The copy step is `cp env.example .env` or "copy env.example to .env"; "fill"
    must follow it, and `docker compose up -d` must follow that.
    """
    text = readme.replace("`", "")
    copy = re.search(
        r"\bcp\s+(?:\./)?env\.example\s+(?:\./)?\.env(?![\w.])"
        r"|\bcopy\b.{0,40}?(?<![\w.])env\.example\b.{0,20}?\bto\b.{0,20}?(?<![\w])\.env(?![\w.])",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    assert copy, "README does not say to copy env.example to .env"
    fill = re.search(r"\bfill", text[copy.end() :], re.IGNORECASE)
    assert fill, "README does not say to fill in .env after copying it"
    after_fill = copy.end() + fill.end()
    assert "docker compose up -d" in text[after_fill:], (
        "README does not give `docker compose up -d` after the fill-in step"
    )


def test_ac7_names_env_example_never_dot_env_example(readme):
    """AC7: README names `env.example` and never `.env.example`."""
    assert re.search(r"(?<![\w.])env\.example", readme), "README does not name env.example"
    assert ".env.example" not in readme, "README names .env.example"


def test_ac8_gives_proxy_and_ui_urls(readme):
    """AC8: README gives `http://127.0.0.1:4000` and `http://127.0.0.1:4000/ui`."""
    assert "http://127.0.0.1:4000/ui" in readme, "README does not give http://127.0.0.1:4000/ui"
    assert re.search(r"http://127\.0\.0\.1:4000(?!/ui)(?!\d)", readme), (
        "README does not give http://127.0.0.1:4000 on its own"
    )


def test_ac9_salt_key_rule(sections):
    """AC9: one section names `LITELLM_SALT_KEY` and says it is generated once, never changed,
    and cannot be rotated in place."""
    assert _section_with(sections, r"litellm_salt_key"), "README does not name LITELLM_SALT_KEY"
    assert _section_with(
        sections,
        r"litellm_salt_key",
        r"generat\w*.{0,40}?\bonce\b",
        r"\bnever\b.{0,40}?\bchang",
        r"\b(?:cannot|can't|can not|not)\b.{0,40}?\brotat\w*.{0,40}?\bin place\b",
    ), "no README section says LITELLM_SALT_KEY is generated once, never changed, not rotatable in place"


def test_ac10_pgdata_volume_and_down_v(sections):
    """AC10: one section says `litellm_pgdata` holds the database and `docker compose down -v` deletes it."""
    assert _section_with(
        sections,
        r"litellm_pgdata",
        r"database|postgres",
        r"docker compose down -v\b",
        r"delet|remov|eras|wipe|destroy",
    ), "no README section says what litellm_pgdata holds and that docker compose down -v deletes it"


def test_ac11_linux_write_limitation_of_workspace(sections):
    """AC11: one section states that on Linux, writes to the workspace mount may fail when the
    owner of `workspace/` has another user id than the sandbox user (ADR 0006)."""
    assert _section_with(
        sections,
        r"\blinux\b",
        r"workspace",
        r"\bwrit",
        r"\buid\b|user id|user-id|owner",
    ), "no README section states the Linux write limitation of the workspace mount"


def test_ac12_gives_the_stack_test_command(readme):
    """AC12: README gives `STACK_TESTS=1 uv run --with pytest pytest tests/stack -v`."""
    assert STACK_COMMAND in readme


def test_ac13_readme_describes_the_claude_api_key(sections):
    """AC13: one section names the `haiku` alias and `ANTHROPIC_API_KEY`."""
    assert _section_with(sections, r"anthropic_api_key", r"\bhaiku\b"), (
        "README does not describe the haiku alias and ANTHROPIC_API_KEY"
    )


def test_edge_readme_cites_adr_paths_not_decisions(repo_root, readme):
    """Edge case: README cites ADRs by existing `docs/adr/` paths, never `decisions.md` or `docs/epics/`."""
    assert "decisions.md" not in readme, "README cites decisions.md"
    assert "docs/epics" not in readme, "README cites the epic folder"
    cited = set(re.findall(r"docs/adr/[\w.-]+\.md", readme))
    assert cited, "README cites no ADR path"
    missing = sorted(p for p in cited if not (repo_root / p).is_file())
    assert missing == [], f"README cites ADR paths that do not exist: {missing}"
