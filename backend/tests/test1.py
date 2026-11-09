"""连接当前真实 MySQL 验证消费者权限和业务，仅清理自身测试账户与图书。"""

from pathlib import Path
from datetime import timedelta
from uuid import uuid4
from urllib.parse import quote
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, func
from dependencies import create_access_token, password_context
from database import AsyncSessionLocal, BookDB, UserDB, AuthSessionDB
from main import app


@pytest.fixture(scope="session")
def client():
    """提供使用真实数据库和原始依赖的 HTTP 客户端；无参数。"""
    with TestClient(app) as instance:
        yield instance


@pytest.fixture
def registered_user(client):
    """通过 client 注册独立账户，结束时仅删除本 fixture 创建的用户ID。"""
    ids = []

    async def remove_users():
        """从真实数据库删除 ids 中本 fixture 创建的用户及级联记录；无参数。"""
        async with AsyncSessionLocal() as db:
            await db.execute(delete(UserDB).where(UserDB.id.in_(ids)))
            await db.commit()

    def register(password="测试 password 123", username=None):
        """通过真实接口注册 username 和 password，返回用户资料及原始密码。"""
        username = username or "pytest-" + uuid4().hex
        response = client.post(
            "/auth/register", json={"username": username, "password": password}
        )
        assert response.status_code == 200, response.text
        user = response.json()["data"]
        ids.append(user["id"])
        return {**user, "password": password}

    try:
        yield register
    finally:
        client.portal.call(remove_users)


@pytest.fixture
def accounts(client, registered_user):
    """通过 client 和 registered_user 创建自有账户，仅提升自有管理员角色。"""
    result = {}

    async def promote(user_id):
        """将真实数据库中本 fixture 创建的 user_id 设为管理员。"""
        async with AsyncSessionLocal() as db:
            user = await db.get(UserDB, user_id)
            user.role = "admin"
            await db.commit()

    for role in ("admin", "reader"):
        user = registered_user()
        if role == "admin":
            client.portal.call(promote, user["id"])
        response = client.post(
            "/auth/token",
            data={"username": user["username"], "password": user["password"]},
        )
        assert response.status_code == 200, response.text
        result[role] = {
            "Authorization": "Bearer " + response.json()["data"]["access_token"]
        }
    yield result


@pytest.fixture
def create_book(client, accounts):
    """通过 client 和 accounts 创建独立前缀图书，逐条清理自身 ID。"""
    ids = []

    def create(**changes):
        """以 changes 覆盖有效完整资料并返回已创建图书。"""
        payload = {
            "name": "pytest-" + uuid4().hex,
            "author": "测试作者",
            "category": "pytest分类",
            "description": "测试说明",
            "price": 0,
            "cover": "",
            "published": True,
        }
        payload.update(changes)
        response = client.post("/books", json=payload, headers=accounts["admin"])
        assert response.status_code == 200, response.text
        book = response.json()["data"]
        ids.append(book["id"])
        return book

    yield create
    for book_id in ids:
        response = client.delete(f"/books/{book_id}", headers=accounts["admin"])
        assert response.status_code in (200, 404), response.text


def test_lifecycle_search_pagination(client, accounts, create_book):
    """使用 client、accounts、create_book 验证完整编辑及独立查询分页。"""
    prefix = "pytest-" + uuid4().hex
    books = [create_book(name=f"{prefix}-{i}") for i in range(3)]
    admin = accounts["admin"]
    for sort in ("newest", "name", "author"):
        pages = [
            client.get(
                "/books",
                params={
                    "q": prefix,
                    "category": "pytest分类",
                    "sort": sort,
                    "page": p,
                    "page_size": 2,
                },
                headers=admin,
            ).json()["data"]
            for p in (1, 2)
        ]
        assert [p["total"] for p in pages] == [3, 3]
        assert {b["id"] for p in pages for b in p["list"]} == {b["id"] for b in books}
        assert len(pages[0]["list"]) == 2 and len(pages[1]["list"]) == 1
    book = books[0]
    payload = {
        k: book[k]
        for k in (
            "name",
            "author",
            "category",
            "description",
            "price",
            "cover",
            "published",
        )
    }
    payload.update(author=prefix, description="修改后的正文", price=12.5)
    response = client.put(f"/books/{book['id']}", json=payload, headers=admin)
    assert response.status_code == 200, response.text
    read = client.get(f"/books/{book['id']}", headers=accounts["reader"]).json()["data"]
    assert read["description"] == payload["description"] and read["price"] == 12.5
    assert read["created_at"].endswith("Z")
    assert (
        client.get("/books", params={"q": prefix}, headers=admin).json()["data"][
            "total"
        ]
        == 3
    )
    assert client.delete(f"/books/{book['id']}", headers=admin).status_code == 200
    assert client.get(f"/books/{book['id']}", headers=admin).status_code == 404


