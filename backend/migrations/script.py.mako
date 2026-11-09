"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    """执行当前版本的前向结构迁移；无参数。"""
    ${upgrades if upgrades else "pass"}


def downgrade():
    """执行当前版本经审查的数据结构回退；无参数。"""
    ${downgrades if downgrades else "pass"}
