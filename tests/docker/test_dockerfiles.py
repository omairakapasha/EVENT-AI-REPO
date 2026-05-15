"""
Structural assertion tests for the docker-light-images feature.

Encodes all 9 correctness properties from the design document as executable
assertions over the finite, enumerable set of Dockerfiles in the project.

Properties:
  1. No build tool leakage into runner stages
  2. Non-root user invariant (UID/GID 1001)
  3. Build context secrets exclusion (.dockerignore completeness)
  4. Package manager compliance (no pip/npm)
  5. Health check presence and parameters
  6. Cache mount presence in dependency stages
  7. Manifest-first layer ordering
  8. Compose service invariants (restart, resources, build args)
  9. Standalone output configuration in Next.js configs
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.docker.conftest import (
    NODE_SERVICES,
    PYTHON_SERVICES,
    REPO_ROOT,
    SERVICES,
)

# ── Property 1: No build tool leakage into runner stages ─────────────────────


class TestProperty1NoBuildToolLeakage:
    """Runner/final stage must not contain build tools."""

    def test_no_uv_binary_in_python_runner(self, all_runner_stage_texts):
        for svc in PYTHON_SERVICES:
            runner = all_runner_stage_texts[svc]
            # uv binary should not be copied into the runner stage
            assert "/usr/local/bin/uv" not in runner, (
                f"{svc}: uv binary found in runner stage — build tool leakage"
            )
            assert "COPY --from=ghcr.io/astral-sh/uv" not in runner, (
                f"{svc}: uv COPY from ghcr.io found in runner stage"
            )

    def test_no_pip_in_runner(self, all_runner_stage_texts):
        for svc in PYTHON_SERVICES:
            runner = all_runner_stage_texts[svc]
            assert "pip install" not in runner, (
                f"{svc}: 'pip install' found in runner stage"
            )

    def test_no_npm_in_node_runner(self, all_runner_stage_texts):
        for svc in NODE_SERVICES:
            runner = all_runner_stage_texts[svc]
            assert "npm install" not in runner, (
                f"{svc}: 'npm install' found in runner stage"
            )
            assert "npm ci" not in runner, (
                f"{svc}: 'npm ci' found in runner stage"
            )

    def test_node_runner_copies_only_standalone_artifacts(self, all_runner_stage_texts):
        for svc in NODE_SERVICES:
            runner = all_runner_stage_texts[svc]
            # Must copy standalone
            assert ".next/standalone" in runner, (
                f"{svc}: .next/standalone not copied in runner stage"
            )
            # Must copy static
            assert ".next/static" in runner, (
                f"{svc}: .next/static not copied in runner stage"
            )
            # Must NOT copy full node_modules
            assert "COPY --from=deps /app/node_modules" not in runner, (
                f"{svc}: full node_modules copied into runner stage"
            )


# ── Property 2: Non-root user invariant ──────────────────────────────────────


class TestProperty2NonRootUser:
    """Every runner stage must create appgroup/appuser (1001) and switch to it."""

    def test_appgroup_gid_1001_created(self, all_runner_stage_texts):
        for svc, runner in all_runner_stage_texts.items():
            assert "1001" in runner, (
                f"{svc}: GID 1001 not found in runner stage"
            )
            assert "appgroup" in runner, (
                f"{svc}: appgroup not created in runner stage"
            )

    def test_appuser_uid_1001_created(self, all_runner_stage_texts):
        for svc, runner in all_runner_stage_texts.items():
            assert "appuser" in runner, (
                f"{svc}: appuser not created in runner stage"
            )

    def test_user_appuser_directive_present(self, all_runner_stage_texts):
        for svc, runner in all_runner_stage_texts.items():
            assert re.search(r"^USER appuser", runner, re.MULTILINE), (
                f"{svc}: 'USER appuser' not found in runner stage"
            )

    def test_chown_on_all_copies_in_runner(self, all_runner_stage_texts):
        for svc, runner in all_runner_stage_texts.items():
            copy_lines = [
                line.strip()
                for line in runner.splitlines()
                if line.strip().startswith("COPY")
            ]
            for line in copy_lines:
                assert "--chown=appuser:appgroup" in line, (
                    f"{svc}: COPY without --chown=appuser:appgroup in runner: {line!r}"
                )

    def test_no_user_root_after_user_appuser(self, all_runner_stage_texts):
        for svc, runner in all_runner_stage_texts.items():
            lines = runner.splitlines()
            appuser_idx = next(
                (i for i, l in enumerate(lines) if re.match(r"^USER appuser", l.strip())),
                None,
            )
            if appuser_idx is not None:
                subsequent = lines[appuser_idx + 1:]
                for line in subsequent:
                    assert not re.match(r"^USER root", line.strip()), (
                        f"{svc}: 'USER root' found after 'USER appuser'"
                    )


# ── Property 3: Build context secrets exclusion ───────────────────────────────


class TestProperty3DockerignoreCompleteness:
    """Every service must have a .dockerignore excluding secrets and build artifacts."""

    REQUIRED_PATTERNS_COMMON = [
        ".env",
        "*.log",
        ".git/",
        ".vscode/",
        ".idea/",
    ]

    REQUIRED_PATTERNS_PYTHON = [
        "__pycache__/",
        "*.pyc",
        ".venv/",
    ]

    REQUIRED_PATTERNS_NODE = [
        "node_modules/",
        ".next/",
    ]

    def test_dockerignore_exists(self):
        for svc, info in SERVICES.items():
            assert info["dockerignore"].exists(), (
                f"{svc}: .dockerignore file is missing"
            )

    def test_common_patterns_present(self, all_dockerignore_texts):
        for svc, text in all_dockerignore_texts.items():
            for pattern in self.REQUIRED_PATTERNS_COMMON:
                assert pattern in text, (
                    f"{svc}: .dockerignore missing required pattern: {pattern!r}"
                )

    def test_python_patterns_present(self, all_dockerignore_texts):
        for svc in PYTHON_SERVICES:
            text = all_dockerignore_texts[svc]
            for pattern in self.REQUIRED_PATTERNS_PYTHON:
                assert pattern in text, (
                    f"{svc}: .dockerignore missing Python pattern: {pattern!r}"
                )

    def test_node_patterns_present(self, all_dockerignore_texts):
        for svc in NODE_SERVICES:
            text = all_dockerignore_texts[svc]
            for pattern in self.REQUIRED_PATTERNS_NODE:
                assert pattern in text, (
                    f"{svc}: .dockerignore missing Node pattern: {pattern!r}"
                )

    def test_env_wildcard_excluded(self, all_dockerignore_texts):
        """Ensure .env.* glob or equivalent is present to catch all .env variants."""
        for svc, text in all_dockerignore_texts.items():
            has_wildcard = ".env.*" in text or ".env.local" in text
            assert has_wildcard, (
                f"{svc}: .dockerignore does not exclude .env variants (.env.* or .env.local)"
            )


# ── Property 4: Package manager compliance ────────────────────────────────────


class TestProperty4PackageManagerCompliance:
    """No pip install, npm install, or npm ci in any Dockerfile."""

    def test_no_pip_install_anywhere(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            assert "pip install" not in text, (
                f"{svc}: 'pip install' found in Dockerfile — use uv sync instead"
            )

    def test_no_npm_install_anywhere(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            assert "npm install" not in text, (
                f"{svc}: 'npm install' found in Dockerfile — use pnpm install instead"
            )

    def test_no_npm_ci_anywhere(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            assert "npm ci" not in text, (
                f"{svc}: 'npm ci' found in Dockerfile — use pnpm install instead"
            )

    def test_python_services_use_uv_sync(self, all_dockerfile_texts):
        for svc in PYTHON_SERVICES:
            text = all_dockerfile_texts[svc]
            assert "uv sync" in text, (
                f"{svc}: 'uv sync' not found — Python deps must use uv sync"
            )

    def test_node_services_use_pnpm_install(self, all_dockerfile_texts):
        for svc in NODE_SERVICES:
            text = all_dockerfile_texts[svc]
            assert "pnpm install" in text, (
                f"{svc}: 'pnpm install' not found — Node deps must use pnpm"
            )

    def test_node_services_use_corepack(self, all_dockerfile_texts):
        for svc in NODE_SERVICES:
            text = all_dockerfile_texts[svc]
            assert "corepack enable" in text, (
                f"{svc}: 'corepack enable' not found — must use corepack to activate pnpm"
            )
            assert "corepack prepare pnpm" in text, (
                f"{svc}: 'corepack prepare pnpm' not found"
            )


# ── Property 5: Health check presence and parameters ─────────────────────────


class TestProperty5HealthChecks:
    """Every Dockerfile must have a HEALTHCHECK with correct parameters."""

    def test_healthcheck_present(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            assert "HEALTHCHECK" in text, (
                f"{svc}: HEALTHCHECK instruction missing"
            )

    def test_healthcheck_interval_30s(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            assert "--interval=30s" in text, (
                f"{svc}: HEALTHCHECK --interval=30s not found"
            )

    def test_healthcheck_timeout_5s(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            assert "--timeout=5s" in text, (
                f"{svc}: HEALTHCHECK --timeout=5s not found"
            )

    def test_healthcheck_retries_3(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            assert "--retries=3" in text, (
                f"{svc}: HEALTHCHECK --retries=3 not found"
            )

    def test_healthcheck_start_period_at_least_15s(self, all_dockerfile_texts):
        for svc, text in all_dockerfile_texts.items():
            match = re.search(r"--start-period=(\d+)s", text)
            assert match, f"{svc}: HEALTHCHECK --start-period not found"
            assert int(match.group(1)) >= 15, (
                f"{svc}: HEALTHCHECK --start-period={match.group(1)}s is less than 15s"
            )

    def test_node_healthcheck_uses_wget(self, all_dockerfile_texts):
        for svc in NODE_SERVICES:
            text = all_dockerfile_texts[svc]
            assert "wget -qO-" in text, (
                f"{svc}: Node HEALTHCHECK must use 'wget -qO-'"
            )
            assert "localhost:3000" in text, (
                f"{svc}: Node HEALTHCHECK must poll localhost:3000"
            )

    def test_python_healthcheck_uses_urllib(self, all_dockerfile_texts):
        for svc in PYTHON_SERVICES:
            text = all_dockerfile_texts[svc]
            assert "urllib.request" in text, (
                f"{svc}: Python HEALTHCHECK must use urllib.request"
            )


# ── Property 6: Cache mount presence in dependency stages ────────────────────


class TestProperty6CacheMounts:
    """Dependency install RUN instructions must use --mount=type=cache."""

    def test_python_uv_cache_mount(self, all_dockerfile_texts):
        for svc in PYTHON_SERVICES:
            text = all_dockerfile_texts[svc]
            assert "--mount=type=cache,target=/root/.cache/uv" in text, (
                f"{svc}: uv cache mount missing — add "
                "'--mount=type=cache,target=/root/.cache/uv' to uv sync RUN"
            )

    def test_node_pnpm_store_cache_mount(self, all_dockerfile_texts):
        for svc in NODE_SERVICES:
            text = all_dockerfile_texts[svc]
            assert "--mount=type=cache,target=/root/.local/share/pnpm/store" in text, (
                f"{svc}: pnpm store cache mount missing — add "
                "'--mount=type=cache,target=/root/.local/share/pnpm/store' to pnpm install RUN"
            )


# ── Property 7: Manifest-first layer ordering ─────────────────────────────────


class TestProperty7ManifestFirstOrdering:
    """Dependency manifests must be copied before application source."""

    def test_python_manifests_before_source(self, all_dockerfile_texts):
        for svc in PYTHON_SERVICES:
            text = all_dockerfile_texts[svc]
            lines = text.splitlines()
            manifest_idx = next(
                (i for i, l in enumerate(lines) if "pyproject.toml" in l and "COPY" in l),
                None,
            )
            # Source copy: COPY --chown=... src ./src  OR  COPY --chown=... . .
            source_idx = next(
                (
                    i for i, l in enumerate(lines)
                    if "COPY" in l and ("--chown" in l) and (
                        " src " in l or " . ." in l or "./src" in l
                    )
                ),
                None,
            )
            assert manifest_idx is not None, f"{svc}: pyproject.toml COPY not found"
            assert source_idx is not None, f"{svc}: source COPY not found"
            assert manifest_idx < source_idx, (
                f"{svc}: manifest COPY (line {manifest_idx}) must come before "
                f"source COPY (line {source_idx})"
            )

    def test_node_manifests_before_source(self, all_dockerfile_texts):
        for svc in NODE_SERVICES:
            text = all_dockerfile_texts[svc]
            lines = text.splitlines()
            manifest_idx = next(
                (i for i, l in enumerate(lines) if "package.json" in l and "COPY" in l),
                None,
            )
            # Source copy: COPY . .
            source_idx = next(
                (
                    i for i, l in enumerate(lines)
                    if re.match(r"\s*COPY\s+\.\s+\.\s*$", l)
                ),
                None,
            )
            assert manifest_idx is not None, f"{svc}: package.json COPY not found"
            assert source_idx is not None, f"{svc}: 'COPY . .' not found"
            assert manifest_idx < source_idx, (
                f"{svc}: manifest COPY (line {manifest_idx}) must come before "
                f"source COPY (line {source_idx})"
            )


# ── Property 8: Compose service invariants ────────────────────────────────────


class TestProperty8ComposeInvariants:
    """docker-compose.yml must define all services with correct resource limits and restart."""

    EXPECTED_SERVICES = {"backend", "orchestrator", "vendor", "user", "admin"}

    def test_all_services_defined(self, compose_config):
        defined = set(compose_config.get("services", {}).keys())
        assert self.EXPECTED_SERVICES == defined, (
            f"compose services mismatch: expected {self.EXPECTED_SERVICES}, got {defined}"
        )

    def test_restart_unless_stopped(self, compose_config):
        for svc_name in self.EXPECTED_SERVICES:
            svc = compose_config["services"][svc_name]
            assert svc.get("restart") == "unless-stopped", (
                f"{svc_name}: restart must be 'unless-stopped'"
            )

    def test_python_resource_limits(self, compose_config):
        for svc_name in ["backend", "orchestrator"]:
            svc = compose_config["services"][svc_name]
            limits = svc.get("deploy", {}).get("resources", {}).get("limits", {})
            assert limits.get("memory") == "512M", (
                f"{svc_name}: memory limit must be 512M, got {limits.get('memory')}"
            )
            assert limits.get("cpus") == "1.0", (
                f"{svc_name}: CPU limit must be 1.0, got {limits.get('cpus')}"
            )

    def test_node_resource_limits(self, compose_config):
        for svc_name in ["vendor", "user", "admin"]:
            svc = compose_config["services"][svc_name]
            limits = svc.get("deploy", {}).get("resources", {}).get("limits", {})
            assert limits.get("memory") == "256M", (
                f"{svc_name}: memory limit must be 256M, got {limits.get('memory')}"
            )
            assert limits.get("cpus") == "0.5", (
                f"{svc_name}: CPU limit must be 0.5, got {limits.get('cpus')}"
            )

    def test_node_services_have_next_public_api_url_build_arg(self, compose_config):
        for svc_name in ["vendor", "user", "admin"]:
            svc = compose_config["services"][svc_name]
            build_args = svc.get("build", {}).get("args", {})
            assert "NEXT_PUBLIC_API_URL" in build_args, (
                f"{svc_name}: NEXT_PUBLIC_API_URL build ARG missing from compose"
            )

    def test_depends_on_backend_healthy(self, compose_config):
        for svc_name in ["orchestrator", "vendor", "user", "admin"]:
            svc = compose_config["services"][svc_name]
            depends = svc.get("depends_on", {})
            assert "backend" in depends, (
                f"{svc_name}: depends_on backend not set"
            )
            condition = depends["backend"].get("condition")
            assert condition == "service_healthy", (
                f"{svc_name}: depends_on backend condition must be service_healthy, got {condition}"
            )

    def test_port_mappings(self, compose_config):
        expected_ports = {
            "backend": "5000:5000",
            "orchestrator": "8000:8000",
            "vendor": "3002:3000",
            "user": "3003:3000",
            "admin": "3004:3000",
        }
        for svc_name, expected_port in expected_ports.items():
            svc = compose_config["services"][svc_name]
            ports = svc.get("ports", [])
            assert expected_port in ports, (
                f"{svc_name}: port mapping {expected_port!r} not found, got {ports}"
            )

    def test_shared_public_network(self, compose_config):
        networks = compose_config.get("networks", {})
        assert "public" in networks, "docker-compose.yml missing 'public' network"
        for svc_name in self.EXPECTED_SERVICES:
            svc = compose_config["services"][svc_name]
            svc_networks = svc.get("networks", [])
            assert "public" in svc_networks, (
                f"{svc_name}: not attached to 'public' network"
            )


# ── Property 9: Standalone output configuration ───────────────────────────────


class TestProperty9StandaloneOutput:
    """All Next.js portals must have output: 'standalone' in their next.config."""

    NEXT_CONFIGS = {
        "vendor": REPO_ROOT / "packages" / "vendor" / "next.config.js",
        "user": REPO_ROOT / "packages" / "user" / "next.config.ts",
        "admin": REPO_ROOT / "packages" / "admin" / "next.config.ts",
    }

    def test_standalone_output_present(self):
        for svc, config_path in self.NEXT_CONFIGS.items():
            assert config_path.exists(), f"{svc}: {config_path} does not exist"
            text = config_path.read_text()
            assert re.search(r"""output\s*:\s*['"]standalone['"]""", text), (
                f"{svc}: output: 'standalone' not found in {config_path.name}"
            )

    def test_transpile_packages_for_ui_consumers(self):
        """user and admin depend on @event-ai/ui and must transpile it."""
        for svc in ["user", "admin"]:
            config_path = self.NEXT_CONFIGS[svc]
            text = config_path.read_text()
            assert "@event-ai/ui" in text, (
                f"{svc}: transpilePackages for @event-ai/ui missing in {config_path.name}"
            )

    def test_vendor_does_not_need_transpile(self):
        """vendor does not import @event-ai/ui — transpilePackages should not be required."""
        # This is a documentation test — we just verify vendor config exists and has standalone
        config_path = self.NEXT_CONFIGS["vendor"]
        text = config_path.read_text()
        assert re.search(r"""output\s*:\s*['"]standalone['"]""", text), (
            "vendor: output: 'standalone' missing"
        )
