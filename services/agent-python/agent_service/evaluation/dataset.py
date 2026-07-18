from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedFinding:
    category: str
    severity: str


@dataclass(frozen=True)
class EvaluationSample:
    name: str
    language: str
    diff: str
    expected_findings: tuple[ExpectedFinding, ...]
    expected_test_suggestions: int
    source_type: str
    notes: str

    @property
    def expected_categories(self) -> set[str]:
        return {finding.category for finding in self.expected_findings}

    @property
    def expected_severities(self) -> set[str]:
        return {finding.severity for finding in self.expected_findings}


def _diff(path: str, body: str) -> str:
    return f"""diff --git a/{path} b/{path}
--- a/{path}
+++ b/{path}
@@ -1,3 +1,8 @@
 package demo
{body}
"""


def _py_diff(path: str, body: str) -> str:
    return f"""diff --git a/{path} b/{path}
--- a/{path}
+++ b/{path}
@@ -1,3 +1,8 @@
 def handler():
{body}
"""


MEDIUM_TIMEOUT = ExpectedFinding("timeout_missing", "medium")
HIGH_RESOURCE = ExpectedFinding("resource_leak", "high")
MEDIUM_ERROR = ExpectedFinding("error_handling", "medium")
HIGH_SQL = ExpectedFinding("sql_injection", "high")
CRITICAL_SECURITY = ExpectedFinding("security", "critical")


