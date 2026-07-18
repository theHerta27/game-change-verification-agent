# Unity 子系统约束

- Unity Editor 锁定为 `6000.3.19f1`。
- `Assets`、`Packages`、`ProjectSettings` 和所有 `.meta` 必须成对保留。
- Milestone 0 不新增玩法；只允许迁移、占位角色、本地角色解析和 smoke 修复。
- 配置字段必须通过现有 runtime contract 进入 C#，不得在 Scene 中复制另一套目标值。
- `Assets/Resources/LocalThirdParty/` 是本地忽略目录。
- 已提交 Scene、Prefab 和 ScriptableObject 不得序列化引用本地第三方资产。
- `CharacterViewResolver` 找不到本地角色时必须回退到 `Resources/Characters/Placeholder`。
- 完成变更后运行根目录 `scripts/smoke-unity.ps1`。

