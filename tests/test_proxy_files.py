"""Static tests for item 001/01: the proxy, its database and the admin UI.

They read the committed files of the stack (`.gitignore`, `compose.yaml`,
`litellm/config.yaml`, `env.example`) and the epic's `decisions.md`. They never
touch Docker or `.env`. Each test names the acceptance criterion it checks.
"""

import os
import pathlib
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

DECISIONS = pathlib.Path("docs/epics/001-docker-compose-stack-with-sandbox-and-li/decisions.md")
BASE_SECRET_NAMES = {
    "LITELLM_MASTER_KEY",
    "LITELLM_SALT_KEY",
    "UI_USERNAME",
    "UI_PASSWORD",
    "POSTGRES_PASSWORD",
}
STACK_PROXY_TESTS = {
    "test_litellm_and_db_are_running",
    "test_db_is_healthy",
    "test_proxy_reports_ready",
    "test_missing_key_gets_401",
    "test_wrong_key_gets_401",
    "test_master_key_is_not_refused",
    "test_master_key_has_sk_prefix",
    "test_ui_page_is_served",
    "test_proxy_port_is_loopback_only",
    "test_compose_refuses_an_empty_env",
}


# ---------------------------------------------------------------- helpers


def _git(repo_root, *args, extra_config=()):
    cmd = ["git"]
    for item in extra_config:
        cmd += ["-c", item]
    cmd += list(args)
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)


def _assert_committed_gitignore_rule(repo_root, path, extra_config=()):
    tracked = _git(repo_root, "ls-files", "--error-unmatch", ".gitignore")
    assert tracked.returncode == 0, ".gitignore is not tracked by git"
    quiet = _git(repo_root, "check-ignore", "-q", "--no-index", path, extra_config=extra_config)
    assert quiet.returncode == 0, f"{path} is not ignored by git"
    verbose = _git(repo_root, "check-ignore", "-v", "--no-index", path, extra_config=extra_config)
    assert verbose.returncode == 0, f"git check-ignore -v found no rule for {path}"
    # Output: <source>:<line>:<pattern>\t<path>
    rule = verbose.stdout.strip().split("\t", 1)[0]
    source, _, rest = rule.partition(":")
    _, _, pattern = rest.partition(":")
    assert source == ".gitignore", (
        f"the rule that ignores {path} comes from {source!r}, not the committed .gitignore"
    )
    assert not pattern.startswith("!"), f"the deciding .gitignore rule for {path} is a negation"


def _services(compose) -> dict:
    services = compose.get("services")
    assert isinstance(services, dict), "compose.yaml has no services mapping"
    return services


def _service(compose, name) -> dict:
    services = _services(compose)
    assert name in services, f"compose.yaml defines no service {name!r}"
    service = services[name]
    return service if isinstance(service, dict) else {}


def _environment(service) -> dict:
    """A service's environment as a dict; a list entry without `=` maps to None."""
    env = service.get("environment") or {}
    if isinstance(env, dict):
        return dict(env)
    result = {}
    for entry in env:
        name, sep, value = str(entry).partition("=")
        result[name] = value if sep else None
    return result


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


def _is_bind_source(source: str) -> bool:
    return source.startswith((".", "/", "~", "$"))


def _resolve_source(repo_root, source: str) -> pathlib.Path:
    return (repo_root / os.path.expanduser(source)).resolve()


def _normalise_port(entry):
    """Return (host_ip, published, target) for a short or long port entry."""
    if isinstance(entry, dict):
        return (
            str(entry.get("host_ip", "")),
            str(entry.get("published", "")),
            str(entry.get("target", "")),
        )
    text = str(entry).split("/", 1)[0]
    parts = text.split(":")
    if len(parts) == 3:
        return tuple(parts)
    if len(parts) == 2:
        return ("", parts[0], parts[1])
    return ("", "", parts[0])


def _decisions_text(repo_root) -> str:
    path = repo_root / DECISIONS
    assert path.is_file(), f"{DECISIONS} does not exist"
    return path.read_text(encoding="utf-8")


def _newest_verdict_tag(repo_root) -> str:
    tags = re.findall(r"^Verdict:[^\n]*\nTag:\s*(\S+)\s*$", _decisions_text(repo_root), re.M)
    if not tags:
        pytest.fail("decisions.md holds no probe verdict record (BLOCKED: the tag is not guessed)")
    return tags[-1]


