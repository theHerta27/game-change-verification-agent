from pathlib import Path

from agent_service.tools.diff_parser import parse_unified_diff
from agent_service.tools.static_checker import run_static_checks


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _hints(name: str, language: str):
    parsed = parse_unified_diff((EXAMPLES / name).read_text(encoding="utf-8"))
    return run_static_checks(parsed, language)


def _hints_from_text(diff_text: str, language: str):
    return run_static_checks(parse_unified_diff(diff_text), language)


def test_static_checker_hits_go_http_timeout_and_ignored_error():
    rule_ids = {hint.rule_id for hint in _hints("go_http_no_timeout.patch", "go")}

    assert "go_http_no_timeout" in rule_ids
    assert "go_ignored_err" not in rule_ids


def test_static_checker_hits_go_resp_body_not_closed():
    rule_ids = {hint.rule_id for hint in _hints("go_resp_body_not_closed.patch", "go")}

    assert "go_resp_body_not_closed" in rule_ids


def test_static_checker_hits_python_requests_sql_and_eval():
    request_rule_ids = {hint.rule_id for hint in _hints("python_requests_no_timeout.patch", "python")}
    sql_rule_ids = {hint.rule_id for hint in _hints("python_sql_injection.patch", "python")}

    assert "python_requests_no_timeout" in request_rule_ids
    assert "python_sql_string_concat" in sql_rule_ids
    assert "python_eval_exec" in sql_rule_ids


def test_go_err_returned_should_not_trigger_ignored_err():
    diff = """diff --git a/service/client.go b/service/client.go
--- a/service/client.go
+++ b/service/client.go
@@ -1,3 +1,6 @@
 func Fetch(url string) (*Response, error) {
+    resp, err := http.Get(url)
+    return resp, err
 }
"""
    rule_ids = {hint.rule_id for hint in _hints_from_text(diff, "go")}

    assert "go_ignored_err" not in rule_ids


def test_go_err_checked_should_not_trigger_ignored_err():
    diff = """diff --git a/service/client.go b/service/client.go
--- a/service/client.go
+++ b/service/client.go
@@ -1,3 +1,9 @@
 func Fetch(url string) (*Response, error) {
+    resp, err := http.Get(url)
+    if err != nil {
+        return nil, err
+    }
+    return resp, nil
 }
"""
    rule_ids = {hint.rule_id for hint in _hints_from_text(diff, "go")}

    assert "go_ignored_err" not in rule_ids


def test_go_err_assigned_but_unused_should_trigger_ignored_err():
    diff = """diff --git a/service/client.go b/service/client.go
--- a/service/client.go
+++ b/service/client.go
@@ -1,3 +1,7 @@
 func Fetch(url string) *Response {
+    resp, err := http.Get(url)
+    _ = resp
+    return resp
 }
"""
    rule_ids = {hint.rule_id for hint in _hints_from_text(diff, "go")}

    assert "go_ignored_err" in rule_ids


def test_csharp_checker_detects_per_frame_io_and_external_execution():
    diff = """diff --git a/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs b/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs
--- a/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs
+++ b/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs
@@ -10,3 +10,6 @@
 private void Update()
 {
+    string config = File.ReadAllText("config.json");
+    System.Diagnostics.Process.Start("cmd.exe");
 }
"""

    rule_ids = {hint.rule_id for hint in _hints_from_text(diff, "csharp")}

    assert "csharp_per_frame_io_or_lookup" in rule_ids
    assert "csharp_external_execution" in rule_ids


def test_csharp_checker_detects_unseeded_runtime_random():
    diff = """diff --git a/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs b/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs
--- a/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs
+++ b/game-unity/Assets/Scripts/RuntimeDemoBootstrap.cs
@@ -10,3 +10,4 @@
 private void SpawnWave()
 {
+    int roll = UnityEngine.Random.Range(0, 10);
 }
"""

    rule_ids = {hint.rule_id for hint in _hints_from_text(diff, "csharp")}

    assert "csharp_unseeded_runtime_random" in rule_ids
