"""使用当前 .env 中的 MySQL；仅清理本文件自行创建的图书。"""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from config import settings
from dependencies import create_access_token
from main import app


@pytest.fixture(scope="session")
def client():
    # 运行真实 lifespan：连接现有 MySQL、建表（若不存在）、关闭连接池。
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth_headers(client):
    response = client.post("/auth/token")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 200, body
    return {"Authorization": f"Bearer {body['data']['access_token']}"}


@pytest.fixture
def create_book(client, auth_headers):
    """记录本用例创建的 ID，即使断言失败，也尝试逐条清理。"""
    created_ids = []

    def create(price=39.9):
        name = f"pytest-{uuid4().hex}"
        response = client.post(
            "/books", json={"name": name, "price": price}, headers=auth_headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["code"] == 200, body
        book = body["data"]
        created_ids.append(book["id"])
        assert book["name"] == name
        assert book["price"] == pytest.approx(price)
        return book

    try:
        yield create
    finally:
        # 不依赖列表、不批量删除；失败时继续清理其余本用例记录。
        failures = []
        for book_id in created_ids:
            try:
                response = client.delete(f"/books/{book_id}", headers=auth_headers)
                body = response.json()
                if response.status_code != 200 or body.get("code") not in (200, 404):
                    failures.append(f"id={book_id}: {response.status_code} {body}")
            except Exception as exc:
                failures.append(f"id={book_id}: {exc}")
        assert not failures, "测试图书清理失败：" + "; ".join(failures)


def test_book_lifecycle(client, auth_headers, create_book):
    """真实新增、持久化读取、删除，再验证图书已不存在。"""
    book = create_book()
    path = f"/books/{book['id']}"

    response = client.get(path, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 200, body
    assert body["data"]["id"] == book["id"]
    assert body["data"]["name"] == book["name"]
    assert body["data"]["price"] == pytest.approx(book["price"])

    response = client.delete(path, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 200

    response = client.get(path, headers=auth_headers)
    # 当前项目的业务异常使用 HTTP 200 + 响应体业务码。
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 404
    assert response.json()["data"] is None


def test_delete_missing_book(client, auth_headers, create_book):
    # 使用自己刚删除的 ID，不猜测某个 ID 一定不存在。
    book = create_book()
    path = f"/books/{book['id']}"
    response = client.delete(path, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 200

    response = client.delete(path, headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 404


def test_pagination(client, auth_headers, create_book):
    """允许数据库已有数据；执行期间不要让其他程序增删图书。"""
    response = client.get("/books", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()["code"] == 200
    initial_total = response.json()["data"]["total"]
    for _ in range(3):
        create_book()
    expected_total = initial_total + 3

    pages = []
    for page in (1, 2):
        response = client.get(
            "/books", params={"page": page, "page_size": 2}, headers=auth_headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["code"] == 200, body
        data = body["data"]
        assert data["total"] == expected_total
        assert data["page"] == page
        assert data["page_size"] == 2
        assert len(data["list"]) == min(2, expected_total - (page - 1) * 2)
        pages.append({book["id"] for book in data["list"]})
    assert pages[0].isdisjoint(pages[1])

    response = client.get(
        "/books",
        params={"page": expected_total // 2 + 2, "page_size": 2},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 200, body
    assert body["data"]["total"] == expected_total
    assert body["data"]["list"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "price": 10},
        {"name": "x" * 101, "price": 10},
        {"name": "invalid", "price": 0},
        {"name": "invalid", "price": -1},
        {"name": "invalid", "price": "not-a-number"},
        {"name": "invalid"},
        {"price": 10},
    ],
    ids=["empty-name", "long-name", "zero-price", "negative-price", "bad-price", "missing-price", "missing-name"],
)
def test_invalid_book(client, auth_headers, payload):
    response = client.post("/books", json=payload, headers=auth_headers)
    assert response.status_code == 400, response.text
    assert response.json()["code"] == 400


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 51}, {"page": "abc"}],
    ids=["zero-page", "negative-page", "zero-size", "oversized-page", "bad-page"],
)
def test_invalid_pagination(client, auth_headers, params):
    response = client.get("/books", params=params, headers=auth_headers)
    assert response.status_code == 400, response.text
    assert response.json()["code"] == 400


def test_invalid_book_id(client, auth_headers):
    response = client.get("/books/not-an-int", headers=auth_headers)
    assert response.status_code == 400, response.text
    assert response.json()["code"] == 400


def test_missing_token(client):
    response = client.get("/books")
    assert response.status_code == 401, response.text
    assert response.json()["code"] == 401


@pytest.mark.parametrize("kind", ["malformed", "expired", "missing-sub", "wrong-signature"])
def test_invalid_token(client, kind):
    if kind == "malformed":
        token = "not-a-jwt"
    elif kind == "expired":
        token = create_access_token({"sub": "pytest-user"}, timedelta(minutes=-5))
    elif kind == "missing-sub":
        token = create_access_token({})
    else:
        token = jwt.encode(
            {"sub": "pytest-user"},
            settings.SECRET_KEY + "-wrong-key",
            algorithm=settings.ALGORITHM,
        )
    response = client.get("/books", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401, response.text
    assert response.json()["code"] == 401
