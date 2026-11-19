"""Circuit de validation des offres, rémunération et consentement matching."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    graduate_cols = {c["name"] for c in inspector.get_columns("graduate_profiles")}
    offer_cols = {c["name"] for c in inspector.get_columns("opportunities")}
    # 0001 construit le schéma depuis les modèles courants sur une base neuve ;
    # ces contrôles évitent de doubler les colonnes dans ce cas.
    with op.batch_alter_table("graduate_profiles") as b:
        if "matching_opt_in" not in graduate_cols:
            b.add_column(sa.Column("matching_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "matching_consent_at" not in graduate_cols:
            b.add_column(sa.Column("matching_consent_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("opportunities") as b:
        additions = [
            ("salary_type", sa.String(20), "negotiable"), ("salary_min", sa.Integer(), None),
            ("salary_max", sa.Integer(), None), ("salary_period", sa.String(20), "month"),
            ("salary_currency", sa.String(8), "XOF"), ("benefits", sa.Text(), ""),
            ("review_reason", sa.Text(), ""), ("reviewed_at", sa.DateTime(), None),
        ]
        for name, typ, default in additions:
            if name not in offer_cols:
                if default is None:
                    b.add_column(sa.Column(name, typ, nullable=True))
                else:
                    b.add_column(sa.Column(name, typ, nullable=False, server_default=default))
    # Toutes les anciennes annonces publiées passent en file de contrôle humain.
    op.execute(sa.text("UPDATE opportunities SET status='pending_review' WHERE status='published'"))

    if "offer_matches" not in sa.inspect(bind).get_table_names():
        op.create_table("offer_matches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("opportunity_id", sa.Integer(), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False),
            sa.Column("graduate_id", sa.Integer(), sa.ForeignKey("graduate_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False), sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("total", sa.Integer(), nullable=False), sa.Column("criteria_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("algorithm_version", sa.String(30), nullable=False, server_default="1.0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("opportunity_id", "graduate_id", name="uq_offer_matches_opportunity_graduate"))
    idx = {i["name"] for i in sa.inspect(bind).get_indexes("offer_matches")}
    for name, cols in [("ix_offer_matches_opportunity_id", ["opportunity_id"]), ("ix_offer_matches_graduate_id", ["graduate_id"]), ("ix_offer_matches_offer_rank", ["opportunity_id", "rank"])]:
        if name not in idx:
            op.create_index(name, "offer_matches", cols)
    constraints = {c.get("name") for c in sa.inspect(bind).get_unique_constraints("offer_matches")}
    unique_indexes = {i["name"] for i in sa.inspect(bind).get_indexes("offer_matches") if i.get("unique")}
    if "uq_offer_matches_opportunity_graduate" not in constraints and "uq_offer_matches_opportunity_graduate" not in unique_indexes:
        # Cas de reprise après une migration interrompue : un index unique évite ALTER CONSTRAINT sur SQLite.
        op.create_index("uq_offer_matches_opportunity_graduate", "offer_matches", ["opportunity_id", "graduate_id"], unique=True)


def downgrade():
    op.drop_table("offer_matches")
    with op.batch_alter_table("opportunities") as b:
        for c in ("reviewed_at", "review_reason", "benefits", "salary_currency", "salary_period", "salary_max", "salary_min", "salary_type"):
            b.drop_column(c)
    with op.batch_alter_table("graduate_profiles") as b:
        b.drop_column("matching_consent_at")
        b.drop_column("matching_opt_in")
