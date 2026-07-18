# Real LLM Smoke Cases

本目录用于前端手动或半自动真实模型 smoke，不计入 Phase 4A mock evaluation 指标。

| 样本 | 语言 | 类型 | 预期分类 |
|---|---|---|---|
| `go_http_no_timeout_positive.patch` | Go | positive | `timeout_missing` |
| `go_response_body_not_closed_positive.patch` | Go | positive | `resource_leak` |
| `go_context_timeout_safe_negative.patch` | Go | safe negative | 无明显 finding |
| `python_requests_no_timeout_positive.patch` | Python | positive | `timeout_missing` |
| `python_sql_injection_positive.patch` | Python | positive | `sql_injection` |
| `python_parameterized_sql_safe_negative.patch` | Python | safe negative | 无明显 finding |
| `python_eval_positive.patch` | Python | positive | `unsafe_eval` |

运行时将 patch 内容粘贴到 Demo Console，选择对应语言和真实模型。真实模型输出具有非确定性，人工验收应同时检查路径、行号、证据和测试建议关联。
