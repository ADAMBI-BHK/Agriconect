"""Schéma initial AgriConnect 1.0

Instantané complet du modèle de données (utilisateurs, organisations, référentiels, profils, listes, offres, abonnements, etc.).
Il est créé à partir des métadonnées des modèles : ``checkfirst`` rend l'opération sans danger si des tables existent déjà.
Les évolutions suivantes se font avec :  alembic revision --autogenerate -m "description"

Revision ID: 0001
Revises:
"""
from alembic import op
from app.db import Base
from app import models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
