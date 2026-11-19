import time
from datetime import timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, Organization, GraduateProfile, now
from .schemas import RegisterOrgIn, LoginIn, ActivateIn, PasswordChangeIn, PasswordResetRequestIn, PasswordResetIn
from .security import hash_password, verify_password, make_token, hash_token, new_reset_token
from .config import settings
from .deps import COOKIE, current_user, audit, notify
from .services import get_setting
from .mailer import send_mail, reset_body

router = APIRouter(prefix="/api", tags=["auth"])
_attempts: dict[str, list[float]] = defaultdict(list)  # limiteur en mémoire (un seul processus) — voir README
MAX_ATTEMPTS, WINDOW = 5, 600


def _throttle(key: str, record: bool = False):
    t = time.time()
    _attempts[key] = [x for x in _attempts[key] if t - x < WINDOW]
    if record:
        _attempts[key].append(t)
    elif len(_attempts[key]) >= MAX_ATTEMPTS:
        raise HTTPException(429, "Trop de tentatives, réessayez plus tard")


def user_out(u: User, db: Session) -> dict:
    d = {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role}
    if u.role in ("company", "institution"):
        o = db.scalar(select(Organization).where(Organization.owner_id == u.id))
        d["org"] = {"id": o.id, "name": o.name, "status": o.status, "status_reason": o.status_reason} if o else None
    return d


def _set_cookie(resp: Response, u: User, request: Request | None = None):
    # Le Preview public est un iframe HTTPS : SameSite=None + Secure est nécessaire pour que
    # le cookie accompagne les appels cross-site. En HTTP local, on conserve le comportement Lax.
    origin = (request.headers.get("origin", "") if request else "")
    forwarded = (request.headers.get("x-forwarded-proto", "") if request else "")
    public_https = settings.cookie_secure or settings.app_url.startswith("https://") or origin.startswith("https://") or forwarded.split(",")[0].strip() == "https"
    resp.set_cookie(COOKIE, make_token(u.id, u.session_version), httponly=True, secure=public_https,
                    samesite="none" if public_https else "lax", max_age=settings.session_hours * 3600, path="/")


@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    return {"payment_mode": settings.payment_mode, "demo_data": get_setting(db, "demo_data") == "true",
            "terms_version": get_setting(db, "terms_version", "1.0"), "contact_email": get_setting(db, "contact_email"),
            "support_phone": get_setting(db, "support_phone")}


@router.post("/auth/register-organization", status_code=201)
def register_org(data: RegisterOrgIn, request: Request, resp: Response, db: Session = Depends(get_db)):
    """Entreprises et établissements uniquement. Leur compte reste « en attente » jusqu'à validation par l'administration."""
    if not data.accept_terms:
        raise HTTPException(422, "Les conditions d'utilisation doivent être acceptées")
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, "Cet email est déjà utilisé")
    u = User(email=data.email, password_hash=hash_password(data.password), full_name=data.full_name.strip(), role=data.role,
             status="active", terms_accepted_at=now())
    db.add(u); db.flush()
    db.add(Organization(owner_id=u.id, kind=data.role, name=data.org_name.strip(), status="pending"))
    audit(db, u.id, "register_org", data.role)
    for a in db.scalars(select(User).where(User.role == "admin", User.status == "active")).all():
        notify(db, a.id, f"Nouvelle demande d'inscription ({'entreprise' if data.role == 'company' else 'établissement'}) : {data.org_name.strip()}")
    db.commit()
    _set_cookie(resp, u, request)
    return user_out(u, db)


@router.post("/auth/login")
def login(data: LoginIn, request: Request, resp: Response, db: Session = Depends(get_db)):
    key = f"{data.email}|{request.client.host if request.client else ''}"
    _throttle(key)
    u = db.scalar(select(User).where(User.email == data.email))
    if not u or not verify_password(data.password, u.password_hash):
        _throttle(key, record=True)
        audit(db, None, "login_failed", data.email); db.commit()
        raise HTTPException(401, "Identifiants invalides. Si vous êtes diplômé, utilisez le lien d'invitation reçu pour activer votre compte.")
    if u.status == "suspended":
        raise HTTPException(403, "Ce compte est suspendu. Contactez l'administration AgriConnect.")
    if u.status != "active":
        raise HTTPException(403, "Ce compte n'est pas encore activé : utilisez le lien d'invitation.")
    _attempts.pop(key, None)
    u.last_login = now(); db.commit()
    _set_cookie(resp, u, request)
    return user_out(u, db)


