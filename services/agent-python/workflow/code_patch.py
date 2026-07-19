"""Safety gate and isolated application helpers for human-authored Unity C# patches."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any
import hashlib
import re
import shutil

from agent_service.schemas import ParsedDiff
from agent_service.tools.diff_parser import iter_added_lines, parse_unified_diff


ALLOWED_PREFIX = "game-unity/Assets/"
MAX_PATCH_BYTES = 100_000
MAX_CHANGED_LINES = 300
MAX_FILES = 5

_DISALLOWED_METADATA = {
    "new file mode": "file creation is not allowed",
    "deleted file mode": "file deletion is not allowed",
    "rename from": "file rename is not allowed",
    "rename to": "file rename is not allowed",
    "GIT binary patch": "binary patches are not allowed",
    "Binary files ": "binary patches are not allowed",
}

_DANGEROUS_PATTERNS = (
    (re.compile(r"\bSystem\.Diagnostics\.Process\b|\bProcess\.Start\s*\("), "process_launch"),
    (re.compile(r"\bDllImport\s*\("), "native_code"),
    (re.compile(r"\bunsafe\b"), "unsafe_code"),
    (re.compile(r"\bEnvironment\.Exit\s*\("), "process_exit"),
    (re.compile(r"\bApplication\.OpenURL\s*\("), "external_url"),
    (re.compile(r"\bUnityWebRequest\b|\bHttpClient\b|\bWebClient\b|\bSocket\b"), "network_access"),
    (re.compile(r"\bFile\.Delete\s*\(|\bDirectory\.Delete\s*\("), "destructive_file_operation"),
)


def inspect_csharp_patch(diff_text: str, repository_root: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    encoded = diff_text.encode("utf-8")
    parsed = parse_unified_diff(diff_text)

    if not diff_text.strip():
        errors.append(_issue("empty_patch", "Patch must not be empty."))
    if len(encoded) > MAX_PATCH_BYTES:
        errors.append(_issue("patch_too_large", f"Patch exceeds {MAX_PATCH_BYTES} bytes."))
    for marker, message in _DISALLOWED_METADATA.items():
        if marker in diff_text:
            errors.append(_issue("unsupported_patch_operation", message, evidence=marker))
    if not parsed.files:
        errors.append(_issue("no_diff_files", "No unified diff file headers were found."))
    if len(parsed.files) > MAX_FILES:
        errors.append(_issue("too_many_files", f"Patch changes more than {MAX_FILES} files."))

    changed_lines = 0
    for file in parsed.files:
        path = file.new_path
        changed_lines += sum(
            1
            for hunk in file.hunks
            for line in hunk.lines
            if line.line_type in {"added", "removed"}
        )
        path_error = _validate_path(file.old_path, file.new_path, repository_root)
        if path_error:
            errors.append(path_error)
        if not file.hunks:
            errors.append(_issue("missing_hunks", "Changed file has no valid hunks.", path=path))

    if changed_lines > MAX_CHANGED_LINES:
        errors.append(_issue("change_too_large", f"Patch changes more than {MAX_CHANGED_LINES} lines."))

    for file, _hunk, line in iter_added_lines(parsed):
        content = line.content.strip()
        for pattern, rule_id in _DANGEROUS_PATTERNS:
            if pattern.search(content):
                errors.append(
                    _issue(
                        rule_id,
                        "High-risk API is not allowed in an automatically validated patch.",
                        path=file.new_path,
                        line=line.new_line_number,
                        evidence=content,
                    )
                )

    if changed_lines == 0 and parsed.files:
        errors.append(_issue("no_changes", "Patch contains no added or removed lines."))
    if changed_lines > 150:
        warnings.append(_issue("large_review_surface", "Patch changes more than 150 lines; split it if possible."))

    return {
        "passed": not errors,
        "patch_sha256": hashlib.sha256(encoded).hexdigest(),
        "file_count": len(parsed.files),
        "changed_line_count": changed_lines,
        "errors": _deduplicate(errors),
        "warnings": warnings,
        "parsed_diff": parsed.model_dump(),
    }


def copy_unity_source(repository_root: Path, workspace_root: Path) -> Path:
    source_project = repository_root / "game-unity"
    target_project = workspace_root / "game-unity"
    if target_project.exists():
        raise FileExistsError(f"Isolated Unity workspace already exists: {target_project}")
    target_project.mkdir(parents=True)
    for directory in ("Assets", "Packages", "ProjectSettings"):
        source = source_project / directory
        if not source.is_dir():
            raise FileNotFoundError(f"Unity source directory is missing: {source}")
        shutil.copytree(
            source,
            target_project / directory,
            ignore=_unity_copy_ignore,
        )
    return target_project


def apply_csharp_patch(diff_text: str, workspace_root: Path) -> list[str]:
    parsed = parse_unified_diff(diff_text)
    changed_paths: list[str] = []
    for file in parsed.files:
        relative_path = PurePosixPath(file.new_path)
        target = workspace_root.joinpath(*relative_path.parts)
        if not target.is_file():
            raise FileNotFoundError(f"Patch target does not exist in isolated workspace: {file.new_path}")
        _apply_file_hunks(target, parsed, file.new_path)
        changed_paths.append(file.new_path)
    return changed_paths


def hash_files(root: Path, relative_paths: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in relative_paths:
        file_path = root.joinpath(*PurePosixPath(path).parts)
        hashes[path] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return hashes


def _validate_path(old_path: str, new_path: str, repository_root: Path) -> dict[str, Any] | None:
    if old_path in {"", "/dev/null"} or new_path in {"", "/dev/null"}:
        return _issue("file_lifecycle_change", "Creating or deleting files is not allowed.", path=new_path)
    if old_path != new_path:
        return _issue("path_changed", "Renaming files is not allowed.", path=new_path)
    normalized = new_path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts:
        return _issue("path_traversal", "Patch path must stay inside the repository.", path=new_path)
    if not normalized.startswith(ALLOWED_PREFIX) or not normalized.lower().endswith(".cs"):
        return _issue(
            "path_not_allowed",
            "Only existing game-unity/Assets/**/*.cs files may be changed.",
            path=new_path,
        )
    target = repository_root.joinpath(*pure.parts)
    if not target.is_file():
        return _issue("target_missing", "Patch target does not exist in the committed baseline.", path=new_path)
    return None


def _apply_file_hunks(target: Path, parsed: ParsedDiff, path: str) -> None:
    file = next(item for item in parsed.files if item.new_path == path)
    source = target.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in source else "\n"
    had_final_newline = source.endswith(("\r\n", "\n"))
    original = source.splitlines()
    output: list[str] = []
    cursor = 0

    for hunk in sorted(file.hunks, key=lambda item: item.old_start):
        start = max(hunk.old_start - 1, 0)
        if start < cursor:
            raise ValueError(f"Overlapping or out-of-order hunks for {path}.")
        output.extend(original[cursor:start])
        cursor = start
        for line in hunk.lines:
            if line.line_type == "added":
                output.append(line.content)
                continue
            if cursor >= len(original) or original[cursor] != line.content:
                actual = "<end-of-file>" if cursor >= len(original) else original[cursor]
                raise ValueError(
                    f"Patch context mismatch for {path} at source line {cursor + 1}: "
                    f"expected {line.content!r}, got {actual!r}."
                )
            if line.line_type == "context":
                output.append(line.content)
            cursor += 1

    output.extend(original[cursor:])
    rendered = newline.join(output)
    if had_final_newline:
        rendered += newline
    target.write_text(rendered, encoding="utf-8", newline="")


def _unity_copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in {"Library", "Temp", "Logs", "Builds", "UserSettings", "obj"}}
    normalized = Path(directory).as_posix()
    if normalized.endswith("Assets/Resources") and "LocalThirdParty" in names:
        ignored.add("LocalThirdParty")
    return ignored


def _issue(
    rule_id: str,
    message: str,
    *,
    path: str | None = None,
    line: int | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "message": message,
        "path": path,
        "line": line,
        "evidence": evidence,
    }


def _deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = (item["rule_id"], item["message"], item["path"], item["line"], item["evidence"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
