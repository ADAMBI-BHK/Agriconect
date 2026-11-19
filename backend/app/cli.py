"""Outils en ligne de commande :  python -m app.cli init-db | seed-demo | create-admin | accounts"""
import sys
from pathlib import Path
from .config import settings, BASE_DIR


def init_db():
    from alembic import command
    from alembic.config import Config
    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "migrations"))
    command.upgrade(cfg, "head")
    from .db import SessionLocal
    from .seed import seed_reference, ensure_admin
    with SessionLocal() as db:
        seed_reference(db); ensure_admin(db)
    print("Base de données prête (migrations appliquées, référentiels et administrateur créés).")


def seed_demo_cmd():
    from .db import SessionLocal
    from .seed import seed_demo, DEMO_ACCOUNTS
    with SessionLocal() as db:
        r = seed_demo(db)
    print("Données de démonstration déjà présentes." if r.get("already") else "Données de démonstration créées.")
    accounts()


def create_admin():
    """Crée ou réinitialise le compte admin à partir de ADMIN_EMAIL / ADMIN_PASSWORD."""
    if not settings.admin_email or not settings.admin_password:
        raise SystemExit("ADMIN_EMAIL et ADMIN_PASSWORD doivent être renseignés dans backend/.env")
    from sqlalchemy import select
    from .db import SessionLocal
    from .models import User, now
    from .security import hash_password
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == settings.admin_email.lower()))
        if u is None:
            u = User(email=settings.admin_email.lower(), full_name="Administrateur AgriConnect", role="admin", status="active", password_hash=hash_password(settings.admin_password), terms_accepted_at=now())
            db.add(u)
            action = "créé"
        else:
            u.role = "admin"
            u.status = "active"
            u.password_hash = hash_password(settings.admin_password)
            u.session_version += 1
            action = "mis à jour"
        db.commit()
    print(f"Compte administrateur {action} : {settings.admin_email.lower()}")


def accounts():
    from .seed import DEMO_ACCOUNTS
    print("\nComptes de test :")
    for role, email, pwd in DEMO_ACCOUNTS:
        print(f"  {role:42} {email:48} {pwd}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"init-db": init_db, "seed-demo": seed_demo_cmd, "create-admin": create_admin, "accounts": accounts}.get(cmd, lambda: print(__doc__))()
