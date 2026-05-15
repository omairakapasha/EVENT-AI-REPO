"""
Shared fixtures for Docker structural assertion tests.

Provides:
  - SERVICES: mapping of service name → paths
  - dockerfile_text(service): full Dockerfile content
  - runner_stage_text(service): only the final FROM...AS runner stage
  - compose_config: parsed docker-compose.yml dict
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

# ── Service registry ──────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent.parent

SERVICES: dict[str, dict[str, Path]] = {
    "backend": {
        "package_dir": REPO_ROOT / "packages" / "backend",
        "dockerfile": REPO_ROOT / "packages" / "backend" / "Dockerfile",
        "dockerignore": REPO_ROOT / "packages" / "backend" / ".dockerignore",
        "runtime": "python",
    },
    "orchestrator": {
        "package_dir": REPO_ROOT / "packages" / "agentic_event_orchestrator",
        "dockerfile": REPO_ROOT / "packages" / "agentic_event_orchestrator" / "Dockerfile",
        "dockerignore": REPO_ROOT / "packages" / "agentic_event_orchestrator" / ".dockerignore",
        "runtime": "python",
    },
    "vendor": {
        "package_dir": REPO_ROOT / "packages" / "vendor",
        "dockerfile": REPO_ROOT / "packages" / "vendor" / "Dockerfile",
        "dockerignore": REPO_ROOT / "packages" / "vendor" / ".dockerignore",
        "runtime": "node",
    },
    "user": {
        "package_dir": REPO_ROOT / "packages" / "user",
        "dockerfile": REPO_ROOT / "packages" / "user" / "Dockerfile",
        "dockerignore": REPO_ROOT / "packages" / "user" / ".dockerignore",
        "runtime": "node",
    },
    "admin": {
        "package_dir": REPO_ROOT / "packages" / "admin",
        "dockerfile": REPO_ROOT / "packages" / "admin" / "Dockerfile",
        "dockerignore": REPO_ROOT / "packages" / "admin" / ".dockerignore",
        "runtime": "node",
    },
}

PYTHON_SERVICES = [name for name, info in SERVICES.items() if info["runtime"] == "python"]
NODE_SERVICES = [name for name, info in SERVICES.items() if info["runtime"] == "node"]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def all_dockerfile_texts() -> dict[str, str]:
    """Read all Dockerfiles once per session."""
    return {
        name: info["dockerfile"].read_text()
        for name, info in SERVICES.items()
    }


@pytest.fixture(scope="session")
def all_runner_stage_texts(all_dockerfile_texts: dict[str, str]) -> dict[str, str]:
    """
    Extract only the final stage (runner) from each Dockerfile.
    The runner stage is everything from the last FROM line to EOF.
    """
    result: dict[str, str] = {}
    for name, text in all_dockerfile_texts.items():
        # Split on FROM lines; the last chunk is the runner stage
        stages = re.split(r"(?m)^FROM\s", text)
        # Re-attach the FROM keyword to each stage (except the empty first split)
        runner_stage = "FROM " + stages[-1] if len(stages) > 1 else text
        result[name] = runner_stage
    return result


@pytest.fixture(scope="session")
def all_dockerignore_texts() -> dict[str, str]:
    """Read all .dockerignore files once per session."""
    return {
        name: info["dockerignore"].read_text()
        for name, info in SERVICES.items()
    }


@pytest.fixture(scope="session")
def compose_config() -> dict:
    """Parse docker-compose.yml at the repo root."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    with compose_path.open() as f:
        return yaml.safe_load(f)
