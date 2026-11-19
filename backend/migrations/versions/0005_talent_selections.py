"""Ajoute la sélection de talents par une entreprise.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "talent_selections" in inspector.get_table_names():
        return
    op.create_table(
        "talent_selections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("graduate_id", sa.Integer(), sa.ForeignKey("graduate_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("company_id", "opportunity_id", "graduate_id", name="uq_talent_selection"),
    )
    op.create_index("ix_talent_selections_company_id", "talent_selections", ["company_id"])
    op.create_index("ix_talent_selections_opportunity_id", "talent_selections", ["opportunity_id"])
    op.create_index("ix_talent_selections_graduate_id", "talent_selections", ["graduate_id"])


def downgrade():
    op.drop_index("ix_talent_selections_graduate_id", table_name="talent_selections")
    op.drop_index("ix_talent_selections_opportunity_id", table_name="talent_selections")
    op.drop_index("ix_talent_selections_company_id", table_name="talent_selections")
    op.drop_table("talent_selections")
