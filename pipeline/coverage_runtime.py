"""Per-invocation coverage collection for Python campaign artifacts.

The reported line percentage is covered executable statement lines divided by
all executable statement lines in the candidate's primary artifact file. Other
files are intentionally excluded from both the numerator and denominator.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _coverage_location() -> tuple[str, str] | None:
    """Return coverage's import root and version in this interpreter, if present."""
    try:
        import coverage
    except ImportError:
        return None
    return str(Path(coverage.__file__).resolve().parent.parent), coverage.__version__


def unavailable(note: str) -> dict[str, Any]:
    return {"status": "unavailable", "collection_note": note}


def _file_metrics(cov: Any, file_report: dict[str, Any], filename: str) -> dict[str, Any]:
    _filename, statements, excluded, _missing, _formatted = cov.analysis2(filename)
    executable = set(statements) - set(excluded)
    executed = sorted(set(cov.get_data().lines(filename) or ()))
    covered = executable & set(executed)
    summary = file_report["summary"]
    total_lines = len(executable)
    covered_lines = len(covered)
    total_branches = int(summary["num_branches"])
    covered_branches = int(summary["covered_branches"])
    # coverage.py JSON's executed_branches/missing_branches are branch arcs:
    # possible arcs leaving decision lines, not all arcs in CoverageData. The
    # report's summary counts come from coverage.py's branch-number accounting,
    # not from the length of either arc list. Preserve negative endpoints:
    # coverage.py uses them as code-object entry/exit markers, not source lines.
    executed_branch_arcs = sorted(file_report.get("executed_branches", []))
    missing_branch_arcs = sorted(file_report.get("missing_branches", []))
    return {
        "line_percent": round(100.0 * covered_lines / total_lines if total_lines else 100.0, 4),
        "covered_lines": covered_lines,
        "total_lines": total_lines,
        "branch_percent": round(
            100.0 * covered_branches / total_branches if total_branches else 100.0,
            4,
        ),
        "covered_branches": covered_branches,
        "total_branches": total_branches,
        "executed_lines": executed,
        "executed_branch_arcs": executed_branch_arcs,
        "missing_branch_arcs": missing_branch_arcs,
    }


