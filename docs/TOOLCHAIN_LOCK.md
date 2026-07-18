# 工具链锁定

```yaml
unity:
  editor_version: 6000.3.19f1
  executable: E:/Unity6/6000.3.19f1/Editor/Unity.exe
  project_path: D:/Desktop/agentic-game-rd/game-unity

python:
  required_version: ">=3.10"
  verified_version: 3.13.5
  dependency_source: services/agent-python/pyproject.toml

node:
  detected_version: 22.16.0
  dependency_lock: web-console/package-lock.json

blender:
  target_version: 4.5 LTS
  status: not_installed
  installer_sha256: pending_installation

mmd_tools:
  repository: MMD-Blender/blender_mmd_tools
  target_version: v4.5.11
  status: not_installed
  commit: pending_installation
  archive_sha256: pending_installation
```

Blender 与 MMD Tools 的精确补丁版本、commit 和文件哈希必须在第一次成功执行 `PMX -> Blender -> FBX -> Unity` 技术验证时补齐，未安装前不得虚构。