RESET_MESSAGE = "Si un compte actif correspond à cette adresse, un lien de récupération vient d'être envoyé. Vérifiez votre boîte de réception et vos courriers indésirables."


@router.post("/auth/request-password-reset")
def request_password_reset(data: PasswordResetRequestIn, db: Session = Depends(get_db)):
    """Répond toujours de la même manière pour ne pas divulguer les comptes existants."""
    u = db.scalar(select(User).where(User.email == data.email))
    if u and u.status == "active":
        raw, digest = new_reset_token()
        u.reset_hash = digest
        u.reset_expires = now() + timedelta(hours=settings.reset_password_hours)
        link = f"{settings.app_url}/reinitialiser-mot-de-passe?token={raw}"
        sent, result = send_mail(u.email, "Réinitialiser votre mot de passe — AgriConnect",
                                 reset_body(u.full_name, link, settings.reset_password_hours))
        audit(db, u.id, "password_reset_requested", "email " + ("envoyé" if sent else result))
    db.commit()
    return {"ok": True, "message": RESET_MESSAGE}


@router.post("/auth/reset-password")
def reset_password(data: PasswordResetIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.reset_hash == hash_token(data.token)))
    if not u or u.status != "active" or not u.reset_expires or u.reset_expires < now():
        raise HTTPException(400, "Ce lien de récupération est invalide ou expiré. Demandez un nouveau lien.")
    u.password_hash = hash_password(data.new_password)
    u.reset_hash = None
    u.reset_expires = None
    u.session_version += 1
    audit(db, u.id, "password_reset_completed")
    db.commit()
    return {"ok": True, "message": "Votre mot de passe a été réinitialisé. Vous pouvez vous connecter."}


@router.post("/auth/logout")
def logout(resp: Response):
    resp.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_out(u, db)


@router.get("/auth/activation-info")
def activation_info(token: str, request: Request, db: Session = Depends(get_db)):
    _throttle("act|" + (request.client.host if request.client else ""))
    u = db.scalar(select(User).where(User.activation_hash == hash_token(token))) if token else None
    if not u or u.status != "pending_activation" or not u.activation_expires or u.activation_expires < now():
        _throttle("act|" + (request.client.host if request.client else ""), record=True)
        raise HTTPException(404, "Lien d'invitation invalide ou expiré. Demandez un nouveau lien à l'administration AgriConnect.")
    return {"full_name": u.full_name, "email": u.email}


@router.post("/auth/activate")
def activate(data: ActivateIn, request: Request, resp: Response, db: Session = Depends(get_db)):
    ip = "act|" + (request.client.host if request.client else "")
    _throttle(ip)
    if not data.accept_terms:
        raise HTTPException(422, "Vous devez accepter les conditions d'utilisation et le traitement de vos données")
    u = db.scalar(select(User).where(User.activation_hash == hash_token(data.token)))
    if not u or u.status != "pending_activation" or not u.activation_expires or u.activation_expires < now():
        _throttle(ip, record=True)
        raise HTTPException(404, "Lien d'invitation invalide ou expiré. Demandez un nouveau lien à l'administration AgriConnect.")
    u.password_hash = hash_password(data.password)
    u.status = "active"
    u.terms_accepted_at = now()
    u.activation_hash = None
    u.activation_expires = None
    u.session_version += 1
    p = db.scalar(select(GraduateProfile).where(GraduateProfile.user_id == u.id))
    if p:
        p.visible = True  # consentement explicite donné à l'activation (cahier des charges §16)
    audit(db, u.id, "account_activated", u.email)
    db.commit()
    _set_cookie(resp, u, request)
    return user_out(u, db)


@router.post("/auth/change-password")
def change_password(data: PasswordChangeIn, request: Request, resp: Response, u: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, u.password_hash):
        raise HTTPException(403, "Mot de passe actuel incorrect")
    u.password_hash = hash_password(data.new_password)
    u.session_version += 1  # invalide les autres sessions
    audit(db, u.id, "password_changed"); db.commit()
    _set_cookie(resp, u, request)
    return {"ok": True}