def _collected_record(tool_version: str, file_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Serialize aggregate metrics and include per-file details only when needed."""
    total_lines = sum(metrics["total_lines"] for metrics in file_metrics.values())
    covered_lines = sum(metrics["covered_lines"] for metrics in file_metrics.values())
    total_branches = sum(metrics["total_branches"] for metrics in file_metrics.values())
    covered_branches = sum(metrics["covered_branches"] for metrics in file_metrics.values())
    executed_lines = sorted({line for metrics in file_metrics.values() for line in metrics["executed_lines"]})
    executed_branch_arcs = sorted({
        tuple(arc) for metrics in file_metrics.values() for arc in metrics["executed_branch_arcs"]
    })
    missing_branch_arcs = sorted({
        tuple(arc) for metrics in file_metrics.values() for arc in metrics["missing_branch_arcs"]
    })
    record: dict[str, Any] = {
        "status": "collected",
        "tool_version": tool_version,
        "line_percent": round(100.0 * covered_lines / total_lines if total_lines else 100.0, 4),
        "covered_lines": covered_lines,
        "total_lines": total_lines,
        "branch_percent": round(
            100.0 * covered_branches / total_branches if total_branches else 100.0,
            4,
        ),
        "covered_branches": covered_branches,
        "total_branches": total_branches,
        "executed_lines": executed_lines,
        "executed_branch_arcs": [list(arc) for arc in executed_branch_arcs],
        "missing_branch_arcs": [list(arc) for arc in missing_branch_arcs],
    }
    if len(file_metrics) > 1:
        record["coverage_files"] = file_metrics
    return record


def _bootstrap_source(artifact_path: Path, data_file: Path, started_file: Path, import_root: str) -> str:
    """Build a -S bootstrap so candidate imports retain the campaign's semantics."""
    values = {
        "artifact": str(artifact_path.resolve()),
        "data_file": str(data_file.resolve()),
        "started_file": str(started_file.resolve()),
        "import_root": import_root,
    }
    return f'''\
import runpy, sys
sys.path.insert(0, {values["import_root"]!r})
from coverage import Coverage
sys.path.remove({values["import_root"]!r})
artifact = {values["artifact"]!r}
coverage = Coverage(data_file={values["data_file"]!r}, include=[artifact], config_file=False, branch=True)
coverage.start()
open({values["started_file"]!r}, "w").close()
try:
    sys.argv[0] = artifact
    runpy.run_path(artifact, run_name="__main__")
finally:
    coverage.stop()
    coverage.save()
'''


def _read_coverage(data_file: Path, artifact_path: Path, tool_version: str) -> dict[str, Any]:
    """Read one isolated data file and calculate artifact-only line and branch coverage."""
    import coverage

    cov = coverage.Coverage(data_file=str(data_file), config_file=False)
    cov.load()
    target = str(artifact_path.resolve())
    data = cov.get_data()
    measured = {str(Path(name).resolve()) for name in data.measured_files()}
    if target not in measured:
        return {"status": "error", "collection_note": "coverage data did not include the candidate artifact"}

    report_path = data_file.with_suffix(".json")
    cov.json_report(outfile=str(report_path))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_files = report.get("files", {})
    if target not in report_files:
        return {"status": "error", "collection_note": "coverage JSON report omitted the candidate artifact"}
    # Keys come from the measured paths rather than assuming one candidate file.
    names = [Path(filename).name for filename in report_files]
    file_metrics: dict[str, dict[str, Any]] = {}
    for filename, file_report in report_files.items():
        key = Path(filename).name
        if names.count(key) > 1:
            key = filename
        file_metrics[key] = _file_metrics(cov, file_report, filename)
    return _collected_record(tool_version, file_metrics)


def run_python_artifact(
    artifact_path: Path,
    case_bytes: bytes,
    *,
    cwd: str,
    env: dict[str, str],
    timeout: float,
) -> tuple[subprocess.CompletedProcess[bytes] | None, dict[str, Any]]:
    """Run one artifact once under a unique coverage data file and collect it.

    The returned process result can have a non-zero exit code; coverage is still
    read in that case so partial execution is retained. A timeout has no process
    result, but any data saved before termination is also retained when possible.
    """
    location = _coverage_location()
    if location is None:
        try:
            result = subprocess.run(
                [sys.executable, "-S", "-B", "-u", str(artifact_path)],
                input=case_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                timeout=timeout,
                text=False,
            )
            return result, unavailable("coverage.py is not installed in the campaign interpreter")
        except Exception as exc:
            return None, unavailable(f"coverage.py is unavailable; ordinary execution failed: {exc}")

    import_root, version = location
    try:
        with tempfile.TemporaryDirectory(prefix="nvp_coverage_") as temp_dir:
            data_file = Path(temp_dir) / "coverage.data"
            started_file = Path(temp_dir) / "candidate_started"
            command = [
                sys.executable,
                "-S",
                "-c",
                _bootstrap_source(artifact_path, data_file, started_file, import_root),
            ]
            result: subprocess.CompletedProcess[bytes] | None = None
            note = ""
            try:
                result = subprocess.run(
                    command,
                    input=case_bytes,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                    timeout=timeout,
                    text=False,
                )
                if result.returncode != 0:
                    note = f"candidate exited with code {result.returncode}"
            except subprocess.TimeoutExpired as exc:
                note = f"candidate timed out after {timeout:g}s"
                # The process may have saved data before it was terminated.
                result = subprocess.CompletedProcess(command, 124, exc.stdout or b"", exc.stderr or b"")

            if not data_file.is_file():
                if started_file.is_file():
                    return result, unavailable(note or "coverage data file was not produced after candidate execution")
                # Coverage startup can fail before the artifact runs. Retry using
                # the campaign's original command so optional coverage cannot
                # change the candidate's recorded result.
                try:
                    fallback = subprocess.run(
                        [sys.executable, "-S", "-B", "-u", str(artifact_path)],
                        input=case_bytes,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=cwd,
                        env=env,
                        timeout=timeout,
                        text=False,
                    )
                    return fallback, unavailable(note or "coverage data file was not produced")
                except Exception as exc:
                    return None, unavailable(f"coverage data file was not produced; ordinary execution failed: {exc}")
            try:
                coverage_result = _read_coverage(data_file, artifact_path, version)
            except Exception as exc:
                return result, {"status": "error", "collection_note": f"could not read coverage data: {exc}"}
            if note:
                coverage_result["collection_note"] = note
            return result, coverage_result
    except Exception as exc:
        return None, {"status": "error", "collection_note": f"coverage execution failed: {exc}"}


def unavailable_if_requested(enabled: bool) -> dict[str, Any] | None:
    """Cheap helper for paths where no Python candidate process was run."""
    if not enabled:
        return None
    if importlib.util.find_spec("coverage") is None:
        return unavailable("coverage.py is not installed in the campaign interpreter")
    return unavailable("coverage was not collected because no Python candidate process ran")


def coverage_record(test_id: int, version_id: str, passed: bool, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_id": test_id,
        "version_id": version_id,
        "result": "passed" if passed else "failed",
        "coverage": data,
    }
