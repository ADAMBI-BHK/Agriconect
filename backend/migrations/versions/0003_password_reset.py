"""Ajoute les jetons de récupération de mot de passe.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch:
        if "reset_hash" not in columns:
            batch.add_column(sa.Column("reset_hash", sa.String(length=64), nullable=True))
        if "reset_expires" not in columns:
            batch.add_column(sa.Column("reset_expires", sa.DateTime(), nullable=True))
    inspector = sa.inspect(op.get_bind())
    indexes = {i["name"] for i in inspector.get_indexes("users")}
    if "ix_users_reset_hash" not in indexes:
        op.create_index("ix_users_reset_hash", "users", ["reset_hash"], unique=False)


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("users")}
    indexes = {i["name"] for i in inspector.get_indexes("users")}
    with op.batch_alter_table("users") as batch:
        if "ix_users_reset_hash" in indexes:
            batch.drop_index("ix_users_reset_hash")
        if "reset_expires" in columns:
            batch.drop_column("reset_expires")
        if "reset_hash" in columns:
            batch.drop_column("reset_hash")
