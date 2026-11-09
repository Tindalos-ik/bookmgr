"""扩展现有图书并一次性初始化账户和原创目录，保留已有图书。"""

import json
from pathlib import Path
from datetime import datetime, UTC
from alembic import op
import sqlalchemy as sa
from passlib.hash import pbkdf2_sha256

revision = "20261109_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """在当前库扩展表并写入本版本独立种子资源；无参数。"""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "books" not in inspector.get_table_names():
        op.create_table(
            "books",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("price", sa.Float, nullable=False),
        )
        op.create_index("ix_books_name", "books", ["name"])
    columns = {c["name"] for c in sa.inspect(connection).get_columns("books")}
    additions = [
        sa.Column("author", sa.String(60)),
        sa.Column("category", sa.String(40)),
        sa.Column("description", sa.String(3000)),
        sa.Column("cover", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("published_at", sa.DateTime),
        sa.Column("published", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("file_name", sa.String(255)),
        sa.Column("file_format", sa.String(10)),
        sa.Column("file_size", sa.Integer),
        sa.Column("file_path", sa.String(255)),
    ]
    for column in additions:
        if column.name not in columns:
            op.add_column("books", column)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(60), unique=True, nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("jti", sa.String(32), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "favorites",
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "book_id",
            sa.Integer,
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    metadata = sa.MetaData()
    users = sa.Table("users", metadata, autoload_with=connection)
    books = sa.Table("books", metadata, autoload_with=connection)
    connection.execute(
        users.insert(),
        [
            {
                "username": "reader",
                "name": "读者",
                "role": "reader",
                "password_hash": pbkdf2_sha256.hash("reader123"),
            },
            {
                "username": "admin",
                "name": "管理员",
                "role": "admin",
                "password_hash": pbkdf2_sha256.hash("admin123"),
            },
        ],
    )
    root = Path(__file__).resolve().parents[2]
    rows = json.loads(
        (root / "migrations" / "seed_books.json").read_text(encoding="utf-8")
    )
    for row in rows:
        book = {
            key: row[key]
            for key in (
                "name",
                "author",
                "category",
                "description",
                "cover",
                "price",
                "published",
            )
        }
        book["created_at"] = (
            datetime.fromisoformat(row["createdAt"].replace("Z", "+00:00"))
            .astimezone(UTC)
            .replace(tzinfo=None)
        )
        book["published_at"] = (
            datetime.fromisoformat(row["publishedAt"].replace("Z", "+00:00"))
            .astimezone(UTC)
            .replace(tzinfo=None)
            if row.get("publishedAt")
            else None
        )
        if "file" in row:
            filename = row["file"]["url"].rsplit("/", 1)[1]
            book.update(
                file_name=row["file"]["name"],
                file_format="TXT",
                file_size=(root / "resources" / "books" / filename).stat().st_size,
                file_path=filename,
            )
        connection.execute(books.insert().values(**book))


def downgrade():
    """阻止自动删除业务数据；无参数。"""
    raise RuntimeError("本迁移包含业务数据，请通过经过审查的前向迁移调整")
