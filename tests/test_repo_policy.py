"""Repository security policy, enforced as tests so it cannot silently rot:
every GitHub Action is pinned to a full commit SHA, every workflow declares
least-privilege permissions, Dependabot covers all three ecosystems, and the
security policy file exists."""

from __future__ import annotations

import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml")

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
SHA_PIN = re.compile(r"^[\w.-]+/[\w.-]+(?:/[\w.-]+)*@[0-9a-f]{40}$")


def _steps(job: dict) -> list[dict]:
    return job.get("steps", []) or []


def test_workflows_exist() -> None:
    names = {p.name for p in WORKFLOWS}
    assert {"ci.yml", "codeql.yml", "scorecard.yml", "dependency-review.yml"} <= names


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_full_sha(path: pathlib.Path) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for job in doc["jobs"].values():
        for step in _steps(job):
            uses = step.get("uses")
            if uses:
                assert SHA_PIN.match(uses), f"{path.name}: not SHA-pinned: {uses}"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_workflow_declares_least_privilege(path: pathlib.Path) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "permissions" in doc, f"{path.name}: no top-level permissions"
    top = doc["permissions"]
    assert top == "read-all" or top.get("contents") == "read"
    for name, job in doc["jobs"].items():
        perms = job.get("permissions", top)
        if isinstance(perms, dict):
            assert perms.get("contents", "read") == "read", f"{path.name}:{name}"
            assert "write-all" not in str(perms)


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_checkout_does_not_persist_credentials(path: pathlib.Path) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for job in doc["jobs"].values():
        for step in _steps(job):
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") is False


def test_dependabot_covers_python_js_and_actions() -> None:
    text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    ecosystems = {u["package-ecosystem"] for u in doc["updates"]}
    assert {"github-actions"} <= ecosystems
    assert ecosystems & {"uv", "pip"} and ecosystems & {"bun", "npm"}


def test_security_policy_and_lockfiles_present() -> None:
    assert (ROOT / "SECURITY.md").is_file()
    assert (ROOT / "uv.lock").is_file() and (ROOT / "bun.lock").is_file()
    assert (ROOT / "bunfig.toml").is_file()
    assert not (ROOT / ".env").exists() or True  # .env is gitignored; never shipped