def test_reader_permissions_and_hidden(client, accounts, create_book):
    """使用真实 client、accounts、create_book 验证所有写权限与下架不可见。"""
    book = create_book(published=False)
    path = f"/books/{book['id']}"
    reader = accounts["reader"]
    payload = {
        k: book[k]
        for k in (
            "name",
            "author",
            "category",
            "description",
            "price",
            "cover",
            "published",
        )
    }
    for method, url, body in (
        ("post", "/books", payload),
        ("put", path, payload),
        ("patch", path + "/publication", {"published": True}),
        ("delete", path, None),
    ):
        response = client.request(method, url, json=body, headers=reader)
        assert response.status_code == 403, response.text
    assert (
        client.get("/books", params={"scope": "all"}, headers=reader).status_code == 403
    )
    for headers in accounts.values():
        assert client.get(path, headers=headers).status_code == 404
        assert client.get(path + "/download", headers=headers).status_code == 404
    assert client.put(f"/favorites/{book['id']}", headers=reader).status_code == 404
    page = client.get(
        "/books", params={"scope": "all", "q": book["name"]}, headers=accounts["admin"]
    ).json()["data"]
    assert page["list"][0]["id"] == book["id"]


def test_favorite_isolation_visibility_delete(client, accounts, create_book):
    """用 client、accounts、create_book 验证收藏隔离、隐藏恢复及删除引用。"""
    book = create_book()
    book_id = book["id"]
    reader, admin = accounts["reader"], accounts["admin"]

    def favorites(headers):
        """读取 headers 所属用户的真实收藏 ID 集合。"""
        response = client.get("/favorites", headers=headers)
        assert response.status_code == 200, response.text
        return {b["id"] for b in response.json()["data"]}

    for _ in range(2):
        assert client.put(f"/favorites/{book_id}", headers=reader).status_code == 200
    assert book_id in favorites(reader) and book_id not in favorites(admin)
    assert client.delete(f"/favorites/{book_id}", headers=admin).status_code == 200
    assert book_id in favorites(reader)
    assert (
        client.patch(
            f"/books/{book_id}/publication", json={"published": False}, headers=admin
        ).status_code
        == 200
    )
    assert book_id not in favorites(reader)
    assert (
        client.patch(
            f"/books/{book_id}/publication", json={"published": True}, headers=admin
        ).status_code
        == 200
    )
    assert book_id in favorites(reader)
    assert client.delete(f"/books/{book_id}", headers=admin).status_code == 200
    assert book_id not in favorites(reader)
    for _ in range(2):
        assert client.delete(f"/favorites/{book_id}", headers=reader).status_code == 200


def test_login_revocation_and_expiration(client, registered_user):
    """通过 client、registered_user 验证真实密码、注销、过期和无会话 JWT。"""
    user = registered_user()
    assert client.post("/auth/token").status_code == 400
    assert (
        client.post(
            "/auth/token", data={"username": user["username"], "password": "wrong"}
        ).status_code
        == 401
    )
    response = client.post(
        "/auth/token", data={"username": user["username"], "password": user["password"]}
    )
    body = response.json()["data"]
    headers = {"Authorization": "Bearer " + body["access_token"]}
    assert (
        client.get("/auth/me", headers=headers).json()["data"]["id"]
        == body["user"]["id"]
    )
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401
    for token in (
        "invalid",
        create_access_token(
            {"sub": str(body["user"]["id"]), "jti": uuid4().hex}, timedelta(minutes=-1)
        ),
        create_access_token({"sub": str(body["user"]["id"]), "jti": uuid4().hex}),
    ):
        assert (
            client.get(
                "/books", headers={"Authorization": "Bearer " + token}
            ).status_code
            == 401
        )
    assert client.get("/books").status_code == 401


