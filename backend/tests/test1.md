# 后端测试

`tests/test1.py` 使用 `.env` 配置的真实 MySQL，不使用临时数据库或模拟数据库。

## 运行

在项目根目录启动 MySQL：

```powershell
docker compose --env-file backend/.env up -d mysql
```

然后进入后端目录：

```powershell
cd backend
uv sync
uv run pytest -v tests/test1.py
```

也可以执行 `uv run pytest -q`，自动发现并运行测试。

`.env` 需要包含 `config.py` 要求的数据库、JWT 和跨域配置。测试通过
`TestClient` 调用真实应用并执行启动/关闭逻辑，无需另外启动 Uvicorn。
如果表不存在，应用启动逻辑会建表。

## 覆盖范围

- 图书新增、查询、删除，以及重复删除。
- 分页总数、翻页和超出末页。
- 书名、价格、必填字段、分页参数和图书 ID 校验。
- 缺失、格式错误、过期、缺少用户标识及签名错误的 Token。
- HTTP 状态码和响应体业务码；当前不存在图书的响应为 HTTP 200、`code=404`。

## 数据影响

- 会短暂写入名称以 `pytest-` 开头的测试图书，并推进自增 ID。
- 每个用例结束时，仅按自己创建的 ID 删除记录；断言失败也会尝试清理。
- 不清空表，不删除已有图书；强制终止进程可能留下测试记录。
- 分页测试依赖总数稳定，运行期间不要让其他程序增删图书，也不要并行运行测试。
- 测试会真实写库；运行前确认 `.env` 指向允许测试的数据库。