def _fact_sheet_row_13(repo_root) -> tuple[str, str]:
    """(Postgres image, data directory) from the newest fact-sheet row 13."""
    rows = re.findall(r"^\s*13\.\s+Postgres\b[^\n]*$", _decisions_text(repo_root), re.M | re.I)
    if not rows:
        pytest.fail("decisions.md holds no fact-sheet row 13 (BLOCKED: not guessed)")
    quoted = re.findall(r"`([^`]+)`", rows[-1])
    images = [q for q in quoted if q.startswith("postgres:")]
    paths = [q for q in quoted if q.startswith("/")]
    if not images or not paths:
        pytest.fail("fact-sheet row 13 names no Postgres tag or no data directory")
    return images[0], paths[0]


def _env_example_lines(repo_root) -> list[str]:
    path = repo_root / "env.example"
    assert path.is_file(), "env.example does not exist"
    return path.read_text(encoding="utf-8").splitlines()


def _env_example_entries(repo_root) -> list[tuple[int, str, str]]:
    """(line index, name, value with surrounding quotes removed) per definition."""
    entries = []
    for index, raw in enumerate(_env_example_lines(repo_root)):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        name, sep, value = line.partition("=")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        entries.append((index, name.strip(), value))
    return entries


def _string_values(node):
    """Every string value (never a mapping key) in a parsed YAML tree."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _string_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _string_values(item)
    elif isinstance(node, str):
        yield node


def _all_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_keys(item)


# ---------------------------------------------------------------- .gitignore


def test_ac1_env_is_ignored_by_a_committed_gitignore_rule(repo_root):
    """AC1: `git check-ignore -v .env` names a rule from the committed `.gitignore`."""
    _assert_committed_gitignore_rule(repo_root, ".env")


def test_ac1_edge_personal_exclude_rule_does_not_satisfy_it(repo_root, tmp_path):
    """AC1 edge case: a personal exclude rule for `.env` is not the committed rule.

    With `.env` also excluded through the person's own exclude file, git must
    still name the committed `.gitignore` as the rule that ignores `.env`.
    """
    personal = tmp_path / "exclude"
    personal.write_text(".env\n.env.local\n", encoding="utf-8")
    _assert_committed_gitignore_rule(
        repo_root, ".env", extra_config=(f"core.excludesFile={personal}",)
    )


def test_ac2_env_local_is_ignored_by_a_committed_gitignore_rule(repo_root):
    """AC2: `git check-ignore -v .env.local` names a rule from the committed `.gitignore`."""
    _assert_committed_gitignore_rule(repo_root, ".env.local")


def test_ac3_env_example_exists_and_is_not_ignored(repo_root):
    """AC3: `git check-ignore env.example` reports the committed example file as not ignored."""
    assert (repo_root / "env.example").is_file(), "env.example does not exist"
    result = _git(repo_root, "check-ignore", "--no-index", "env.example")
    assert result.returncode == 1, "git reports env.example as ignored"
    assert result.stdout.strip() == ""


# ---------------------------------------------------------------- compose.yaml


def test_ac4_compose_project_name(compose):
    """AC4: the top-level `name` of `compose.yaml` is `data-visualization-agent`."""
    assert compose.get("name") == "data-visualization-agent"


def test_ac5_compose_defines_litellm_and_db(compose):
    """AC5: `compose.yaml` defines `litellm` and `db` (other services are allowed)."""
    services = _services(compose)
    assert {"litellm", "db"} <= set(services)


def test_ac6_pgdata_volume_declared_and_mounted_by_db_only(compose, repo_root):
    """AC6: `litellm_pgdata` is declared, mounted by `db` at row 13's data directory, by no other service."""
    _, data_dir = _fact_sheet_row_13(repo_root)
    declared = compose.get("volumes") or {}
    assert "litellm_pgdata" in declared, "named volume litellm_pgdata is not declared"
    db_targets = [t for s, t, _ in _volume_mounts(_service(compose, "db")) if s == "litellm_pgdata"]
    assert db_targets == [data_dir], f"db mounts litellm_pgdata at {db_targets}, expected {data_dir}"
    others = sorted(
        name
        for name, service in _services(compose).items()
        if name != "db"
        and any(s == "litellm_pgdata" for s, _, _ in _volume_mounts(service or {}))
    )
    assert others == [], f"litellm_pgdata is also mounted by {others}"


