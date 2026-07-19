from pathlib import Path

import pytest

from workflow.code_patch import apply_csharp_patch, copy_unity_source, inspect_csharp_patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TARGET = "game-unity/Assets/Scripts/RuntimeRunSettings.cs"


def _safe_patch() -> str:
    return f"""diff --git a/{TARGET} b/{TARGET}
--- a/{TARGET}
+++ b/{TARGET}
@@ -13,6 +13,8 @@ public static RuntimeRunSettings FromArgs(string[] args)
         public static RuntimeRunSettings FromArgs(string[] args)
         {{
+            if (args == null)
+                throw new ArgumentNullException(nameof(args));
             RuntimeRunSettings settings = new()
             {{
                 AutoRun = Array.IndexOf(args, "--auto-run") >= 0,
"""


def test_patch_gate_accepts_existing_unity_csharp_file():
    result = inspect_csharp_patch(_safe_patch(), REPOSITORY_ROOT)

    assert result["passed"] is True
    assert result["file_count"] == 1
    assert result["changed_line_count"] == 2


@pytest.mark.parametrize(
    ("path", "expected_rule"),
    [
        ("services/agent-python/api/server.py", "path_not_allowed"),
        ("../outside.cs", "path_traversal"),
        ("game-unity/Assets/Scripts/NotPresent.cs", "target_missing"),
    ],
)
def test_patch_gate_rejects_out_of_scope_paths(path: str, expected_rule: str):
    patch = f"""diff --git a/{path} b/{path}
--- a/{path}
+++ b/{path}
@@ -1,1 +1,2 @@
 existing
+changed
"""

    result = inspect_csharp_patch(patch, REPOSITORY_ROOT)

    assert result["passed"] is False
    assert expected_rule in {item["rule_id"] for item in result["errors"]}


def test_patch_gate_rejects_process_launch():
    patch = _safe_patch().replace(
        "        if (args == null)",
        "        System.Diagnostics.Process.Start(\"cmd.exe\");",
    )

    result = inspect_csharp_patch(patch, REPOSITORY_ROOT)

    assert result["passed"] is False
    assert "process_launch" in {item["rule_id"] for item in result["errors"]}


def test_patch_is_applied_only_to_isolated_workspace(tmp_path: Path):
    source_file = REPOSITORY_ROOT / TARGET
    source_before = source_file.read_bytes()
    workspace = tmp_path / "workspace"
    copy_unity_source(REPOSITORY_ROOT, workspace)

    changed = apply_csharp_patch(_safe_patch(), workspace)
    isolated = workspace / TARGET

    assert changed == [TARGET]
    assert "ArgumentNullException" in isolated.read_text(encoding="utf-8")
    assert source_file.read_bytes() == source_before


def test_patch_application_rejects_context_mismatch(tmp_path: Path):
    workspace = tmp_path / "workspace"
    copy_unity_source(REPOSITORY_ROOT, workspace)
    invalid = _safe_patch().replace("RuntimeRunSettings settings = new()", "missing context")

    with pytest.raises(ValueError, match="context mismatch"):
        apply_csharp_patch(invalid, workspace)
