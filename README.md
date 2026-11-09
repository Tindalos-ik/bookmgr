# 图书管理系统

## Windows 一键启动

安装 Python 3.12+、uv、Node.js 24（含 npm），保证 `uv`、`node`、`npm.cmd` 在 PATH 中。首次安装依赖，在 PowerShell 执行（路径按实际位置调整）：

```powershell
Set-Location 'D:\myproject\bookmgr\backend'
uv sync --frozen
Set-Location '..\frontend'
npm.cmd ci
```

启动前确认 `backend/.env` 已配置完整，并指向可连接的**已有 MySQL 数据库**；配置项参考 `backend/.env.example` 和后端文档。示例本机 MySQL 端口为 `127.0.0.1:3307`，以已有配置为准。脚本不启动、初始化或备份数据库；后端自身的正常启动流程会连接数据库并检查、创建缺失的表。请使用预期的已有数据库，勿随意改动连接配置。

双击根目录 `start.cmd`，或从任意工作目录调用完整路径：

```powershell
& 'D:\myproject\bookmgr\start.cmd'
```

在 cmd 中可直接运行 `"D:\myproject\bookmgr\start.cmd"`。脚本使用自身所在目录定位前后端，支持路径含空格，不依赖调用时的工作目录。

- 后端窗口执行 `uv run --no-sync main.py`，仅使用已安装环境；依赖缺失时按上面的命令安装并处理错误。
- 前端窗口执行 `npm.cmd run dev -- --port 5173 --strictPort`。
- 前端目标地址：<http://localhost:5173/>；后端接口文档：<http://localhost:8000/docs>（接口定义：<http://localhost:8000/openapi.json>）。
- 两个独立终端显示真实运行日志。打开窗口仅代表已提交启动，须在日志出现后端 `Application startup complete`、前端 Vite 地址后，再访问对应地址确认。
- 启动前发现 `8000` 或 `5173` 被占用会报错退出；脚本不终止已有进程、不复用未知服务、不自动换端口。请先确认占用服务归属，再手动关闭。
- 停止时分别在两个服务窗口按 `Ctrl+C`，若提示终止批处理则输入 `Y`。确认服务停止后关闭窗口；服务意外退出时窗口会保留日志及退出码。主启动窗口退出不会停止两个服务。

后端和前端保持各自现有实现；前端演示的数据与使用方式见前端说明。开发服务器会监听网络接口，请仅在可信开发环境运行。

## 文档索引

- [前端使用说明](frontend/README.md)：演示账号、页面功能与浏览器数据。
- [后端说明](docs/图书管理系统后端%28古法部分.md)：后端接口与实现说明。
- [后端环境配置示例](backend/.env.example)：已有 MySQL 的连接配置项。
