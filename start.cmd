@rem Windows 一键启动入口：检查已有依赖与端口，在独立窗口运行后端和前端。
@echo off
chcp 65001 >nul
setlocal
if "%~1"=="--backend" goto backend
if "%~1"=="--frontend" goto frontend
if not "%~1"=="" (
    echo [错误] 不支持的启动参数：%~1
    goto failed
)
pushd "%~dp0" || goto failed

rem 启动前检查工具与已安装依赖，后端窗口先执行当前库迁移。
where uv >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 uv，请安装 uv 并重新打开终端。
    goto failed
)
where node >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请安装 Node.js 24 并重新打开终端。
    goto failed
)
where npm.cmd >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 npm.cmd，请检查 Node.js 安装与 PATH。
    goto failed
)
if not exist "backend\.env" (
    echo [错误] 缺少 backend\.env，请按已有后端配置填写并连接已有 MySQL。
    goto failed
)
if not exist "backend\.venv\Scripts\python.exe" (
    echo [错误] 缺少后端虚拟环境，请在 backend 目录执行 uv sync --frozen。
    goto failed
)
"backend\.venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12+ required'; import fastapi, uvicorn, aiomysql, sqlalchemy, pydantic_settings, jose, multipart, passlib, alembic"
if errorlevel 1 (
    echo [错误] 后端依赖检查失败，请在 backend 目录执行 uv sync --frozen 并处理上方错误。
    goto failed
)
if not exist "frontend\node_modules\.bin\vite.cmd" (
    echo [错误] 缺少前端依赖，请在 frontend 目录执行 npm.cmd ci。
    goto failed
)

rem 同时检查 IPv4 与 IPv6 监听；任何占用均报错，不终止或复用已有服务。
powershell.exe -NoProfile -Command "$ErrorActionPreference = 'Stop'; $ports = @(8000, 5173); $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners(); $busy = @($listeners | Where-Object { $_.Port -in $ports } | Select-Object -ExpandProperty Port -Unique); if ($busy.Count -gt 0) { Write-Host ('[错误] 启动端口已占用：' + ($busy -join ', ') + '。请确认占用服务的归属并手动关闭；脚本不会停止其他进程。'); exit 1 }"
if errorlevel 1 goto failed

start "Bookmgr Backend" "%ComSpec%" /d /k call "%~f0" --backend
if errorlevel 1 goto failed
start "Bookmgr Frontend" "%ComSpec%" /d /k call "%~f0" --frontend
if errorlevel 1 goto failed
echo 已打开两个服务窗口，请查看各自日志确认启动结果。
echo 前端目标地址：http://localhost:5173/
echo 后端文档目标地址：http://localhost:8000/docs
echo 窗口打开不代表服务已就绪；关闭方式见 README.md。
popd
exit /b 0

rem 后端运行入口，参数 --backend；工作目录固定为脚本旁的 backend。
:backend
title Bookmgr Backend
pushd "%~dp0backend" || goto failed
echo 启动后端，使用已有 .env 与 MySQL；请查看下方真实启动日志。
uv run --no-sync alembic upgrade head
if errorlevel 1 goto service_exit
uv run --no-sync main.py
goto service_exit

rem 前端运行入口，参数 --frontend；固定端口，端口冲突时直接报错。
:frontend
title Bookmgr Frontend
pushd "%~dp0frontend" || goto failed
echo 启动前端，固定端口 5173；请查看下方真实启动日志。
call npm.cmd run dev -- --port 5173 --strictPort
goto service_exit

rem 保留服务退出码与输出，参数为空；外层 cmd /k 保持日志窗口可见。
:service_exit
set "service_code=%errorlevel%"
echo.
echo 服务已退出，退出码：%service_code%。日志保留在此窗口。
popd
exit /b %service_code%

rem 启动检查失败时保留错误窗口，参数为空。
:failed
echo.
echo 启动失败，请处理上方错误后重试。
pause
exit /b 1
