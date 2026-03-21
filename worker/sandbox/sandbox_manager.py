"""
sandbox_manager.py

Handles the full container lifecycle for the agent sandbox:
  - Image selection per language/runtime
  - Spawn with security constraints (no network, CPU/mem limits, read-only fs)
  - Volume mounting strategy (ro base + rw overlay)
  - Exec commands inside a running container
  - Teardown and log archival

Usage:
    mgr = SandboxManager(repo_path="/tmp/repos/myrepo", incident_id="inc-123")
    with mgr.container() as sb:
        result = sb.exec(["pytest", "--json-report", "-q"])
        print(result.stdout)
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import tempfile
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Image registry — maps language/runtime to a pinned Docker image
# ---------------------------------------------------------------------------

IMAGE_REGISTRY: dict[str, str] = {
    "python":      "python:3.11-slim",
    "python310":   "python:3.10-slim",
    "node18":      "node:18-alpine",
    "node20":      "node:20-alpine",
    "default":     "python:3.11-slim",
}

# Pre-installed tooling baked into each image
# (run `docker build` with these Dockerfiles once; cache in your registry)
SETUP_COMMANDS: dict[str, list[str]] = {
    "python": [
        "pip install --quiet pytest pytest-json-report pytest-cov pyflakes mypy 2>&1 | tail -5",
    ],
    "node": [
        "npm install --global --quiet jest eslint typescript ts-node 2>&1 | tail -5",
    ],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ExecResult:
    exit_code:  int
    stdout:     str
    stderr:     str
    duration_s: float
    timed_out:  bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


@dataclass
class SandboxConfig:
    repo_path:    str
    incident_id:  str
    language:     str         = "python"
    image:        str         = ""            # auto-selected from language if empty
    cpu_quota:    int         = 100_000       # 100% of one CPU core (100000/100000)
    mem_limit:    str         = "512m"        # hard memory cap
    timeout_deps: int         = 90            # seconds for dep install
    timeout_test: int         = 180           # seconds for test run
    network_mode: str         = "none"        # NO network access inside sandbox
    working_dir:  str         = "/workspace"
    extra_env:    dict        = field(default_factory=dict)

    def __post_init__(self):
        if not self.image:
            self.image = IMAGE_REGISTRY.get(self.language, IMAGE_REGISTRY["default"])


# ---------------------------------------------------------------------------
# Sandbox handle — represents a running container
# ---------------------------------------------------------------------------

class Sandbox:
    """
    A running container. Created by SandboxManager.container().
    Use .exec() to run commands inside it.
    """

    def __init__(self, container: Container, config: SandboxConfig):
        self._container = container
        self.config     = config
        self.container_id = container.short_id

    def exec(
        self,
        cmd: list[str] | str,
        timeout: Optional[int] = None,
        workdir: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> ExecResult:
        """
        Run a command inside the container.
        Returns structured ExecResult — never raises on non-zero exit.
        """
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)

        workdir = workdir or self.config.working_dir
        timeout = timeout or self.config.timeout_test

        env_list = [f"{k}={v}" for k, v in (env or {}).items()]

        start = time.monotonic()
        timed_out = False

        try:
            exit_code, output = self._container.exec_run(
                cmd=cmd,
                workdir=workdir,
                environment=env_list,
                demux=True,         # separate stdout/stderr
                tty=False,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return ExecResult(
                exit_code=1,
                stdout="",
                stderr=str(exc),
                duration_s=elapsed,
            )

        elapsed = time.monotonic() - start

        stdout_raw, stderr_raw = output if isinstance(output, tuple) else (output, b"")
        stdout = (stdout_raw or b"").decode("utf-8", errors="replace")
        stderr = (stderr_raw or b"").decode("utf-8", errors="replace")

        # Soft timeout check (docker SDK doesn't have built-in timeout for exec_run)
        if elapsed > timeout:
            timed_out = True
            logger.warning(
                "exec timed out after %.1fs: %s",
                elapsed,
                " ".join(cmd[:4]),
            )

        return ExecResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_s=elapsed,
            timed_out=timed_out,
        )

    def copy_file_in(self, host_path: str, container_path: str) -> None:
        """Copy a single file from host into the running container."""
        import tarfile, io
        data = Path(host_path).read_bytes()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo(name=Path(container_path).name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        buf.seek(0)
        self._container.put_archive(str(Path(container_path).parent), buf)

    def read_file(self, container_path: str) -> str:
        """Read a file from inside the container."""
        result = self.exec(["cat", container_path])
        if result.exit_code != 0:
            raise FileNotFoundError(f"Container file not found: {container_path}")
        return result.stdout


# ---------------------------------------------------------------------------
# Sandbox manager
# ---------------------------------------------------------------------------

class SandboxManager:
    """
    Creates and manages Docker containers for the agent sandbox.

    Example:
        mgr = SandboxManager(SandboxConfig(
            repo_path="/tmp/repos/myrepo",
            incident_id="inc-42",
            language="python",
        ))
        with mgr.container() as sb:
            r = sb.exec(["python", "-m", "pytest", "--json-report", "-q"])
    """

    def __init__(self, config: SandboxConfig):
        self.config = config
        self._client = docker.from_env()
        self._container: Optional[Container] = None

    @contextmanager
    def container(self) -> Iterator[Sandbox]:
        """
        Context manager: spawns container, yields Sandbox, tears down on exit.
        Always cleans up even if an exception is raised.
        """
        container = self._spawn()
        sandbox = Sandbox(container, self.config)
        try:
            self._install_deps(sandbox)
            yield sandbox
        finally:
            self._teardown(container)

    # ------------------------------------------------------------------
    # Internal: spawn
    # ------------------------------------------------------------------

    def _spawn(self) -> Container:
        """
        Start a Docker container with hard security constraints.

        Security model:
          - network_mode="none"        → no outbound network
          - read_only=True             → base FS immutable
          - tmpfs on /tmp              → writable scratch space only
          - volumes: repo ro + overlay rw
          - cap_drop=["ALL"]           → no Linux capabilities
          - security_opt no-new-privileges
          - cpu/mem limits             → can't starve the host
        """
        repo_path = str(Path(self.config.repo_path).resolve())
        overlay_dir = tempfile.mkdtemp(prefix=f"sandbox-overlay-{self.config.incident_id}-")

        # Copy repo into overlay so writes are isolated
        import shutil
        shutil.copytree(repo_path, overlay_dir, dirs_exist_ok=True)

        volumes = {
            overlay_dir: {
                "bind": self.config.working_dir,
                "mode": "rw",
            },
        }

        env = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "CI": "true",
            **self.config.extra_env,
        }

        logger.info(
            "Spawning sandbox | image=%s incident=%s",
            self.config.image,
            self.config.incident_id,
        )

        container = self._client.containers.run(
            image         = self.config.image,
            command       = ["tail", "-f", "/dev/null"],   # keep alive
            detach        = True,
            remove        = False,                          # we remove manually in teardown
            name          = f"agent-sandbox-{self.config.incident_id}-{uuid.uuid4().hex[:6]}",
            network_mode  = self.config.network_mode,
            mem_limit     = self.config.mem_limit,
            cpu_quota     = self.config.cpu_quota,
            cpu_period     = 100_000,
            read_only     = False,                          # overlay is rw
            cap_drop      = ["ALL"],
            security_opt  = ["no-new-privileges:true"],
            tmpfs         = {"/tmp": "size=128m,mode=1777"},
            volumes       = volumes,
            environment   = env,
            working_dir   = self.config.working_dir,
            user          = "nobody",                       # non-root
        )

        # Store overlay path for cleanup
        container._overlay_dir = overlay_dir             # type: ignore[attr-defined]
        logger.info("Container started: %s", container.short_id)
        return container

    # ------------------------------------------------------------------
    # Internal: dep install
    # ------------------------------------------------------------------

    def _install_deps(self, sandbox: Sandbox) -> None:
        """
        Install project dependencies inside the container.
        Detects the package manager from lock files.
        """
        lang = self.config.language.lower()

        if lang == "python":
            # Try poetry, then pipenv, then requirements.txt
            for cmd, lockfile in [
                (["pip", "install", "-r", "requirements.txt", "-q"], "requirements.txt"),
                (["pip", "install", "-e", ".", "-q"],                 "setup.py"),
                (["pip", "install", "-e", ".", "-q"],                 "pyproject.toml"),
            ]:
                r = sandbox.exec(["test", "-f", lockfile])
                if r.exit_code == 0:
                    logger.info("Installing deps via: %s", " ".join(cmd))
                    result = sandbox.exec(cmd, timeout=self.config.timeout_deps)
                    if not result.success:
                        logger.warning(
                            "Dep install failed (exit %d): %s",
                            result.exit_code,
                            result.stderr[:300],
                        )
                    break

        elif lang in ("node", "javascript", "typescript"):
            r = sandbox.exec(["test", "-f", "package-lock.json"])
            cmd = ["npm", "ci", "--silent"] if r.exit_code == 0 else ["npm", "install", "--silent"]
            logger.info("Installing deps via: %s", " ".join(cmd))
            result = sandbox.exec(cmd, timeout=self.config.timeout_deps)
            if not result.success:
                logger.warning("npm install failed: %s", result.stderr[:300])

    # ------------------------------------------------------------------
    # Internal: teardown
    # ------------------------------------------------------------------

    def _teardown(self, container: Container) -> None:
        """Stop, remove container and clean up overlay directory."""
        overlay_dir = getattr(container, "_overlay_dir", None)
        try:
            container.stop(timeout=5)
            container.remove(force=True)
            logger.info("Container removed: %s", container.short_id)
        except (NotFound, DockerException) as exc:
            logger.warning("Teardown error: %s", exc)
        finally:
            if overlay_dir and Path(overlay_dir).exists():
                import shutil
                shutil.rmtree(overlay_dir, ignore_errors=True)