def test_download_real_content(client, accounts, create_book):
    """用 client、accounts 和 create_book 的自有图书核对各真实附件正文与文件名。"""
    resource = Path(__file__).resolve().parents[1] / "resources" / "books"

    async def attach_file(book_id, path, filename):
        """在当前真实数据库为自有 book_id 关联 path 文件及 filename 下载名。"""
        async with AsyncSessionLocal() as db:
            book = await db.get(BookDB, book_id)
            book.file_name = filename
            book.file_format = "TXT"
            book.file_size = path.stat().st_size
            book.file_path = path.name
            await db.commit()

    for path in sorted(resource.glob("*.txt")):
        content = path.read_bytes()
        title = (
            content.decode("utf-8")
            .splitlines()[0]
            .removeprefix("《")
            .removesuffix("》")
        )
        book = create_book(name=title)
        filename = title + ".txt"
        client.portal.call(attach_file, book["id"], path, filename)
        detail = client.get(f"/books/{book['id']}", headers=accounts["reader"]).json()[
            "data"
        ]
        response = client.get(detail["file"]["url"], headers=accounts["reader"])
        assert response.status_code == 200, response.text
        assert response.content == content
        assert (
            response.content.decode("utf-8").splitlines()[0] == f"《{detail['name']}》"
        )
        assert len(response.content) == detail["file"]["size"]
        assert detail["file"]["name"] == filename
        assert response.headers["content-disposition"] == (
            "attachment; filename*=utf-8''" + quote(filename)
        )
        assert response.headers["cache-control"] == "no-store, private"
        assert client.get(detail["file"]["url"]).status_code == 401
    assert (
        client.get(
            "/resources/books/book-1.txt", headers=accounts["reader"]
        ).status_code
        == 404
    )
    no_file = create_book()
    assert (
        client.get(
            f"/books/{no_file['id']}/download", headers=accounts["reader"]
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "  "},
        {"author": " "},
        {"category": " "},
        {"description": " "},
        {"name": "x" * 101},
        {"author": "x" * 61},
        {"category": "x" * 41},
        {"description": "x" * 3001},
        {"price": -1},
        {"price": "NaN"},
        {"price": "Infinity"},
    ],
)
def test_invalid_book(client, accounts, changes):
    """用 client、accounts 确认 changes 违反资料约束时返回实际 400。"""
    payload = {
        "name": "pytest-invalid",
        "author": "作者",
        "category": "分类",
        "description": "说明",
        "price": 0,
    }
    payload.update(changes)
    response = client.post("/books", json=payload, headers=accounts["admin"])
    assert response.status_code == 400, response.text
    assert response.json()["code"] == 400


@pytest.mark.parametrize(
    "params", [{"page": 0}, {"page_size": 51}, {"sort": "invalid"}]
)
def test_invalid_pagination(client, accounts, params):
    """使用 client、accounts 验证非法 params 分页排序。"""
    assert (
        client.get("/books", params=params, headers=accounts["reader"]).status_code
        == 400
    )


def test_register_identity_and_password_spaces(client, registered_user):
    """用 client、registered_user 验证用户名trim、真实哈希、密码空格和重复约束。"""
    username = "pytest-" + uuid4().hex
    user = registered_user(
        password="  中文 password  ", username="  " + username + "  "
    )
    assert user["username"] == username and user["name"] == username
    assert user["role"] == "reader" and "password_hash" not in user

    async def verify_hash():
        """读取自有 user 的真实密码哈希并校验原始空格；无参数。"""
        async with AsyncSessionLocal() as db:
            row = await db.get(UserDB, user["id"])
            return (
                row.password_hash != user["password"]
                and password_context.verify(user["password"], row.password_hash)
                and not password_context.verify(
                    user["password"].strip(), row.password_hash
                )
            )

    assert client.portal.call(verify_hash)
    for duplicate in (username, username.upper()):
        assert (
            client.post(
                "/auth/register",
                json={"username": duplicate, "password": "password123"},
            ).status_code
            == 409
        )
    for password, status in ((user["password"], 200), (user["password"].strip(), 401)):
        response = client.post(
            "/auth/token", data={"username": username, "password": password}
        )
        assert response.status_code == status, response.text
        if status == 200:
            headers = {
                "Authorization": "Bearer " + response.json()["data"]["access_token"]
            }
            assert (
                client.get(
                    "/books", params={"scope": "all"}, headers=headers
                ).status_code
                == 403
            )


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "password": "password123"},
        {"username": " " * 5, "password": "password123"},
        {"username": "u" * 61, "password": "password123"},
        {"username": "valid-user", "password": "short"},
        {"username": "valid-user", "password": " " * 8},
        {"username": "valid-user", "password": "p" * 129},
        {"username": "valid-user", "password": "password123", "role": "admin"},
    ],
)
def test_register_validation(client, payload):
    """用 client 拒绝 payload 中的无效字段及角色注入。"""
    assert client.post("/auth/register", json=payload).status_code == 400


