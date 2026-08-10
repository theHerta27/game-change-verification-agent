# 工具链锁定

```yaml
unity:
  editor_version: 6000.3.19f1
  executable_env: GAMECHANGE_UNITY_EDITOR
  project_path: game-unity

python:
  required_version: ">=3.10"
  verified_version: 3.13.5
  dependency_source: services/agent-python/pyproject.toml

node:
  detected_version: 22.16.0
  dependency_lock: web-console/package-lock.json

unreal:
  editor_version: 5.8.1
  executable_env: GAMECHANGE_UE_EDITOR

blender:
  target_version: 4.5.11 LTS
  status: portable_installed
  build_hash: 4db51e9d1e1e
  archive_sha256: e11d3a8e4d4249be5a7db4a9325c1f670037d4233467c3b0bda181001efe44d3

mmd_tools:
  repository: MMD-Blender/blender_mmd_tools
  target_version: v4.5.10
  status: installed
  release_commit: 325d7d4
  commit: 325d7d456e8e186d75828349ddefef7ee5ace2ec
  archive_sha256: 6e7c232379499ac045ce3fcd950a1b60b61c1645a4263d5fc5c64d71c6654362
```

工具链安装在 Git 忽略的 `local-tools/`。本地机器可读取 `local-tools/toolchain-lock.json` 获取可执行文件路径和完整版本输出。

版本核对说明：截至 2026-07-18，Blender 4.5 LTS 当前补丁版为 `4.5.11`；MMD Tools 官方最新稳定版为 `v4.5.10`，release commit 短 SHA 为 `325d7d4`。原迁移计划中的 MMD Tools `v4.5.11` 不存在，已按官方 release 更正。
