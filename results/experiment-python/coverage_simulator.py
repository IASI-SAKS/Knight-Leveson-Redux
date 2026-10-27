from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class CoverageMetrics:
    total_lines: int = 0
    covered_lines: int = 0
    line_percent: float = 0.0
    total_branches: int = 0
    covered_branches: int = 0
    branch_percent: float = 0.0
    covered_line_ids: set[int] = field(default_factory=set)
    covered_branch_arcs: set[tuple[int, int]] = field(default_factory=set)
    missing_test_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "line_percent": self.line_percent,
            "total_branches": self.total_branches,
            "covered_branches": self.covered_branches,
            "branch_percent": self.branch_percent,
            "covered_line_ids": sorted(self.covered_line_ids),
            "covered_branch_arcs": [list(arc) for arc in sorted(self.covered_branch_arcs)],
            "missing_test_ids": self.missing_test_ids,
        }


def _safe_float_percentage(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return 100.0 * numerator / denominator


def _validate_coverage_payload(payload: dict[str, Any], source: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Coverage payload for {source} is not an object")
    if payload.get("status") != "collected":
        raise ValueError(f"Coverage payload for {source} has status '{payload.get('status')}' instead of 'collected'")
    required_fields = ["total_lines", "executed_lines", "total_branches", "executed_branch_arcs"]
    missing = [field_name for field_name in required_fields if field_name not in payload]
    if missing:
        raise ValueError(f"Coverage payload for {source} is missing required fields: {missing}")


def load_coverage_history(coverage_jsonl_path: Path | str) -> dict[tuple[int, str], dict[str, Any]]:
    path = Path(coverage_jsonl_path)
    history: dict[tuple[int, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} at line {line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Record at {path}:{line_no} is not a JSON object")
            test_id = record.get("test_id")
            version_id = record.get("version_id")
            if not isinstance(test_id, int):
                raise ValueError(f"Record at {path}:{line_no} has invalid test_id: {test_id!r}")
            if not isinstance(version_id, str):
                raise ValueError(f"Record at {path}:{line_no} has invalid version_id: {version_id!r}")
            coverage = record.get("coverage")
            if not isinstance(coverage, dict):
                raise ValueError(f"Record at {path}:{line_no} is missing a valid 'coverage' object")
            if coverage.get("status") != "collected":
                continue
            _validate_coverage_payload(coverage, f"test_id={test_id}, version_id={version_id}")
            key = (test_id, version_id)
            if key in history:
                raise ValueError(
                    f"Duplicate coverage record for test_id={test_id} and version_id={version_id!r} in {path} "
                    f"(first at line {history[key]['_line_no']}, duplicate at line {line_no})"
                )
            coverage = dict(coverage)
            coverage["_line_no"] = line_no
            history[key] = coverage
    return history


def parse_test_suite(suite_path: Path | str) -> list[int]:
    path = Path(suite_path)
    values: list[int] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            match = re.search(r"\btest_id\s*=\s*(\d+)\b", text)
            if not match:
                raise ValueError(f"Invalid test suite line in {path}:{line_no}: {line.rstrip()!r}")
            values.append(int(match.group(1)))
    return values


def load_implementations(implementations_path: Path | str) -> list[str]:
    path = Path(implementations_path)
    implementations: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            name = line.strip()
            if not name or name.startswith("#"):
                continue
            if name in seen:
                raise ValueError(f"Duplicate implementation name {name!r} in {path}:{line_no}")
            seen.add(name)
            implementations.append(name)
    return implementations


def find_dependent_suite_file(implementation: str, dependent_dir: Path | str) -> Path:
    impl_name = implementation.strip()
    path = Path(dependent_dir)
    matches: list[Path] = []
    for candidate in sorted(path.glob("*.txt")):
        basename = candidate.stem
        stripped = re.sub(r"^[0-9]+-", "", basename)
        if stripped == impl_name:
            matches.append(candidate)
    if not matches:
        raise FileNotFoundError(f"No dependent suite file found for implementation {impl_name!r} in {path}")
    if len(matches) > 1:
        raise ValueError(
            f"Multiple dependent suite files match implementation {impl_name!r}: "
            f"{', '.join(sorted(p.name for p in matches))}"
        )
    return matches[0]


def _collect_test_record(test_id: int, target_implementation: str, history: dict[tuple[int, str], dict[str, Any]]) -> dict[str, Any]:
    key = (test_id, target_implementation)
    if key not in history:
        raise ValueError(
            f"Missing coverage for test_id={test_id} and version_id={target_implementation!r} in history"
        )
    record = history[key]
    coverage = record
    _validate_coverage_payload(coverage, f"test_id={test_id}, version_id={target_implementation}")
    return coverage


def get_cumulative_coverage(
    test_ids: list[int],
    target_implementation: str,
    history: dict[tuple[int, str], dict[str, Any]],
    strict: bool = True,
) -> CoverageMetrics:
    covered_lines: set[int] = set()
    covered_branches: set[tuple[int, int]] = set()
    total_lines = 0
    total_branches = 0
    missing_ids: list[int] = []

    for test_id in test_ids:
        if (test_id, target_implementation) not in history:
            missing_ids.append(test_id)
            if strict:
                raise ValueError(
                    f"missing coverage for test_id={test_id} and version_id={target_implementation!r} in history"
                )
            continue
        record = _collect_test_record(test_id, target_implementation, history)
        executed_lines = record.get("executed_lines", [])
        executed_branch_arcs = record.get("executed_branch_arcs", [])
        if not isinstance(executed_lines, list):
            raise ValueError(f"Coverage for test_id={test_id}, version_id={target_implementation!r} has invalid executed_lines")
        if not isinstance(executed_branch_arcs, list):
            raise ValueError(f"Coverage for test_id={test_id}, version_id={target_implementation!r} has invalid executed_branch_arcs")
        covered_lines.update(int(line) for line in executed_lines)
        for arc in executed_branch_arcs:
            if not isinstance(arc, (list, tuple)) or len(arc) != 2:
                raise ValueError(
                    f"Coverage for test_id={test_id}, version_id={target_implementation!r} has malformed branch arc: {arc!r}"
                )
            covered_branches.add((int(arc[0]), int(arc[1])))

        current_total_lines = record.get("total_lines")
        current_total_branches = record.get("total_branches")
        if current_total_lines is None or current_total_branches is None:
            raise ValueError(
                f"Coverage for test_id={test_id}, version_id={target_implementation!r} is missing total_lines/total_branches"
            )
        if total_lines == 0:
            total_lines = int(current_total_lines)
        elif total_lines != int(current_total_lines):
            raise ValueError(
                f"Inconsistent total_lines for version_id={target_implementation!r}: "
                f"found {total_lines} and {current_total_lines} across selected tests"
            )
        if total_branches == 0:
            total_branches = int(current_total_branches)
        elif total_branches != int(current_total_branches):
            raise ValueError(
                f"Inconsistent total_branches for version_id={target_implementation!r}: "
                f"found {total_branches} and {current_total_branches} across selected tests"
            )

    if total_lines == 0 and test_ids:
        total_lines = 0
    if total_branches == 0 and test_ids:
        total_branches = 0

    return CoverageMetrics(
        total_lines=total_lines,
        covered_lines=len(covered_lines),
        line_percent=_safe_float_percentage(len(covered_lines), total_lines),
        total_branches=total_branches,
        covered_branches=len(covered_branches),
        branch_percent=_safe_float_percentage(len(covered_branches), total_branches),
        covered_line_ids=covered_lines,
        covered_branch_arcs=covered_branches,
        missing_test_ids=missing_ids,
    )


def _sequence_for_pair(source_implementation: str, independent_suite: list[int], dependent_suites: dict[str, list[int]]) -> list[int]:
    seq = list(independent_suite)
    seq.extend(dependent_suites.get(source_implementation, []))
    return seq


def simulate_pairwise(
    implementations: list[str],
    independent_suite: list[int],
    dependent_suites: dict[str, list[int]],
    history: dict[tuple[int, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for source_impl in implementations:
        source_suite = _sequence_for_pair(source_impl, independent_suite, dependent_suites)
        independent_only = list(independent_suite)
        dependent_only = list(dependent_suites.get(source_impl, []))
        for target_impl in implementations:
            independent_metrics = get_cumulative_coverage(independent_only, target_impl, history, strict=False)
            full_metrics = get_cumulative_coverage(source_suite, target_impl, history, strict=False)
            trace_rows = _build_trace_rows(source_impl, target_impl, source_suite, independent_only, history, strict=False)
            result = {
                "source_implementation": source_impl,
                "target_implementation": target_impl,
                "independent_suite_size": len(independent_only),
                "dependent_suite_size": len(dependent_only),
                "total_test_ids": len(source_suite),
                "independent_test_ids": independent_only,
                "dependent_test_ids": dependent_only,
                "source_test_ids": source_suite,
                "missing_test_ids": sorted(set(independent_metrics.missing_test_ids) | set(full_metrics.missing_test_ids)),
                "coverage_by_mark": {
                    "independent": independent_metrics.to_dict(),
                    "independent_plus_dependent": full_metrics.to_dict(),
                },
                "trace_rows": trace_rows,
            }
            results.append(result)
    return results


def _format_percent(value: float) -> str:
    return f"{value:.4f}"


def _build_trace_rows(
    source_implementation: str,
    target_implementation: str,
    source_sequence: list[int],
    independent_suite: list[int],
    history: dict[tuple[int, str], dict[str, Any]],
    strict: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cumulative_lines: set[int] = set()
    cumulative_branches: set[tuple[int, int]] = set()
    independent_count = len(independent_suite)
    step_index = 0

    for test_id in source_sequence:
        key = (test_id, target_implementation)
        if key not in history:
            if strict:
                raise ValueError(
                    f"Missing coverage for test_id={test_id} and version_id={target_implementation!r} in history"
                )
            continue
        record = _collect_test_record(test_id, target_implementation, history)
        before_lines = set(cumulative_lines)
        before_branches = set(cumulative_branches)

        executed_lines = [int(value) for value in record.get("executed_lines", [])]
        executed_arcs = [
            (int(arc[0]), int(arc[1]))
            for arc in record.get("executed_branch_arcs", [])
            if isinstance(arc, (list, tuple)) and len(arc) == 2
        ]
        cumulative_lines.update(executed_lines)
        cumulative_branches.update(executed_arcs)
        step_index += 1

        suite_type = "independent" if step_index <= independent_count else "dependent"
        suite_position = step_index if suite_type == "independent" else step_index - independent_count

        rows.append(
            {
                "step": step_index,
                "suite_type": suite_type,
                "suite_position": suite_position,
                "test_id": test_id,
                "source_implementation": source_implementation,
                "target_implementation": target_implementation,
                "covered_lines": len(cumulative_lines),
                "total_lines": int(record.get("total_lines")),
                "line_percent": _safe_float_percentage(len(cumulative_lines), int(record.get("total_lines"))),
                "new_lines_covered": len(cumulative_lines - before_lines),
                "covered_branches": len(cumulative_branches),
                "total_branches": int(record.get("total_branches")),
                "branch_percent": _safe_float_percentage(len(cumulative_branches), int(record.get("total_branches"))),
                "new_branches_covered": len(cumulative_branches - before_branches),
            }
        )
    return rows


def write_reports(
    results: list[dict[str, Any]],
    output_dir: Path | str,
    history: dict[tuple[int, str], dict[str, Any]] | None = None,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    traces_dir = output_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)

    global_rows: list[dict[str, Any]] = []
    for item in results:
        rows = item.get("trace_rows")
        if rows is None:
            if history is None:
                raise ValueError(
                    "write_reports requires either per-test trace_rows in each result or an indexed coverage history"
                )
            source_sequence = item.get("source_test_ids", [])
            if not source_sequence:
                source_sequence = list(item.get("independent_test_ids", [])) + list(item.get("dependent_test_ids", []))
            rows = _build_trace_rows(
                item["source_implementation"],
                item["target_implementation"],
                source_sequence,
                item.get("independent_test_ids", []),
                history,
            )
        else:
            rows = list(rows)
        global_rows.extend(rows)

        trace_csv_path = traces_dir / f"{item['source_implementation']}__to__{item['target_implementation']}.csv"
        trace_jsonl_path = traces_dir / f"{item['source_implementation']}__to__{item['target_implementation']}.jsonl"
        with trace_csv_path.open("w", newline="", encoding="utf-8") as csv_handle:
            writer = csv.DictWriter(
                csv_handle,
                fieldnames=[
                    "step",
                    "suite_type",
                    "suite_position",
                    "test_id",
                    "source_implementation",
                    "target_implementation",
                    "covered_lines",
                    "total_lines",
                    "line_percent",
                    "new_lines_covered",
                    "covered_branches",
                    "total_branches",
                    "branch_percent",
                    "new_branches_covered",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        with trace_jsonl_path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, default=str, sort_keys=True) + "\n")

    with (output_dir / "coverage_pairwise.jsonl").open("w", encoding="utf-8") as handle:
        for row in global_rows:
            handle.write(json.dumps(row, default=str, sort_keys=True) + "\n")

    summary_rows = [
        {
            "source_implementation": "source_implementation",
            "target_implementation": "target_implementation",
            "independent_lines": "independent_lines",
            "independent_plus_dependent_lines": "independent_plus_dependent_lines",
            "coverage_gain_lines": "coverage_gain_lines",
            "independent_branches": "independent_branches",
            "independent_plus_dependent_branches": "independent_plus_dependent_branches",
            "coverage_gain_branches": "coverage_gain_branches",
            "total_ids": "total_ids",
        }
    ]
    for item in results:
        coverage = item["coverage_by_mark"]
        independent = coverage["independent"]
        full = coverage["independent_plus_dependent"]
        coverage_gain_lines = abs(full["line_percent"] - independent["line_percent"])
        coverage_gain_branches = abs(full["branch_percent"] - independent["branch_percent"])
        summary_rows.append(
            {
                "source_implementation": item["source_implementation"],
                "target_implementation": item["target_implementation"],
                "independent_lines": f"{independent['covered_lines']}/{independent['total_lines']} ({_format_percent(independent['line_percent'])}%)",
                "independent_plus_dependent_lines": f"{full['covered_lines']}/{full['total_lines']} ({_format_percent(full['line_percent'])}%)",
                "coverage_gain_lines": f"{_format_percent(coverage_gain_lines)}%",
                "independent_branches": f"{independent['covered_branches']}/{independent['total_branches']} ({_format_percent(independent['branch_percent'])}%)",
                "independent_plus_dependent_branches": f"{full['covered_branches']}/{full['total_branches']} ({_format_percent(full['branch_percent'])}%)",
                "coverage_gain_branches": f"{_format_percent(coverage_gain_branches)}%",
                "total_ids": item["total_test_ids"],
            }
        )

    summary_path = output_dir / "coverage_pairwise_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as csv_handle:
        writer = csv.DictWriter(
            csv_handle,
            fieldnames=[
                "source_implementation",
                "target_implementation",
                "independent_lines",
                "independent_plus_dependent_lines",
                "coverage_gain_lines",
                "independent_branches",
                "independent_plus_dependent_branches",
                "coverage_gain_branches",
                "total_ids",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows[1:])


def _run_simulation(coverage_path: Path, implementations_path: Path, independent_suite_path: Path, dependent_dir: Path, output_dir: Path, verbose: bool = False) -> list[dict[str, Any]]:
    implementations = load_implementations(implementations_path)
    independent_suite = parse_test_suite(independent_suite_path)
    dependent_suites: dict[str, list[int]] = {}
    for impl in implementations:
        suite_path = find_dependent_suite_file(impl, dependent_dir)
        dependent_suites[impl] = parse_test_suite(suite_path)
    history = load_coverage_history(coverage_path)
    results = simulate_pairwise(implementations, independent_suite, dependent_suites, history)
    write_reports(results, output_dir, history)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate cumulative combinatorial test coverage from coverage history.")
    parser.add_argument("--coverage", default="coverage.jsonl")
    parser.add_argument("--implementations", default="alternativeImplementations.txt")
    parser.add_argument("--independent-suite", default="implementationIndependentTestSuite.txt")
    parser.add_argument("--dependent-dir", default="ImplementationDependentTestSuites")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    root = Path.cwd()
    coverage_path = (root / args.coverage).resolve()
    implementations_path = (root / args.implementations).resolve()
    independent_suite_path = (root / args.independent_suite).resolve()
    dependent_dir = (root / args.dependent_dir).resolve()
    output_dir = (root / args.output_dir).resolve()

    _run_simulation(coverage_path, implementations_path, independent_suite_path, dependent_dir, output_dir, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
