"""
test_runner.py

Runs tests inside a Sandbox and returns structured results the agent
can reason over directly — not raw stdout.

Three parallel tracks:
  1. Test suite (pytest / jest)        — which tests pass/fail and why
  2. Quality gates (lint, type-check)  — code health signals
  3. Coverage delta                    — did the fix add coverage?

The agent receives a TestRunResult with machine-readable fields,
not a blob of ANSI-escaped terminal output.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from typing import Optional

from .sandbox_manager import ExecResult, Sandbox


# ---------------------------------------------------------------------------
# Data structures — what the agent reasons over
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    name:         str
    status:       str           # "passed" | "failed" | "error" | "skipped"
    file:         Optional[str] = None
    line:         Optional[int] = None
    error_type:   Optional[str] = None   # e.g. "AssertionError", "TypeError"
    error_msg:    Optional[str] = None   # first line of the error
    stack_frames: list[str]     = field(default_factory=list)
    duration_s:   float         = 0.0


@dataclass
class QualityResult:
    tool:     str        # "pyflakes" | "mypy" | "eslint"
    passed:   bool
    issues:   list[str]  # human-readable issue strings, max 20


@dataclass
class EnvError:
    """
    Raised when the environment itself is broken, not the code.
    Examples: missing import, wrong Python version, corrupt dep.
    The sandbox's LLM advisor diagnoses these.
    """
    category:   str      # "missing_dep" | "import_error" | "env_config"
    raw_error:  str
    suggestion: Optional[str] = None    # LLM-generated fix hint


@dataclass
class TestRunResult:
    # Summary
    passed:        int   = 0
    failed:        int   = 0
    errors:        int   = 0
    skipped:       int   = 0
    total:         int   = 0

    # Detail
    test_cases:    list[TestCase]    = field(default_factory=list)
    quality:       list[QualityResult] = field(default_factory=list)
    env_errors:    list[EnvError]    = field(default_factory=list)
    coverage_pct:  Optional[float]   = None
    duration_s:    float             = 0.0

    # Raw output (kept for debugging, not fed to LLM)
    raw_stdout:    str   = ""
    raw_stderr:    str   = ""

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.errors == 0 and not self.env_errors

    @property
    def confidence_score(self) -> float:
        """
        Rough confidence score for the PR.
        100% if all tests pass + quality clean.
        Degrades per failure.
        """
        if self.total == 0:
            return 0.4   # no tests run — low confidence
        base = self.passed / max(self.total, 1)
        quality_penalty = sum(0.05 for q in self.quality if not q.passed)
        env_penalty = 0.2 if self.env_errors else 0.0
        return max(0.0, min(1.0, base - quality_penalty - env_penalty))

    def to_agent_context(self) -> str:
        """
        Serialise to a compact string for injection into the agent's context.
        Designed to be token-efficient — no raw stdout, no ANSI codes.
        """
        lines = [
            f"Test run: {self.passed} passed, {self.failed} failed, "
            f"{self.errors} errors, {self.skipped} skipped "
            f"(confidence: {self.confidence_score:.0%})",
        ]

        if self.env_errors:
            lines.append("\nEnvironment issues:")
            for e in self.env_errors:
                lines.append(f"  [{e.category}] {e.raw_error[:200]}")
                if e.suggestion:
                    lines.append(f"  → Suggestion: {e.suggestion}")

        failing = [t for t in self.test_cases if t.status in ("failed", "error")]
        if failing:
            lines.append(f"\nFailing tests ({len(failing)}):")
            for t in failing[:10]:   # cap at 10 for context window
                lines.append(f"  ✗ {t.name}")
                if t.error_type:
                    lines.append(f"    {t.error_type}: {(t.error_msg or '')[:120]}")
                if t.file and t.line:
                    lines.append(f"    at {t.file}:{t.line}")
                for frame in t.stack_frames[:3]:
                    lines.append(f"    {frame}")

        if self.quality:
            lines.append("\nQuality gates:")
            for q in self.quality:
                status = "✓" if q.passed else "✗"
                lines.append(f"  {status} {q.tool}")
                for issue in q.issues[:5]:
                    lines.append(f"    {issue}")

        if self.coverage_pct is not None:
            lines.append(f"\nCoverage: {self.coverage_pct:.1f}%")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Language-specific runners
# ---------------------------------------------------------------------------

class PytestRunner:
    """
    Runs pytest with --json-report for structured output.
    Falls back to parsing plain text if json-report plugin is unavailable.
    """

    REPORT_PATH = "/tmp/pytest-report.json"

    def run(self, sandbox: Sandbox, test_paths: Optional[list[str]] = None) -> tuple[ExecResult, list[TestCase]]:
        cmd = [
            "python", "-m", "pytest",
            "--json-report",
            f"--json-report-file={self.REPORT_PATH}",
            "--tb=short",
            "--no-header",
            "-q",
        ]

        if test_paths:
            cmd += test_paths

        result = sandbox.exec(cmd, timeout=sandbox.config.timeout_test)
        test_cases = self._parse_json_report(sandbox) or self._parse_text_output(result.stdout)
        return result, test_cases

    def _parse_json_report(self, sandbox: Sandbox) -> Optional[list[TestCase]]:
        try:
            raw = sandbox.read_file(self.REPORT_PATH)
            data = json.loads(raw)
        except Exception:
            return None

        cases = []
        for t in data.get("tests", []):
            outcome = t.get("outcome", "unknown")
            call    = t.get("call", {})
            crash   = call.get("crash", {})
            longrepr = call.get("longrepr", "")

            # Extract stack frames from longrepr
            frames = [
                line.strip()
                for line in longrepr.splitlines()
                if line.strip().startswith(("E ", "FAILED", ">"))
            ][:5]

            cases.append(TestCase(
                name       = t.get("nodeid", "unknown"),
                status     = outcome,
                file       = crash.get("path"),
                line       = crash.get("lineno"),
                error_type = _extract_error_type(longrepr),
                error_msg  = crash.get("message", "")[:200] if crash else None,
                stack_frames = frames,
                duration_s = t.get("call", {}).get("duration", 0.0),
            ))
        return cases

    def _parse_text_output(self, stdout: str) -> list[TestCase]:
        """Fallback: parse pytest plain text output."""
        cases = []
        # Match lines like: FAILED tests/test_auth.py::test_login - AssertionError
        pattern = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED)\s+(.+?)(?:\s+-\s+(.+))?$", re.MULTILINE)
        for m in pattern.finditer(stdout):
            status_map = {"PASSED": "passed", "FAILED": "failed", "ERROR": "error", "SKIPPED": "skipped"}
            cases.append(TestCase(
                name      = m.group(2).strip(),
                status    = status_map.get(m.group(1), "unknown"),
                error_msg = m.group(3),
            ))
        return cases


class JestRunner:
    """Runs Jest with --json for structured output."""

    def run(self, sandbox: Sandbox, test_paths: Optional[list[str]] = None) -> tuple[ExecResult, list[TestCase]]:
        cmd = ["npx", "jest", "--json", "--no-coverage", "--forceExit"]
        if test_paths:
            cmd += test_paths

        result = sandbox.exec(cmd, timeout=sandbox.config.timeout_test)
        test_cases = self._parse_json(result.stdout)
        return result, test_cases

    def _parse_json(self, stdout: str) -> list[TestCase]:
        # Jest --json writes JSON to stdout
        try:
            # Jest may mix non-JSON lines; find the JSON blob
            for line in stdout.splitlines():
                line = line.strip()
                if line.startswith("{") and "testResults" in line:
                    data = json.loads(line)
                    break
            else:
                data = json.loads(stdout)
        except (json.JSONDecodeError, UnboundLocalError):
            return []

        cases = []
        for suite in data.get("testResults", []):
            for t in suite.get("testResults", []):
                status_map = {"passed": "passed", "failed": "failed", "pending": "skipped"}
                msg = None
                frames = []
                if t.get("failureMessages"):
                    raw_msg = t["failureMessages"][0]
                    msg = raw_msg.splitlines()[0][:200] if raw_msg else None
                    frames = [l.strip() for l in raw_msg.splitlines() if "at " in l][:5]
                cases.append(TestCase(
                    name         = t.get("fullName", "unknown"),
                    status       = status_map.get(t.get("status", ""), "unknown"),
                    file         = suite.get("testFilePath", "").replace(sandbox.config.working_dir + "/", ""),
                    error_msg    = msg,
                    stack_frames = frames,
                    duration_s   = t.get("duration", 0) / 1000,
                ))
        return cases


# ---------------------------------------------------------------------------
# Quality gates (run in parallel with tests)
# ---------------------------------------------------------------------------

class QualityGateRunner:
    """
    Runs lint + type-check in parallel with the test suite.
    Results are merged into TestRunResult.quality.
    """

    def run_python(self, sandbox: Sandbox) -> list[QualityResult]:
        results = []
        threads = []
        output_bucket: dict[str, QualityResult] = {}

        def run_pyflakes():
            r = sandbox.exec(["python", "-m", "pyflakes", "."], timeout=30)
            issues = [l for l in r.stdout.splitlines() if l.strip()][:20]
            output_bucket["pyflakes"] = QualityResult(
                tool="pyflakes", passed=r.exit_code == 0, issues=issues
            )

        def run_mypy():
            r = sandbox.exec(
                ["python", "-m", "mypy", ".", "--ignore-missing-imports", "--no-error-summary"],
                timeout=60,
            )
            issues = [l for l in r.stdout.splitlines() if ": error:" in l][:20]
            output_bucket["mypy"] = QualityResult(
                tool="mypy", passed=r.exit_code == 0, issues=issues
            )

        for fn in (run_pyflakes, run_mypy):
            t = threading.Thread(target=fn)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=90)

        return list(output_bucket.values())

    def run_node(self, sandbox: Sandbox) -> list[QualityResult]:
        r = sandbox.exec(
            ["npx", "eslint", ".", "--ext", ".js,.ts", "--format", "compact"],
            timeout=60,
        )
        issues = [l for l in r.stdout.splitlines() if ": error:" in l or ": warning:" in l][:20]
        return [QualityResult(tool="eslint", passed=r.exit_code == 0, issues=issues)]


# ---------------------------------------------------------------------------
# Incremental test selector
# ---------------------------------------------------------------------------

class IncrementalTestSelector:
    """
    Figures out which test files need to run based on which source files changed.
    Uses a simple import-graph heuristic — good enough for most repos.

    For Python: grep for 'import <module>' in test files.
    For Node: look at require/import statements.
    """

    def select_tests(
        self,
        sandbox: Sandbox,
        changed_files: list[str],
        language: str = "python",
    ) -> Optional[list[str]]:
        """
        Returns a list of test file paths to run, or None to run all tests.
        Returns None (run everything) if the changed file is a core module
        that many tests might import.
        """
        if not changed_files:
            return None

        # Changed module names (without path/extension)
        changed_modules = {
            Path(f).stem
            for f in changed_files
            if not f.startswith("test")
        }

        if language == "python":
            return self._select_python(sandbox, changed_modules)
        elif language in ("node", "javascript", "typescript"):
            return self._select_node(sandbox, changed_modules)
        return None

    def _select_python(self, sandbox: Sandbox, modules: set[str]) -> Optional[list[str]]:
        # Find all test files
        r = sandbox.exec(["find", ".", "-name", "test_*.py", "-o", "-name", "*_test.py"])
        test_files = [l.strip() for l in r.stdout.splitlines() if l.strip()]

        if not test_files:
            return None

        relevant = []
        for tf in test_files:
            # Check for both "import module" and "from module import"
            patterns = [f"import {m}", f"from {m}"]
            r = sandbox.exec(["grep", "-qE", "|".join(patterns), tf])
            if r.exit_code == 0:
                relevant.append(tf)

        # If more than 70% of tests are relevant, just run everything
        if len(relevant) > len(test_files) * 0.7:
            return None

        return relevant or None

    def _select_node(self, sandbox: Sandbox, modules: set[str]) -> Optional[list[str]]:
        r = sandbox.exec(["find", ".", "-name", "*.test.js", "-o", "-name", "*.test.ts",
                          "-o", "-name", "*.spec.js", "-o", "-name", "*.spec.ts"])
        test_files = [l.strip() for l in r.stdout.splitlines() if l.strip()]

        if not test_files:
            return None

        relevant = []
        for tf in test_files:
            for m in modules:
                r = sandbox.exec(["grep", "-l", m, tf])
                if r.exit_code == 0:
                    relevant.append(tf)
                    break

        if len(relevant) > len(test_files) * 0.7:
            return None

        return relevant or None


# ---------------------------------------------------------------------------
# Env error detector + LLM advisor
# ---------------------------------------------------------------------------

class EnvErrorDetector:
    """
    Detects when the environment itself is broken (not the code),
    and optionally calls a lightweight LLM to suggest a fix.
    """

    IMPORT_ERROR_PATTERNS = [
        (r"ModuleNotFoundError: No module named '([^']+)'", "missing_dep"),
        (r"ImportError: cannot import name '([^']+)'",       "import_error"),
        (r"cannot find module '([^']+)'",                    "missing_dep"),   # node
    ]

    ENV_PATTERNS = [
        (r"SyntaxError: invalid syntax",                     "syntax_error"),
        (r"IndentationError",                                "syntax_error"),
        (r"Permission denied",                               "env_config"),
        (r"No such file or directory: '([^']+)'",            "env_config"),
    ]

    def detect(self, stdout: str, stderr: str) -> list[EnvError]:
        combined = stdout + "\n" + stderr
        errors = []

        for pattern, category in self.IMPORT_ERROR_PATTERNS + self.ENV_PATTERNS:
            m = re.search(pattern, combined, re.IGNORECASE)
            if m:
                errors.append(EnvError(
                    category  = category,
                    raw_error = m.group(0)[:300],
                ))

        return errors

    def advise(self, env_error: EnvError, llm_client=None) -> str:
        """
        Call the LLM inside the sandbox to suggest a fix for the env error.
        llm_client: an Anthropic client (or None to skip LLM advice).
        """
        if llm_client is None:
            return self._rule_based_advice(env_error)

        prompt = (
            f"A Docker container running automated tests encountered this environment error:\n\n"
            f"Category: {env_error.category}\n"
            f"Error: {env_error.raw_error}\n\n"
            f"Suggest a one-line fix (e.g. add a package to requirements.txt, "
            f"change a Python version, fix an import path). Be specific and brief."
        )
        try:
            response = llm_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception:
            return self._rule_based_advice(env_error)

    def _rule_based_advice(self, env_error: EnvError) -> str:
        if env_error.category == "missing_dep":
            m = re.search(r"'([^']+)'", env_error.raw_error)
            pkg = m.group(1) if m else "the missing package"
            return f"Add '{pkg}' to requirements.txt (or package.json) and retry."
        if env_error.category == "import_error":
            return "Check that the module path is correct and the package is installed."
        if env_error.category == "syntax_error":
            return "The patch introduced a syntax error. Re-read the patched file and fix it."
        return "Check the container configuration and dependency files."


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

class SandboxTestRunner:
    """
    Main entry point. Runs tests + quality gates in parallel,
    parses all output, returns a TestRunResult.

    Usage:
        runner = SandboxTestRunner(language="python")
        with manager.container() as sandbox:
            result = runner.run(sandbox, changed_files=["auth/tokens.py"])
            print(result.to_agent_context())
    """

    def __init__(self, language: str = "python", llm_client=None):
        self.language     = language
        self.llm_client   = llm_client
        self.env_detector = EnvErrorDetector()
        self.selector     = IncrementalTestSelector()
        self.quality      = QualityGateRunner()

    def run(
        self,
        sandbox: Sandbox,
        changed_files: Optional[list[str]] = None,
        run_all: bool = False,
    ) -> TestRunResult:

        result = TestRunResult()

        # --- Incremental test selection ---
        test_paths = None
        if not run_all and changed_files:
            test_paths = self.selector.select_tests(sandbox, changed_files, self.language)

        # --- Parallel: tests + quality gates ---
        test_output: dict   = {}
        quality_output: dict = {}

        def run_tests():
            if self.language == "python":
                runner = PytestRunner()
            else:
                runner = JestRunner()
            exec_r, cases = runner.run(sandbox, test_paths)
            test_output["exec"]  = exec_r
            test_output["cases"] = cases

        def run_quality():
            if self.language == "python":
                quality_output["results"] = self.quality.run_python(sandbox)
            else:
                quality_output["results"] = self.quality.run_node(sandbox)

        t1 = threading.Thread(target=run_tests)
        t2 = threading.Thread(target=run_quality)
        t1.start(); t2.start()
        t1.join(timeout=sandbox.config.timeout_test + 30)
        t2.join(timeout=90)

        # --- Assemble result ---
        exec_r    = test_output.get("exec")
        test_cases = test_output.get("cases", [])

        if exec_r:
            result.raw_stdout = exec_r.stdout
            result.raw_stderr = exec_r.stderr
            result.duration_s = exec_r.duration_s

            # Detect env errors first — they explain test failures
            env_errors = self.env_detector.detect(exec_r.stdout, exec_r.stderr)
            for e in env_errors:
                e.suggestion = self.env_detector.advise(e, self.llm_client)
            result.env_errors = env_errors

        result.test_cases = test_cases
        result.passed  = sum(1 for t in test_cases if t.status == "passed")
        result.failed  = sum(1 for t in test_cases if t.status == "failed")
        result.errors  = sum(1 for t in test_cases if t.status == "error")
        result.skipped = sum(1 for t in test_cases if t.status == "skipped")
        result.total   = len(test_cases)

        result.quality = quality_output.get("results", [])

        # --- Coverage (optional) ---
        result.coverage_pct = self._extract_coverage(exec_r.stdout if exec_r else "")

        return result

    def _extract_coverage(self, stdout: str) -> Optional[float]:
        m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
        if m:
            return float(m.group(1))
        m = re.search(r"All files\s*\|\s*[\d.]+\s*\|\s*[\d.]+\s*\|\s*[\d.]+\s*\|\s*([\d.]+)", stdout)
        if m:
            return float(m.group(1))
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_error_type(text: str) -> Optional[str]:
    """Extract exception class name from pytest longrepr."""
    m = re.search(r"^E\s+(\w+(?:Error|Exception|Warning|Failure)):", text, re.MULTILINE)
    return m.group(1) if m else None