def test_ac7_only_published_port_is_loopback_4000_on_litellm(compose):
    """AC7: across all services the only published port is `127.0.0.1:4000:4000`, on `litellm`."""
    published = [
        (name, _normalise_port(entry))
        for name, service in _services(compose).items()
        for entry in ((service or {}).get("ports") or [])
    ]
    assert published == [("litellm", ("127.0.0.1", "4000", "4000"))]


def test_ac8_litellm_image_is_pinned_to_the_verdict_tag(compose, repo_root):
    """AC8: the `litellm` image is `ghcr.io/berriai/litellm:<Tag>` of the newest verdict record."""
    tag = _newest_verdict_tag(repo_root)
    assert _service(compose, "litellm").get("image") == f"ghcr.io/berriai/litellm:{tag}"


def test_ac9_db_image_is_the_postgres_tag_of_row_13(compose, repo_root):
    """AC9: the `db` image is exactly the Postgres tag of fact-sheet row 13."""
    image, _ = _fact_sheet_row_13(repo_root)
    assert _service(compose, "db").get("image") == image


def test_ac10_every_interpolation_requires_its_variable(compose):
    """AC10: every `${...}` (and any bare `$NAME`) in compose.yaml has the form `${NAME:?message}`."""
    values = list(_string_values(compose))
    found = 0
    bad = []
    for value in values:
        text = value.replace("$$", "")
        good = re.findall(r"\$\{[A-Za-z_][A-Za-z0-9_]*:\?[^}]+\}", text)
        found += len(good)
        rest = re.sub(r"\$\{[A-Za-z_][A-Za-z0-9_]*:\?[^}]+\}", "", text)
        if "$" in rest:
            bad.append(value)
    assert found > 0, "compose.yaml interpolates no variable"
    assert bad == [], f"interpolations not of the form ${{NAME:?message}}: {bad}"


def test_ac11_no_env_file_and_no_bare_pass_through(compose):
    """AC11: no service has `env_file`, nor an environment entry with a name and no value."""
    services = _services(compose)
    with_env_file = sorted(n for n, s in services.items() if "env_file" in (s or {}))
    assert with_env_file == [], f"services with env_file: {with_env_file}"
    bare = sorted(
        f"{n}.{k}"
        for n, s in services.items()
        for k, v in _environment(s or {}).items()
        if v is None
    )
    assert bare == [], f"environment entries with no value: {bare}"


def test_ac12_no_mount_of_repo_root_env_or_docker_socket(compose, repo_root):
    """AC12: no service mounts the repository root, `.env` or `/var/run/docker.sock`."""
    root = repo_root.resolve()
    forbidden = []
    for name, service in _services(compose).items():
        for source, _, _ in _volume_mounts(service or {}):
            if not _is_bind_source(source):
                continue
            normalised = os.path.normpath(source)
            if normalised in ("/var/run/docker.sock", "/run/docker.sock"):
                forbidden.append((name, source))
                continue
            resolved = _resolve_source(repo_root, source)
            if resolved == root / ".env" or resolved == root or resolved in root.parents:
                forbidden.append((name, source))
    assert forbidden == [], f"forbidden mounts: {forbidden}"


def test_ac13_litellm_environment_holds_the_base_keys(compose):
    """AC13: `litellm` gets at least the four secrets and `DATABASE_URL` pointing at `db`."""
    env = _environment(_service(compose, "litellm"))
    required = {"LITELLM_MASTER_KEY", "LITELLM_SALT_KEY", "UI_USERNAME", "UI_PASSWORD", "DATABASE_URL"}
    missing = sorted(required - set(env))
    assert missing == [], f"litellm environment lacks {missing}"
    assert re.fullmatch(
        r"postgresql://litellm:\$\{POSTGRES_PASSWORD:\?[^}]+\}@db:5432/litellm",
        str(env["DATABASE_URL"]),
    ), "DATABASE_URL is not postgresql://litellm:${POSTGRES_PASSWORD:?...}@db:5432/litellm"


def test_ac14_db_environment(compose):
    """AC14: `db` gets `POSTGRES_USER=litellm`, `POSTGRES_DB=litellm` and `POSTGRES_PASSWORD`."""
    env = _environment(_service(compose, "db"))
    assert env.get("POSTGRES_USER") == "litellm"
    assert env.get("POSTGRES_DB") == "litellm"
    assert "POSTGRES_PASSWORD" in env


