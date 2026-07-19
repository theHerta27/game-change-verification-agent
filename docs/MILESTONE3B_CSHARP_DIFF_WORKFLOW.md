# Milestone 3B：人工 C# Diff 质量闭环

## 1. 这阶段解决什么问题

配置变更只能调整现有数据。当需求涉及“运行时不支持空参数”“代码里出现每帧磁盘读取”“需要修改 C# 行为”时，仅生成 JSON 配置已经不够。

Milestone 3B 先解决代码变更的**审查与验证**，暂不解决代码自动生成：

```text
开发者人工编写 C# Diff
-> Patch Safety Gate
-> Quality Review Agent
-> 人工批准
-> 复制 Unity 源工程
-> 在隔离副本应用补丁
-> Unity 编译与固定种子自动试玩
-> 人工接受 / 要求修订 / 回滚
```

系统不会让 LLM 写补丁，也不会把候选补丁自动合并到主仓库。因此这仍然是受控研发工具链，不是 Code Change Agent。

## 2. 各模块分别负责什么

### 人工输入

开发者提供：

- 变更标题；
- 变更原因；
- 标准 unified diff；
- 审批人和最终决策说明。

示例补丁位于 `examples/csharp/runtime_args_null_guard.patch`。它只为 `RuntimeRunSettings.FromArgs` 增加空参数保护，不改变玩法和数值。

### Patch Safety Gate

`workflow/code_patch.py` 是确定性 Gate，不是 Agent。它在调用 LLM 前检查：

- 只允许 `game-unity/Assets/**/*.cs` 中已经存在的文件；
- 不允许新增、删除、重命名、二进制补丁和路径穿越；
- 限制文件数、变更行数和补丁体积；
- 拒绝进程启动、原生调用、网络访问、危险删除等高风险 API；
- 保存补丁 SHA256，防止审批后被替换。

`examples/csharp/unsafe_process_launch.patch` 用于证明危险补丁会在进入 Agent 和 Unity 前被拦截，不应进入实际验证。

### Quality Review Agent

现有 DevQuality Review Agent 读取通过安全门的 C# Diff。确定性静态规则负责发现：

- `Update`、`FixedUpdate`、`LateUpdate` 中的文件 I/O 或全局查找；
- 每帧创建或销毁对象；
- 宽泛异常捕获；
- 进程或原生代码执行；
- 在固定种子运行主流程中引入 `UnityEngine.Random`。

Mock Provider 会把静态提示稳定转换为 Finding 和 Test Suggestion，适合回归。真实 Provider 可以补充语义审查，但不能绕过安全门、结构校验或人工审批。

### 隔离应用 Tool

人工批准后，系统把以下 Unity 源目录复制到：

```text
runtime-artifacts/code-workflows/<workflow_id>/workspace/game-unity/
```

复制范围只有：

- `Assets`；
- `Packages`；
- `ProjectSettings`。

不复制 `Library`、`Temp`、`Logs`、`Builds`、`UserSettings` 和本地第三方角色资源。补丁按 hunk 上下文逐行应用，只要原始行不匹配就立即失败。主仓库文件在应用前后都计算 SHA256，`baseline_unchanged` 必须为 `true`。

### Unity 验证 Tool

`scripts/validate-code-workflow.ps1` 在隔离工程中执行：

1. Unity C# 编译与 Windows Development Build；
2. `RuntimeDemoBuilder` 中的战斗距离、运行参数和角色解析 smoke；
3. 相同 seed 的两次无图形 Player 自动试玩；
4. telemetry 完整性和固定种子重复性评测；
5. 当前 runtime target 评测。

当前工程没有 Unity Test Framework 测试程序集，所以报告使用准确名称“编辑器确定性 smoke”，不宣称已经运行 EditMode/PlayMode Test Framework。

## 3. 如何理解两类通过率

代码补丁验证和策划运行目标是两个层次：

- `repeatability_rate=100%`：两次相同 seed 的关键计数一致，说明回归环境稳定；
- `runtime_target_pass_rate=60%`：当前 Training Sword 配置只满足一部分策划目标，例如通关时间仍可能过快。

因此，代码补丁可以在编译、smoke 和重复性方面通过，同时继续暴露既有配置的平衡偏差。这不是矛盾，而是证据分层：

```text
代码是否可构建、可重复运行？        -> 代码质量结论
当前配置是否达到 60–90 秒等目标？   -> 策划效果结论
```

## 4. Web Console 操作

1. 启动后端和前端。
2. 切换到“开发者调试”。
3. 找到“人工 C# Diff 质量闭环”。
4. 使用默认安全示例或粘贴人工编写的 unified diff。
5. 点击“提交补丁并审查”。
6. 查看安全门、Finding 和 Test Suggestion。
7. 填写审批人，批准后创建隔离工作区。
8. 点击“运行 Unity 验证”，页面轮询后台状态。
9. 查看编译、编辑器 smoke、Player 双跑、重复性和运行目标证据。
10. 记录“接受，待人工合并”“要求修订”或“回滚候选”。

“接受”只表示证据支持后续人工合并，响应中的 `patch_applied_to_repository` 始终为 `false`。

## 5. API

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/api/code-workflows` | 提交人工 Diff 并运行安全门与质量审查 |
| GET | `/api/code-workflows/{workflow_id}` | 查询状态和证据 |
| POST | `/api/code-workflows/{workflow_id}/approve` | 人工批准 |
| POST | `/api/code-workflows/{workflow_id}/workspace` | 创建隔离工程并应用补丁 |
| POST | `/api/code-workflows/{workflow_id}/validate` | 后台启动 Unity 验证 |
| POST | `/api/code-workflows/{workflow_id}/decision` | 接受、要求修订或回滚 |
| GET | `/api/code-workflows/{workflow_id}/artifacts/{name}` | 查看白名单证据文件 |

## 6. 失败如何处理

- 补丁越界：状态为 `rejected`，不进入 Agent 和 Unity。
- Agent 输出或 Validator 失败：状态为 `rejected` 或 `failed`，保留 `quality_review.json`。
- 补丁上下文不匹配：隔离应用失败，主仓库不变。
- Unity 编译、许可证或 Player 失败：写入 `validation_result.json` 和日志。
- 后台进程异常退出且没有结果：工作流自动转为 `ValidationProcessError`，不会一直卡在“验证中”。
- PowerShell 生成的 BOM JSON 使用 `utf-8-sig` 读取，Windows 本地运行可正常推进状态。

## 7. 当前边界与后续方向

当前已经证明“人工代码变更可以被受控审查和回归”，但还没有：

- 自动生成 C# Patch；
- 自动合并 Git；
- Unity Test Framework 的 EditMode/PlayMode 测试程序集；
- 独立 worktree、代码签名或操作系统级沙箱；
- 多个真实游戏场景的代码变更 benchmark。

Post-MVP 的 Code Change Agent 必须建立在这些门禁之上，输出候选 Patch 后仍走同一套人工审批和隔离验证，不能获得直接修改主仓库的权限。