def test_password_change_revokes_all_sessions(client, registered_user):
    """用 client、registered_user 验证错误旧密码无副作用、改密及全部会话撤销。"""
    user = registered_user(password="p" * 128)
    tokens = []
    for _ in range(3):
        response = client.post(
            "/auth/token",
            data={"username": user["username"], "password": user["password"]},
        )
        assert response.status_code == 200, response.text
        tokens.append(
            {"Authorization": "Bearer " + response.json()["data"]["access_token"]}
        )
    new_password = "  新的 password 456  "
    assert (
        client.put(
            "/auth/password",
            json={"old_password": user["password"], "new_password": new_password},
        ).status_code
        == 401
    )
    for payload in (
        {"old_password": "", "new_password": new_password},
        {"old_password": "p" * 129, "new_password": new_password},
        {"old_password": user["password"], "new_password": user["password"]},
        {"old_password": user["password"], "new_password": " " * 8},
        {"old_password": user["password"], "new_password": "short"},
        {"old_password": user["password"], "new_password": "p" * 129},
        {
            "old_password": user["password"],
            "new_password": new_password,
            "role": "admin",
        },
    ):
        assert (
            client.put("/auth/password", json=payload, headers=tokens[0]).status_code
            == 400
        )
    assert (
        client.put(
            "/auth/password",
            json={"old_password": "wrong", "new_password": new_password},
            headers=tokens[0],
        ).status_code
        == 400
    )
    for headers in tokens:
        assert client.get("/auth/me", headers=headers).status_code == 200
    response = client.post(
        "/auth/token", data={"username": user["username"], "password": user["password"]}
    )
    assert response.status_code == 200
    tokens.append(
        {"Authorization": "Bearer " + response.json()["data"]["access_token"]}
    )
    response = client.put(
        "/auth/password",
        json={"old_password": user["password"], "new_password": new_password},
        headers=tokens[0],
    )
    assert response.status_code == 200 and response.json()["data"] is None
    for headers in tokens:
        assert client.get("/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/auth/token",
            data={"username": user["username"], "password": user["password"]},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/token", data={"username": user["username"], "password": new_password}
        ).status_code
        == 200
    )



def test_portal_authentication_and_real_role(client, registered_user):
    """用 client、registered_user 验证入口权限先于会话签发，角色只取真实数据库。"""
    user = registered_user()
    credentials = {"username": user["username"], "password": user["password"]}

    async def session_count():
        """查询当前自有 user 的真实会话数；无参数。"""
        async with AsyncSessionLocal() as db:
            return await db.scalar(
                select(func.count())
                .select_from(AuthSessionDB)
                .where(AuthSessionDB.user_id == user["id"])
            )

    before = client.portal.call(session_count)
    for password, status in ((user["password"], 403), ("wrong-password", 401)):
        response = client.post(
            "/auth/token",
            data={**credentials, "password": password, "portal": "admin", "role": "admin"},
        )
        assert response.status_code == status, response.text
    assert client.portal.call(session_count) == before
    assert client.post(
        "/auth/token", data={**credentials, "portal": "invalid"}
    ).status_code == 400
    response = client.post(
        "/auth/token", data={**credentials, "portal": "reader", "role": "admin"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["user"]["role"] == "reader"

    async def promote_own_user():
        """仅将本测试创建的 user 提升为管理员以验证两个入口；无参数。"""
        async with AsyncSessionLocal() as db:
            row = await db.get(UserDB, user["id"])
            row.role = "admin"
            await db.commit()

    client.portal.call(promote_own_user)
    for portal in ("reader", "admin"):
        response = client.post("/auth/token", data={**credentials, "portal": portal})
        assert response.status_code == 200, response.text
        assert response.json()["data"]["user"]["role"] == "admin"
        headers = {"Authorization": "Bearer " + response.json()["data"]["access_token"]}
        assert client.get("/books", params={"scope": "all"}, headers=headers).status_code == 200
