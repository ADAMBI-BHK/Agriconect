"""Ajoute la photo de profil des diplômés.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("graduate_profiles")}
    if "photo_path" not in columns:
        op.add_column("graduate_profiles", sa.Column("photo_path", sa.String(length=255), nullable=False, server_default=""))
    if "photo_name" not in columns:
        op.add_column("graduate_profiles", sa.Column("photo_name", sa.String(length=255), nullable=False, server_default=""))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("graduate_profiles")}
    if "photo_name" in columns:
        op.drop_column("graduate_profiles", "photo_name")
    if "photo_path" in columns:
        op.drop_column("graduate_profiles", "photo_path")
