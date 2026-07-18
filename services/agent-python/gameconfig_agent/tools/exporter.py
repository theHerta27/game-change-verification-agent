"""Exporter / Report Builder Tool."""

from __future__ import annotations

import json
from pathlib import Path


class ExporterReportBuilderTool:
    name = "Exporter / Report Builder Tool"

    def export(self, blackboard: dict, output_dir: str | Path) -> list[Path]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        files = [
            self._write_json(output_path / "draft_configs.json", blackboard["draft_configs"]),
            self._write_json(output_path / "final_configs.json", blackboard["repaired_configs"]),
            self._write_json(output_path / "blackboard_trace.json", blackboard),
            self._write_text(output_path / "validation_report.md", self._validation_report(blackboard)),
            self._write_text(output_path / "risk_report.md", self._risk_report(blackboard)),
            self._write_text(output_path / "repair_trace.md", self._repair_trace(blackboard)),
        ]
        blackboard["exported_files"] = [str(path) for path in files]
        return files

    def _write_json(self, path: Path, value: object) -> Path:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _write_text(self, path: Path, value: str) -> Path:
        path.write_text(value, encoding="utf-8")
        return path

    def _validation_report(self, blackboard: dict) -> str:
        initial_errors = blackboard["validation_errors"]
        final_validation = blackboard["final_validation"]
        lines = [
            "# Validation Report",
            "",
            "## Initial Validation",
            f"- Error count: {len(initial_errors)}",
        ]
        for error in initial_errors:
            lines.append(f"- `{error['source']}` `{error['code']}` at `{error['path']}`: {error['message']}")
        lines.extend(
            [
                "",
                "## Final Validation",
                f"- Passed: {final_validation.get('passed')}",
                f"- Error count: {len(final_validation.get('errors', []))}",
            ]
        )
        return "\n".join(lines) + "\n"

    def _risk_report(self, blackboard: dict) -> str:
        lines = ["# Risk Report", ""]
        for finding in blackboard["review_findings"]:
            lines.extend(
                [
                    f"## {finding['section']}",
                    f"- Issue: {finding['issue']}",
                    f"- Severity: {finding['severity']}",
                    f"- Evidence: `{json.dumps(finding['evidence'], ensure_ascii=False)}`",
                    f"- Recommended range: `{json.dumps(finding['recommended_range'], ensure_ascii=False)}`",
                    f"- Preferred fix: {finding['preferred_fix']}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _repair_trace(self, blackboard: dict) -> str:
        lines = ["# Repair Trace", ""]
        for index, action in enumerate(blackboard["repair_actions"], start=1):
            lines.extend(
                [
                    f"## Action {index}: {action['action']}",
                    f"- Scope: `{action['scope']}`",
                    f"- Before: `{json.dumps(action['before'], ensure_ascii=False)}`",
                    f"- After: `{json.dumps(action['after'], ensure_ascii=False)}`",
                    f"- Reason: {action['reason']}",
                    "",
                ]
            )
        return "\n".join(lines)
