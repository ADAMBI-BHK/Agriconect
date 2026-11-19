from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, Notification, AuditLog, Organization, GraduateProfile
from .security import read_token

COOKIE = "ac_session"


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    tok = read_token(request.cookies.get(COOKIE, ""))
    user = db.get(User, tok[0]) if tok else None
    if not user or user.status != "active" or user.session_version != tok[1]:
        raise HTTPException(401, "Non authentifié")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Accès interdit")
        return user
    return dep


def _org(user: User, db: Session, kind: str, need_validated: bool) -> Organization:
    o = db.scalar(select(Organization).where(Organization.owner_id == user.id, Organization.kind == kind))
    if not o:
        raise HTTPException(404, "Organisation introuvable")
    if need_validated and o.status != "validated":
        who = "Votre entreprise" if kind == "company" else "Votre établissement"
        raise HTTPException(403, f"{who} n'a pas encore été validé(e) par l'administration AgriConnect")
    return o


def company_any(user: User = Depends(require_role("company")), db: Session = Depends(get_db)) -> Organization:
    return _org(user, db, "company", False)


def company_ok(user: User = Depends(require_role("company")), db: Session = Depends(get_db)) -> Organization:
    return _org(user, db, "company", True)


def institution_any(user: User = Depends(require_role("institution")), db: Session = Depends(get_db)) -> Organization:
    return _org(user, db, "institution", False)


def institution_ok(user: User = Depends(require_role("institution")), db: Session = Depends(get_db)) -> Organization:
    return _org(user, db, "institution", True)


def graduate_profile(user: User = Depends(require_role("graduate")), db: Session = Depends(get_db)) -> GraduateProfile:
    p = db.scalar(select(GraduateProfile).where(GraduateProfile.user_id == user.id))
    if not p:
        raise HTTPException(404, "Profil introuvable")
    return p


admin_only = require_role("admin")


def notify(db: Session, user_id: int, message: str):
    db.add(Notification(user_id=user_id, message=message[:500]))


def audit(db: Session, actor_id: int | None, action: str, detail: str = ""):
    db.add(AuditLog(actor_id=actor_id, action=action, detail=detail[:2000]))
