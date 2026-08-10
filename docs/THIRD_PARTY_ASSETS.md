# 第三方资产说明

## 博丽灵梦 MMD 模型

本地来源（不进入 Git）：

```text
用户自行准备的 MMD_REIMU.ZIP.zip
```

项目内本地归档：

```text
local-assets/reimu/source/
local-assets/reimu/extracted/
local-assets/reimu/converted/
```

上述目录和 Unity 本地角色目录均被 `.gitignore` 排除。

模型包自带说明表明：模型可用于渲染、视频、自制游戏和改造；超出同人流通的企业用途需要联系上海爱丽丝幻乐团。项目采用以下边界：

- 仅用于个人本地学习、测试和面试演示。
- 不在 Git 仓库、发布包或公开下载中分发模型和贴图。
- 不宣称模型由项目作者制作。
- 若未来公开发布或进入企业用途，重新核对权利方规则并取得必要授权。

## 技术边界

- PMX 是本地原始格式。
- FBX 是本项目进入 Unity 的标准交换格式。
- 本地 Prefab 只允许放在 `Assets/Resources/LocalThirdParty/Reimu/Reimu.prefab`。
- 已提交资产不得通过 Unity GUID 引用本地 Prefab。
- 自动测试模式不依赖第三方模型或音频。

## 本地转换记录

Milestone 2 已完成 `R_spring.pmx -> Blender -> FBX -> Unity` 本地验证：

- PMX SHA256：`d137bfe8a432bf53dd78d69f68b93d2655821d4d5e3c67f176ba193bd781238e`
- Blender：`4.5.11 LTS`，build `4db51e9d1e1e`
- MMD Tools：`v4.5.10`
- 网格：1
- Blender 骨骼：301
- Unity 骨骼：297
- 顶点：15,913
- 材质：12
- MMD 物理：未导入

本地输出：

```text
local-assets/reimu/converted/spring/
game-unity/Assets/Resources/LocalThirdParty/Reimu/
runtime-artifacts/reimu-import/
```

上述目录中的模型产物和运行证据均不提交 Git。
