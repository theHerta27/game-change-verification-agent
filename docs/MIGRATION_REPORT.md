# Milestone 0 迁移报告

## 状态

`complete`

## 已迁移

- GameConfig Python、tests、examples、React 源码与 Unity 源工程。
- DevQuality Python 质量审查核心、tests、patch 样本与评测数据。
- GameConfig phase0/1/2/3/final 演示产物。
- 灵梦原始压缩包与解压文件，均位于 Git 忽略目录。

## 架构处理

- 新仓库只有一个 Python 运行时和一个 React 控制台。
- GameConfig API 保持不变，新增 `/api/quality/health` 与 `/api/quality/review`。
- DevQuality Go、旧前端和数据库部署未导入。
- Unity 使用运行时角色解析，不序列化引用本地模型。

## 验证结果

- 来源清单：215 个导入文件，逐文件 SHA256 验证通过。
- Python：`91 passed, 1 warning`，GameConfig、DevQuality 与统一 FastAPI 测试全部通过。
- Web：TypeScript 与 Vite production build 通过，最终构建耗时 2.61 秒。
- Unity：`6000.3.19f1` Windows Development Build 通过。
- Character View：无本地资产回退与本地候选替换两条分支通过。
- Unity auto-run：3 波、5 个敌人、27 次普通攻击、2 次技能，status 为 `completed`。
- API：`GET /api/health` 与 `GET /api/quality/health` 均返回 200。
- 清洁检查：源目录哈希未变化；无嵌套 Git、禁用组件、真实 `.env`、缺失 `.meta` 或被跟踪的本地资产。

唯一 warning 来自 FastAPI/Starlette TestClient 对当前 httpx 适配层的弃用提示，不影响本轮行为。
