"""连接当前真实 MySQL 验证消费者权限和业务，仅删除自身 pytest 图书。"""

from pathlib import Path
from datetime import timedelta
from uuid import uuid4
from urllib.parse import quote
import pytest
from fastapi.testclient import TestClient
from dependencies import create_access_token
from database import AsyncSessionLocal, BookDB
from main import app


@pytest.fixture(scope="session")
def client():
    """提供使用真实数据库和原始依赖的 HTTP 客户端；无参数。"""
    with TestClient(app) as instance:
        yield instance


@pytest.fixture(scope="session")
def accounts(client):
    """通过 client 为两个持久演示账户登录，结束时注销自己的会话。"""
    result = {}
    for name in ("admin", "reader"):
        response = client.post(
            "/auth/token", data={"username": name, "password": name + "123"}
        )
        assert response.status_code == 200, response.text
        result[name] = {
            "Authorization": "Bearer " + response.json()["data"]["access_token"]
        }
    yield result
    for headers in result.values():
        response = client.post("/auth/logout", headers=headers)
        assert response.status_code == 200, response.text


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


def test_login_revocation_and_expiration(client):
    """通过 client 验证真实密码、注销旧 token、过期和无会话 JWT。"""
    assert client.post("/auth/token").status_code == 400
    assert (
        client.post(
            "/auth/token", data={"username": "reader", "password": "wrong"}
        ).status_code
        == 401
    )
    response = client.post(
        "/auth/token", data={"username": "reader", "password": "reader123"}
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
