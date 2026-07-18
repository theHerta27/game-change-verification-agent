from __future__ import annotations

import re

from agent_service.schemas import DiffFile, DiffHunk, DiffLine, ParsedDiff


HUNK_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<header>.*)$"
)


def _normalize_path(path: str) -> str:
    path = path.strip()
    if path in {"/dev/null", ""}:
        return path
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def parse_unified_diff(diff_text: str) -> ParsedDiff:
    parsed = ParsedDiff()
    current_file: DiffFile | None = None
    current_hunk: DiffHunk | None = None
    old_line = 0
    new_line = 0

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("diff --git "):
            parts = raw_line.split()
            old_path = _normalize_path(parts[2]) if len(parts) > 2 else ""
            new_path = _normalize_path(parts[3]) if len(parts) > 3 else old_path
            current_file = DiffFile(old_path=old_path, new_path=new_path)
            parsed.files.append(current_file)
            current_hunk = None
            continue

        if current_file is None:
            continue

        if raw_line.startswith("--- "):
            current_file.old_path = _normalize_path(raw_line[4:])
            continue

        if raw_line.startswith("+++ "):
            current_file.new_path = _normalize_path(raw_line[4:])
            continue

        match = HUNK_RE.match(raw_line)
        if match:
            old_line = int(match.group("old_start"))
            new_line = int(match.group("new_start"))
            current_hunk = DiffHunk(
                old_start=old_line,
                old_count=int(match.group("old_count") or 1),
                new_start=new_line,
                new_count=int(match.group("new_count") or 1),
                section_header=match.group("header").strip(),
            )
            current_file.hunks.append(current_hunk)
            continue

        if current_hunk is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current_hunk.lines.append(
                DiffLine(line_type="added", content=raw_line[1:], new_line_number=new_line)
            )
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            current_hunk.lines.append(
                DiffLine(line_type="removed", content=raw_line[1:], old_line_number=old_line)
            )
            old_line += 1
        elif raw_line.startswith(" "):
            current_hunk.lines.append(
                DiffLine(
                    line_type="context",
                    content=raw_line[1:],
                    old_line_number=old_line,
                    new_line_number=new_line,
                )
            )
            old_line += 1
            new_line += 1
        elif raw_line.startswith("\\"):
            continue

    return parsed


def iter_added_lines(parsed: ParsedDiff):
    for file in parsed.files:
        for hunk in file.hunks:
            for line in hunk.lines:
                if line.line_type == "added" and line.new_line_number is not None:
                    yield file, hunk, line

