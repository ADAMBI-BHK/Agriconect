"""Nettoie les libellés de données fictives visibles dans l'application.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _replace(table: str, column: str, old: str, new: str):
    op.execute(sa.text(f"UPDATE {table} SET {column} = replace({column}, :old, :new) WHERE {column} LIKE :pattern")
              .bindparams(old=old, new=new, pattern=f"%{old}%"))


def upgrade():
    _replace("users", "email", "@demo.agriconnect.test", "@agriconnect.test")
    _replace("users", "full_name", " (démo)", "")
    _replace("users", "full_name", " (demo)", "")
    _replace("organizations", "name", "[DÉMO] ", "")
    _replace("organizations", "name", "[DEMO] ", "")
    _replace("organizations", "description", "Établissement fictif pour la démonstration.", "Établissement partenaire fictif.")
    _replace("opportunities", "description", "Offre fictive de démonstration. ", "Offre de recrutement. ")
    _replace("achievements", "title", " (démo)", "")
    _replace("collaborations", "title", " (démo)", "")
    _replace("evaluations", "comment", "Évaluation fictive de démonstration.", "Évaluation factuelle.")
    _replace("submitted_lists", "title", "[DÉMO] ", "")
    _replace("invoices", "description", "[DÉMO] ", "")
    _replace("payments", "reference", "DEMO-", "AGRI-")


def downgrade():
    _replace("users", "email", "@agriconnect.test", "@demo.agriconnect.test")
    _replace("users", "full_name", "Responsable partenariats", "Responsable partenariats (démo)")
    _replace("users", "full_name", "Établissement en attente", "Établissement en attente (démo)")
    _replace("users", "full_name", "RH AgroVert", "RH AgroVert (démo)")
    _replace("users", "full_name", "RH Ferme du Mono", "RH Ferme du Mono (démo)")
    _replace("organizations", "name", "Institut Agricole Exemple", "[DÉMO] Institut Agricole Exemple")
    _replace("organizations", "name", "Ferme du Mono", "[DÉMO] Ferme du Mono")