def test_ac15_litellm_waits_for_a_healthy_db(compose):
    """AC15: `litellm` depends on `db` with `condition: service_healthy`."""
    depends = _service(compose, "litellm").get("depends_on")
    assert isinstance(depends, dict), "litellm depends_on is not a mapping with conditions"
    assert (depends.get("db") or {}).get("condition") == "service_healthy"


def test_ac16_db_health_check_uses_pg_isready(compose):
    """AC16: `db` declares a health check whose test uses `pg_isready`."""
    healthcheck = _service(compose, "db").get("healthcheck")
    assert isinstance(healthcheck, dict), "db declares no healthcheck"
    assert not healthcheck.get("disable", False), "db healthcheck is disabled"
    test = healthcheck.get("test")
    text = " ".join(str(part) for part in test) if isinstance(test, list) else str(test or "")
    assert "pg_isready" in text


# ---------------------------------------------------------------- env.example


def test_ac17_env_example_names_equal_compose_interpolations(example_env_names, interpolated_names):
    """AC17: the names in `env.example` equal the names interpolated in `compose.yaml`."""
    assert interpolated_names, "compose.yaml interpolates no variable"
    assert example_env_names == interpolated_names


def test_ac18_env_example_includes_the_base_names(example_env_names):
    """AC18: `env.example` defines at least the five base secret names."""
    missing = sorted(BASE_SECRET_NAMES - example_env_names)
    assert missing == [], f"env.example lacks {missing}"


def test_ac19_every_name_has_a_placeholder_and_a_comment_above(repo_root):
    """AC19: every name has a non-empty placeholder value and a comment line directly above it."""
    lines = _env_example_lines(repo_root)
    entries = _env_example_entries(repo_root)
    assert entries, "env.example defines no name"
    without_value = sorted(name for _, name, value in entries if value == "")
    assert without_value == [], f"names without a placeholder value: {without_value}"
    without_comment = sorted(
        name for index, name, _ in entries if index == 0 or not lines[index - 1].strip().startswith("#")
    )
    assert without_comment == [], f"names without a comment line directly above: {without_comment}"


def test_ac20_master_key_placeholder_starts_with_sk(repo_root):
    """AC20: the `LITELLM_MASTER_KEY` placeholder starts with `sk-`."""
    values = {name: value for _, name, value in _env_example_entries(repo_root)}
    assert "LITELLM_MASTER_KEY" in values, "env.example does not define LITELLM_MASTER_KEY"
    assert values["LITELLM_MASTER_KEY"].startswith("sk-")


def test_ac21_env_example_states_the_character_rule(repo_root):
    """AC21: a comment line states that generated values use only letters, digits, `-` and `_`.

    One comment line must mention "generat(ed)", "only", "letters", "digits",
    and both the characters `-` and `_`.
    """
    comments = [line.strip().lower() for line in _env_example_lines(repo_root) if line.strip().startswith("#")]
    stating = [
        line
        for line in comments
        if all(word in line for word in ("generat", "only", "letters", "digits"))
        and "-" in line
        and "_" in line
    ]
    assert stating, "no comment line states the character rule for generated values"


def test_ac21_edge_postgres_password_placeholder_keeps_the_character_rule(repo_root):
    """AC21 edge case: `POSTGRES_PASSWORD` sits inside a URL, so its placeholder keeps the rule."""
    values = {name: value for _, name, value in _env_example_entries(repo_root)}
    assert "POSTGRES_PASSWORD" in values, "env.example does not define POSTGRES_PASSWORD"
    assert re.fullmatch(r"[A-Za-z0-9_-]+", values["POSTGRES_PASSWORD"]), (
        "the POSTGRES_PASSWORD placeholder uses a character other than letters, digits, - and _"
    )


def test_ac22_salt_key_comment_says_generated_once_never_changed(repo_root):
    """AC22: the comment directly above `LITELLM_SALT_KEY` says it is generated once and never changed."""
    lines = _env_example_lines(repo_root)
    indexes = [index for index, name, _ in _env_example_entries(repo_root) if name == "LITELLM_SALT_KEY"]
    assert indexes, "env.example does not define LITELLM_SALT_KEY"
    index = indexes[0]
    assert index > 0 and lines[index - 1].strip().startswith("#"), "no comment directly above LITELLM_SALT_KEY"
    comment = lines[index - 1].lower()
    assert "generat" in comment and "once" in comment, "the comment does not say the key is generated once"
    assert "never" in comment and "change" in comment, "the comment does not say the key is never changed"