EVALUATION_DATASET: tuple[EvaluationSample, ...] = (
    EvaluationSample(
        "go_http_no_timeout_returned_err",
        "go",
        _diff("client.go", "+resp, err := http.Get(url)\n+return resp, err"),
        (MEDIUM_TIMEOUT,),
        1,
        "synthetic_bug",
        "err is returned, so only timeout should be reported",
    ),
    EvaluationSample(
        "go_http_no_timeout_unhandled_err",
        "go",
        _diff("client.go", "+resp, err := http.Get(url)\n+_ = resp"),
        (MEDIUM_TIMEOUT, MEDIUM_ERROR),
        2,
        "synthetic_bug",
        "http helper has no timeout and err is not handled",
    ),
    EvaluationSample(
        "go_resp_body_read_no_close",
        "go",
        _diff("client.go", "+resp, err := http.Get(url)\n+if err != nil { return err }\n+data, _ := io.ReadAll(resp.Body)\n+_ = data"),
        (MEDIUM_TIMEOUT, HIGH_RESOURCE),
        2,
        "synthetic_bug",
        "response body is read without Close",
    ),
    EvaluationSample(
        "go_sql_fmt_sprintf",
        "go",
        _diff("repo.go", '+query := fmt.Sprintf("SELECT * FROM users WHERE id = %s", id)\n+rows, err := db.Query(query)\n+if err != nil { return err }\n+_ = rows'),
        (HIGH_SQL,),
        1,
        "synthetic_bug",
        "SQL string is formatted from input",
    ),
    EvaluationSample(
        "go_sql_concat",
        "go",
        _diff("repo.go", '+query := "SELECT * FROM users WHERE name = " + name\n+rows, err := db.Query(query)\n+if err != nil { return err }\n+_ = rows'),
        (HIGH_SQL,),
        1,
        "synthetic_bug",
        "SQL string is concatenated",
    ),
    EvaluationSample(
        "go_err_assigned_unused",
        "go",
        _diff("store.go", '+value, err := loadValue()\n+fmt.Println(value)'),
        (MEDIUM_ERROR,),
        1,
        "synthetic_bug",
        "err is assigned and not checked or returned",
    ),
    EvaluationSample(
        "go_err_checked_safe",
        "go",
        _diff("store.go", '+value, err := loadValue()\n+if err != nil { return err }\n+fmt.Println(value)'),
        (),
        0,
        "negative",
        "err is checked before use",
    ),
    EvaluationSample(
        "go_http_client_timeout_safe",
        "go",
        _diff("client.go", '+client := &http.Client{Timeout: 3 * time.Second}\n+resp, err := client.Get(url)\n+if err != nil { return err }\n+defer resp.Body.Close()'),
        (),
        0,
        "negative",
        "explicit client timeout and body close",
    ),
    EvaluationSample(
        "go_head_no_timeout",
        "go",
        _diff("probe.go", "+resp, err := http.Head(url)\n+if err != nil { return err }\n+return resp.StatusCode"),
        (MEDIUM_TIMEOUT,),
        1,
        "synthetic_bug",
        "http.Head helper has no timeout",
    ),
    EvaluationSample(
        "go_post_no_timeout_unhandled",
        "go",
        _diff("post.go", '+resp, err := http.Post(url, "application/json", body)\n+fmt.Println(resp.StatusCode)'),
        (MEDIUM_TIMEOUT, MEDIUM_ERROR),
        2,
        "synthetic_bug",
        "http.Post helper has no timeout and err is unhandled",
    ),
    EvaluationSample(
        "go_resp_body_closed_safe",
        "go",
        _diff("client.go", "+resp, err := http.Get(url)\n+if err != nil { return err }\n+defer resp.Body.Close()\n+data, _ := io.ReadAll(resp.Body)\n+_ = data"),
        (MEDIUM_TIMEOUT,),
        1,
        "open_source_patch_like",
        "Close is present, timeout still missing",
    ),
    EvaluationSample(
        "go_negative_logging",
        "go",
        _diff("log.go", '+logger.Info("request completed", "path", path)\n+return nil'),
        (),
        0,
        "negative",
        "safe logging change",
    ),
    EvaluationSample(
        "go_negative_parameterized_sql",
        "go",
        _diff("repo.go", '+rows, err := db.Query("SELECT * FROM users WHERE id = $1", id)\n+if err != nil { return err }\n+_ = rows'),
        (),
        0,
        "negative",
        "parameterized SQL",
    ),
    EvaluationSample(
        "go_multi_sql_and_err",
        "go",
        _diff("repo.go", '+query := fmt.Sprintf("DELETE FROM sessions WHERE user_id = %s", userID)\n+result, err := db.Exec(query)\n+fmt.Println(result)'),
        (HIGH_SQL, MEDIUM_ERROR),
        2,
        "open_source_patch_like",
        "dynamic SQL and unhandled err",
    ),
    EvaluationSample(
        "go_multi_timeout_resource",
        "go",
        _diff("download.go", "+resp, err := http.Get(url)\n+if err != nil { return err }\n+buf, _ := io.ReadAll(resp.Body)\n+return string(buf)"),
        (MEDIUM_TIMEOUT, HIGH_RESOURCE),
        2,
        "open_source_patch_like",
        "timeout and body close risks",
    ),
    EvaluationSample(
        "python_requests_no_timeout",
        "python",
        _py_diff("client.py", "+    resp = requests.get(url)\n+    return resp.text"),
        (MEDIUM_TIMEOUT,),
        1,
        "synthetic_bug",
        "requests.get has no timeout",
    ),
    EvaluationSample(
        "python_requests_timeout_safe",
        "python",
        _py_diff("client.py", "+    resp = requests.get(url, timeout=3)\n+    return resp.text"),
        (),
        0,
        "negative",
        "requests timeout is present",
    ),
    EvaluationSample(
        "python_bare_except",
        "python",
        _py_diff("worker.py", "+    try:\n+        run_job()\n+    except:\n+        return None"),
        (MEDIUM_ERROR,),
        1,
        "synthetic_bug",
        "bare except hides errors",
    ),
    EvaluationSample(
        "python_exception_broad",
        "python",
        _py_diff("worker.py", "+    try:\n+        run_job()\n+    except Exception:\n+        return None"),
        (MEDIUM_ERROR,),
        1,
        "synthetic_bug",
        "broad exception hides errors",
    ),
    EvaluationSample(
        "python_sql_f_string",
        "python",
        _py_diff("repo.py", '+    query = f"SELECT * FROM users WHERE id = {user_id}"\n+    return db.execute(query)'),
        (HIGH_SQL,),
        1,
        "synthetic_bug",
        "SQL query uses f-string interpolation",
    ),
    EvaluationSample(
        "python_sql_concat",
        "python",
        _py_diff("repo.py", '+    query = "DELETE FROM sessions WHERE user_id = " + user_id\n+    return db.execute(query)'),
        (HIGH_SQL,),
        1,
        "synthetic_bug",
        "SQL query uses string concatenation",
    ),
    EvaluationSample(
        "python_sql_percent",
        "python",
        _py_diff("repo.py", '+    query = "SELECT * FROM users WHERE name = %s" % name\n+    return db.execute(query)'),
        (HIGH_SQL,),
        1,
        "open_source_patch_like",
        "SQL query uses percent formatting",
    ),
    EvaluationSample(
        "python_eval",
        "python",
        _py_diff("rules.py", "+    return eval(rule_text)"),
        (CRITICAL_SECURITY,),
        1,
        "synthetic_bug",
        "eval is introduced",
    ),
    EvaluationSample(
        "python_exec",
        "python",
        _py_diff("rules.py", "+    exec(script_text)\n+    return True"),
        (CRITICAL_SECURITY,),
        1,
        "synthetic_bug",
        "exec is introduced",
    ),
    EvaluationSample(
        "python_multi_timeout_sql",
        "python",
        _py_diff("sync.py", '+    resp = requests.post(url)\n+    query = f"INSERT INTO logs VALUES ({resp.text})"\n+    return db.execute(query)'),
        (MEDIUM_TIMEOUT, HIGH_SQL),
        2,
        "open_source_patch_like",
        "requests timeout and SQL interpolation risks",
    ),
    EvaluationSample(
        "python_multi_error_security",
        "python",
        _py_diff("runner.py", "+    try:\n+        exec(payload)\n+    except:\n+        return False"),
        (CRITICAL_SECURITY, MEDIUM_ERROR),
        2,
        "open_source_patch_like",
        "dynamic execution and broad exception",
    ),
    EvaluationSample(
        "python_negative_parameterized_sql",
        "python",
        _py_diff("repo.py", '+    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,))'),
        (),
        0,
        "negative",
        "parameterized SQL",
    ),
    EvaluationSample(
        "python_negative_specific_except",
        "python",
        _py_diff("worker.py", "+    try:\n+        run_job()\n+    except ValueError:\n+        return None"),
        (),
        0,
        "negative",
        "specific exception handler",
    ),
    EvaluationSample(
        "python_negative_logging",
        "python",
        _py_diff("log.py", '+    logger.info("request completed", extra={"path": path})\n+    return True'),
        (),
        0,
        "negative",
        "safe logging change",
    ),
    EvaluationSample(
        "python_delete_request_no_timeout",
        "python",
        _py_diff("client.py", "+    resp = requests.delete(url)\n+    return resp.status_code"),
        (MEDIUM_TIMEOUT,),
        1,
        "synthetic_bug",
        "requests.delete has no timeout",
    ),
    EvaluationSample(
        "python_patch_request_no_timeout",
        "python",
        _py_diff("client.py", "+    resp = requests.patch(url, json=payload)\n+    return resp.json()"),
        (MEDIUM_TIMEOUT,),
        1,
        "synthetic_bug",
        "requests.patch has no timeout",
    ),
)


def load_evaluation_dataset() -> tuple[EvaluationSample, ...]:
    return EVALUATION_DATASET
