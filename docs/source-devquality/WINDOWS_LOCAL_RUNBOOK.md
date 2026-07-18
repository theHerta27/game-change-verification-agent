# Windows 本地启动与排障

## 为什么只运行 npm run dev 不够

`npm run dev` 只启动 React/Vite 前端。点击“运行代码审查”时，浏览器还要访问：

```text
Frontend :5173
  -> Go Backend :18080
  -> PostgreSQL :5432 / Redis :6379
  -> Python Agent Service :8010
```

如果 `18080` 没有监听，浏览器无法建立 HTTP 连接，会显示：

```text
任务 尚未创建
Failed to fetch
```

`.env` 只提供配置，不会自动启动任何进程。关闭终端或重启电脑后，需要重新启动应用服务。

## 推荐：一条命令启动应用服务

先确认 PostgreSQL 已安装，Redis 可以通过 `redis-server.exe` 启动。然后在项目根目录运行：

```powershell
cd D:\Desktop\DevQuality-Agent
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_local.ps1
```

脚本会：

1. 检查或尝试启动 PostgreSQL、Redis。
2. 启动 Python Agent Service。
3. 提示输入 PostgreSQL 密码，仅用于启动 Go 子进程，不写文件。
4. 启动 Go Backend。
5. 启动前端。
6. 输出五个端口和 health 状态。

如果当前 PowerShell 已设置 `DATABASE_URL`，脚本不会询问密码：

```powershell
$env:DATABASE_URL='postgres://postgres:<PASSWORD>@127.0.0.1:5432/devquality_agent?sslmode=disable'
.\scripts\start_local.ps1
Remove-Item Env:DATABASE_URL
```

不要把真实密码写入 README、脚本或 Git。

## 快速检查缺哪个服务

```powershell
cd D:\Desktop\DevQuality-Agent
.\scripts\check_local.ps1
```

正常结果应包含：

| 组件 | 端口 | 预期 |
|---|---:|---|
| PostgreSQL | 5432 | Listening=True |
| Redis | 6379 | Listening=True |
| Python Agent | 8010 | Health=ok |
| Go Backend | 18080 | Health=ok |
| Frontend | 5173 | Listening=True |

## 手动启动：五个 PowerShell 窗口

### 1. PostgreSQL

PostgreSQL 通常作为 Windows 服务自动启动：

```powershell
Get-Service | Where-Object Name -Like 'postgresql*'
```

如果未运行，请在管理员 PowerShell 执行，服务名以实际输出为准：

```powershell
Start-Service postgresql-x64-17
```

### 2. Redis

如果 `redis-server.exe` 在 PATH：

```powershell
redis-server.exe
```

否则进入本机 `Redis-x64-3.0.504` 目录运行：

```powershell
cd <REDIS_INSTALL_DIR>
.\redis-server.exe
```

该窗口需要保持运行。

### 3. Python Agent Service

```powershell
cd D:\Desktop\DevQuality-Agent\agent_service
python -m agent_service.server --host 127.0.0.1 --port 8010
```

检查：

```powershell
curl.exe --max-time 5 http://127.0.0.1:8010/healthz
```

Real 服务端默认配置从 `agent_service/.env` 读取。Mock 模式不需要 LLM key。

### 4. Go Backend

```powershell
cd D:\Desktop\DevQuality-Agent\backend
$env:DATABASE_URL='postgres://postgres:<PASSWORD>@127.0.0.1:5432/devquality_agent?sslmode=disable'
$env:REDIS_ADDR='127.0.0.1:6379'
$env:AGENT_SERVICE_URL='http://127.0.0.1:8010'
$env:SERVER_ADDR=':18080'
& 'C:\Program Files\Go\bin\go.exe' run .\cmd\server
```

检查：

```powershell
curl.exe --max-time 5 http://127.0.0.1:18080/healthz
```

### 5. Frontend

```powershell
cd D:\Desktop\DevQuality-Agent\frontend
npm run dev
```

打开：`http://127.0.0.1:5173`

## 首次数据库初始化

只需在首次安装或新增 migration 后执行。`psql.exe` 路径按本机 PostgreSQL 版本调整：

```powershell
cd D:\Desktop\DevQuality-Agent
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h 127.0.0.1 -p 5432 -U postgres -d devquality_agent -f .\backend\migrations\001_init.sql
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h 127.0.0.1 -p 5432 -U postgres -d devquality_agent -f .\backend\migrations\002_real_llm.sql
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h 127.0.0.1 -p 5432 -U postgres -d devquality_agent -f .\backend\migrations\003_real_llm_debug.sql
```

## 错误如何快速定位

### `Failed to fetch`，任务尚未创建

优先检查：

```powershell
curl.exe --max-time 5 http://127.0.0.1:18080/healthz
```

失败说明 Go Backend 没启动、端口不对或前端 API 地址错误。

### 任务创建了，但一直 pending

检查 Go worker 和数据库：

```powershell
Get-Content -Tail 200 D:\Desktop\DevQuality-Agent\backend\logs\server.log
```

### 任务 failed，提示 Agent Service 错误

检查：

```powershell
curl.exe --max-time 5 http://127.0.0.1:8010/healthz
Get-Content -Tail 200 D:\Desktop\DevQuality-Agent\agent_service\logs\server.log
```

### Mock 可以，Real 提示 `real LLM config missing`

说明服务都正常，但 `agent_service/.env` 缺少默认模型配置，或前端没有选择临时覆盖配置。

### Go 启动后数据库连接失败

检查 `DATABASE_URL` 中数据库名、用户名、密码和端口。项目数据库名是 `devquality_agent`。

## 停止应用服务

```powershell
cd D:\Desktop\DevQuality-Agent
.\scripts\stop_local.ps1
```

该脚本只停止 8010、18080、5173，不停止 PostgreSQL 和 Redis。
