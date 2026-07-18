# Unity 子系统约束

- Unity Editor 锁定为 `6000.3.19f1`。
- `Assets`、`Packages`、`ProjectSettings` 和所有 `.meta` 必须成对保留。
- Milestone 1 只允许圆形灰盒场地、固定种子自动战斗、分波次 telemetry 和 smoke 修复，不新增玩法。
- 自动测试必须显式记录 seed 和 run mode；同一 contract 与 seed 的稳定计数必须可重复。
- 配置字段必须通过现有 runtime contract 进入 C#，不得在 Scene 中复制另一套目标值。
- `Assets/Resources/LocalThirdParty/` 是本地忽略目录。
- 已提交 Scene、Prefab 和 ScriptableObject 不得序列化引用本地第三方资产。
- `CharacterViewResolver` 找不到本地角色时必须回退到 `Resources/Characters/Placeholder`。
- Milestone 2 的 FBX、贴图、Prefab 和动画必须位于 `Assets/Resources/LocalThirdParty/`，不得被 Git 跟踪。
- 已提交代码只能通过资源路径解析本地角色，不能保存本地 Prefab GUID。
- 角色动画、武器视图和命中反馈只能改变表现，不能改变命中判定与伤害数值。
- 完成变更后运行根目录 `scripts/smoke-unity.ps1`。
