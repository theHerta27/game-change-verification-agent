# Milestone 2：灵梦角色表现层

## 目标

Milestone 2 验证第三方角色资产能否作为“可替换表现层”接入 Unity 测试床，同时不污染战斗逻辑、配置契约和 Git 仓库。

核心关系是：

```text
战斗对象 Player
├── 位置、攻击、技能、生命：RuntimeDemoBootstrap 管理
└── 角色外观：CharacterViewResolver 选择
    ├── 本机有 Reimu.prefab -> 灵梦表现
    └── 本机没有 Reimu.prefab -> Placeholder
```

灵梦模型不是新的玩家逻辑，也不是 Agent。它只是同一个 Player 的本地 View。

## 工具链

- Blender `4.5.11 LTS`
- MMD Tools `v4.5.10`
- Unity `6000.3.19f1`
- Unity 交换格式：FBX

官方依据：

- Blender LTS 下载：`https://www.blender.org/download/lts/4-5/`
- MMD Tools：`https://github.com/MMD-Blender/blender_mmd_tools`
- MMD Tools v4.5.10：`https://github.com/MMD-Blender/blender_mmd_tools/releases/tag/v4.5.10`

MMD Tools 官方说明 v4.x 支持 Blender 4.2–5.1。原计划中的插件 v4.5.11 不存在，因此锁定当前稳定版 v4.5.10。

## 自动化流程

### 1. 准备 Blender

```powershell
.\scripts\bootstrap-blender.ps1
```

脚本下载 portable Blender 和 MMD Tools tag archive，记录 SHA256 与完整 commit。它不修改系统 PATH，不注册文件关联。

### 2. 转换 PMX

```powershell
.\scripts\convert-reimu.ps1
```

Blender 后台脚本只导入：

- Mesh
- Armature
- Morphs

本阶段不导入 MMD 刚体和关节。转换输出 FBX、Blend、贴图副本和 `conversion_report.json`。

### 3. 导入 Unity

```powershell
.\scripts\import-reimu-unity.ps1
```

Unity Editor 自动完成：

- 导入 FBX；
- 将角色高度归一化为 2 米；
- 根据 MMD 材质语义绑定 12 张主贴图；
- 创建本地 Standard 材质；
- 添加轻量待机/移动表现组件；
- 保存 `Resources/LocalThirdParty/Reimu/Reimu.prefab`；
- 验证 CharacterViewResolver 选择本地角色。

### 4. 运行验证

```powershell
.\scripts\smoke-reimu-presentation.ps1
```

该脚本执行：

```text
Unity Build
-> Milestone 1 固定种子双跑
-> 本地灵梦截图
-> 截图像素检查
-> --force-placeholder 回退截图
```

## 当前模型数据

| 项目 | 结果 |
|---|---:|
| Mesh | 1 |
| Blender Armature | 1 |
| Blender Bones | 301 |
| Unity Bones | 297 |
| Vertices | 15,913 |
| Materials | 12 |
| Bound Textures | 12 |
| Normalized Height | 2.0m |
| MMD Physics | disabled |

## 表现功能

- 灵梦贴图和基础材质。
- 不依赖骨骼动作的轻量待机/移动摆动。
- 御札与阴阳玉灰盒焦点物。
- 普通攻击和技能命中的短时脉冲反馈。
- 更接近角色的跟随镜头。

这些功能只改变画面，不改变伤害、攻击范围、冷却、敌人和波次。

## 为什么不提交 Prefab

Unity Prefab 会通过 `.meta` GUID 引用 FBX、材质和贴图。如果只提交 Prefab 而不提交第三方模型，其他机器会看到 Missing 引用；如果把全部资产提交，又会违反本项目的分发边界。

因此已提交代码只保存资源路径：

```text
LocalThirdParty/Reimu/Reimu
```

本机有资源时动态加载，没有资源时回退 Placeholder。

## 当前边界

- 当前摆动不是正式骨骼动画状态机。
- 没有还原 MMD 裙摆物理、IK 和表情。
- 自动玩家验证回归稳定性，不代表真人手感。
- 模型仅用于个人学习、测试和面试演示，不公开分发。