# ---------------------------------------------------------------- shared rules


@pytest.mark.parametrize("relative", ["compose.yaml", "litellm/config.yaml", "env.example"])
def test_ac23_no_anthropic_api_key(repo_root, relative):
    """AC23: the string `ANTHROPIC_API_KEY` occurs in none of the three stack files."""
    path = repo_root / relative
    assert path.is_file(), f"{relative} does not exist"
    assert "ANTHROPIC_API_KEY" not in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- litellm/config.yaml


def test_ac24_config_is_mounted_read_only_at_the_config_path(compose, repo_root):
    """AC24: `./litellm/config.yaml` is mounted read-only at the path `command` passes to `--config`."""
    litellm = _service(compose, "litellm")
    command = litellm.get("command")
    args = shlex.split(command) if isinstance(command, str) else [str(a) for a in (command or [])]
    config_path = None
    for i, arg in enumerate(args):
        if arg == "--config" and i + 1 < len(args):
            config_path = args[i + 1]
        elif arg.startswith("--config="):
            config_path = arg.split("=", 1)[1]
    assert config_path, "the litellm command passes no --config"
    config_file = (repo_root / "litellm" / "config.yaml").resolve()
    mounts = [
        (target, read_only)
        for source, target, read_only in _volume_mounts(litellm)
        if _is_bind_source(source) and _resolve_source(repo_root, source) == config_file
    ]
    assert mounts == [(config_path, True)], (
        f"./litellm/config.yaml mounts {mounts}, expected read-only at {config_path}"
    )


def test_ac25_config_parses_as_yaml(repo_root):
    """AC25: `litellm/config.yaml` exists and parses as YAML (a mapping, or empty)."""
    path = repo_root / "litellm" / "config.yaml"
    assert path.is_file(), "litellm/config.yaml does not exist"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        pytest.fail(f"litellm/config.yaml is not valid YAML: {error}")
    assert data is None or isinstance(data, dict), "litellm/config.yaml is not a mapping"


def test_ac26_config_has_no_forwarding_system_or_user_agent_key(proxy_config):
    """AC26: no key name in `litellm/config.yaml` contains `forward`, `system`, `user-agent` or `user_agent`."""
    offending = sorted(
        key
        for key in _all_keys(proxy_config)
        if any(word in key.lower() for word in ("forward", "system", "user-agent", "user_agent"))
    )
    assert offending == [], f"forbidden key names: {offending}"


def test_ac27_config_never_names_claude_code(repo_root):
    """AC27: apart from `CLAUDE_CODE_OAUTH_TOKEN`, the config names no Claude Code client, in any case."""
    path = repo_root / "litellm" / "config.yaml"
    assert path.is_file(), "litellm/config.yaml does not exist"
    text = re.sub("claude_code_oauth_token", "", path.read_text(encoding="utf-8"), flags=re.I).lower()
    found = [word for word in ("claude code", "claude-code", "claude_code", "claude-cli") if word in text]
    assert found == [], f"litellm/config.yaml contains {found}"


# ---------------------------------------------------------------- stack suite contract


def test_ac28_stack_proxy_tests_are_skipped_without_stack_tests(repo_root, tmp_path):
    """AC28: without `STACK_TESTS`, `tests/stack/test_proxy.py` exits 0, runs nothing, skips the ten tests.

    Each contract test must be collected and reported as skipped under its own
    name, so the module-level skip is a `pytestmark`, not a module skip.
    """
    module = repo_root / "tests" / "stack" / "test_proxy.py"
    assert module.is_file(), "tests/stack/test_proxy.py does not exist"
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
            "tests/stack/test_proxy.py",
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"pytest exited {result.returncode}"
    assert report.is_file(), "pytest wrote no report"
    cases = ET.parse(report).getroot().iter("testcase")
    outcomes = {}
    for case in cases:
        children = {child.tag for child in case}
        if "skipped" in children:
            outcomes[case.get("name")] = "skipped"
        elif children & {"failure", "error"}:
            outcomes[case.get("name")] = "failed"
        else:
            outcomes[case.get("name")] = "ran"
    ran = sorted(name for name, outcome in outcomes.items() if outcome != "skipped")
    assert ran == [], f"tests that ran without STACK_TESTS: {ran}"
    missing = sorted(STACK_PROXY_TESTS - {n for n, o in outcomes.items() if o == "skipped"})
    assert missing == [], f"contract tests not reported as skipped: {missing}"
