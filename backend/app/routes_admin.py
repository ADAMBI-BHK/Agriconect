import json
from datetime import date, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from .db import get_db
from .models import (User, Organization, DegreeLevel, Specialty, Degree, Experience, Skill, GraduateProfile, SubmittedList, SubmittedRow,
                     Opportunity, Application, Report, Evaluation, Recommendation, Collaboration, Plan, Subscription, Invoice, Payment,
                     AuditLog, ContactMessage, OfferMatch, now)
from .schemas import (OrgStatusIn, RowIn, RejectIn, NoteIn, AdminCreateGraduateIn, LevelIn, SpecialtyIn, PlanIn, ResolveIn, WeightsIn, SettingsIn)
from .deps import admin_only, notify, audit
from .services import (create_graduate_account, issue_invitation, level_id_by_code, list_counts, recompute_list_status, get_setting, set_setting,
                       match_weights, activate_subscription, plan_out, candidate_data, offer_criteria)
from .routes_institution import list_out, row_out, row_problems
from .routes_company import opp_out, _check_publish
from .routes_billing import settle, sub_out, invoice_out, payment_out
from .mailer import send_mail, invitation_body, smtp_enabled
from .config import settings
from .logic.matching import DEFAULT_WEIGHTS, match
from .payments import new_reference

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_only)])


def _admin(u: User = Depends(admin_only)) -> User:
    return u


# ------------------------------------------------------------------ tableau de bord
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    c = lambda m, *w: db.scalar(select(func.count()).select_from(m).where(*w)) or 0
    revenue = db.scalar(select(func.coalesce(func.sum(Payment.amount_xof), 0)).where(Payment.status == "succeeded", Payment.mode == "live")) or 0
    demo_rev = db.scalar(select(func.coalesce(func.sum(Payment.amount_xof), 0)).where(Payment.status == "succeeded", Payment.mode == "demo")) or 0
    today = date.today()
    return {
        "users": {r: c(User, User.role == r) for r in ("graduate", "company", "institution", "admin")},
        "graduates_by_status": dict(db.execute(select(User.status, func.count()).where(User.role == "graduate").group_by(User.status)).all()),
        "orgs_by_status": {k: dict(db.execute(select(Organization.status, func.count()).where(Organization.kind == k).group_by(Organization.status)).all())
                           for k in ("company", "institution")},
        "lists_by_status": dict(db.execute(select(SubmittedList.status, func.count()).group_by(SubmittedList.status)).all()),
        "offers_published": c(Opportunity, Opportunity.status == "published"), "applications": c(Application),
        "active_subscriptions": c(Subscription, Subscription.status == "active", Subscription.end_date >= today),
        "subscriptions_by_plan": dict(db.execute(select(Plan.name, func.count()).select_from(Subscription).join(Plan, Subscription.plan_id == Plan.id)
                                                 .where(Subscription.status == "active", Subscription.end_date >= today).group_by(Plan.name)).all()),
        "revenue_xof_live": revenue, "revenue_xof_demo": demo_rev, "payment_mode": settings.payment_mode,
        "todo": {"orgs_pending": c(Organization, Organization.status == "pending"),
                 "lists_to_review": c(SubmittedList, SubmittedList.status.in_(["received", "in_review"])),
                 "collaborations_pending": c(Collaboration, Collaboration.status == "pending"),
                 "reports_open": c(Report, Report.status == "open"),
                 "degrees_to_verify": c(Degree, Degree.status.in_(["declared", "in_review"])),
                 "payments_pending": c(Payment, Payment.status == "pending")},
        "smtp_enabled": smtp_enabled(),
    }


# ------------------------------------------------------------------ organisations
def _org_row(o: Organization) -> dict:
    return {"id": o.id, "kind": o.kind, "name": o.name, "sector": o.sector, "city": o.city, "website": o.website, "phone": o.phone,
            "registration_no": o.registration_no, "description": o.description, "status": o.status, "status_reason": o.status_reason,
            "annual_quota": o.annual_quota, "owner": {"id": o.owner.id, "full_name": o.owner.full_name, "email": o.owner.email, "status": o.owner.status},
            "created_at": o.created_at.isoformat()}


@router.get("/orgs")
def orgs(kind: str = "", status: str = "", db: Session = Depends(get_db)):
    q = select(Organization).order_by(Organization.id.desc())
    if kind:
        q = q.where(Organization.kind == kind)
    if status:
        q = q.where(Organization.status == status)
    return [_org_row(o) for o in db.scalars(q).all()]


@router.post("/orgs/{oid}/status")
def org_status(oid: int, data: OrgStatusIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    o = db.get(Organization, oid)
    if not o:
        raise HTTPException(404, "Organisation introuvable")
    if data.status == "rejected" and not data.reason.strip():
        raise HTTPException(422, "Un motif est obligatoire pour rejeter un dossier")
    o.status, o.status_reason = data.status, data.reason.strip()
    if data.annual_quota is not None and o.kind == "institution":
        o.annual_quota = data.annual_quota
    msg = {"validated": "Votre organisation a été validée : vous avez accès à toutes les fonctions de votre espace.",
           "rejected": f"Votre dossier a été rejeté : {o.status_reason}. Corrigez-le puis soumettez-le à nouveau.",
           "suspended": f"Votre organisation a été suspendue. {o.status_reason}", "pending": "Votre dossier est de nouveau en cours d'examen."}[data.status]
    notify(db, o.owner_id, msg)
    audit(db, a.id, "org_status", f"{oid}={data.status} {o.status_reason}"); db.commit()
    return _org_row(o)


# ------------------------------------------------------------------ utilisateurs
class UserStatusIn(BaseModel):
    status: Literal["active", "suspended"]


def _user_row(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "status": u.status, "created_at": u.created_at.isoformat(),
            "last_login": u.last_login.isoformat() if u.last_login else None}


@router.get("/users")
def users(role: str = "", status: str = "", q: str = "", page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    cond = []
    if role:
        cond.append(User.role == role)
    if status:
        cond.append(User.status == status)
    if q:
        cond.append(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(User).where(*cond))
    rows = db.scalars(select(User).where(*cond).order_by(User.id.desc()).offset((page - 1) * size).limit(size)).all()
    return {"total": total, "items": [_user_row(u) for u in rows]}


@router.post("/users/{uid}/status")
def user_status(uid: int, data: UserStatusIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    if u.id == a.id or u.role == "admin":
        raise HTTPException(409, "Un compte administrateur ne peut pas être suspendu ici")
    if data.status == "active" and u.activation_hash:  # jamais activé : reste en attente d'activation
        u.status = "pending_activation"
    else:
        u.status = data.status
    u.session_version += 1
    audit(db, a.id, "user_status", f"{uid}={u.status}"); db.commit()
    return _user_row(u)


@router.post("/users/{uid}/invitation")
def reissue_invitation(uid: int, a: User = Depends(_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u or u.role != "graduate" or u.status != "pending_activation":
        raise HTTPException(404, "Seul un compte candidat en attente d'activation peut recevoir une nouvelle invitation")
    link = issue_invitation(u)
    ok, info = send_mail(u.email, "Votre invitation AgriConnect", invitation_body(u.full_name, link, settings.activation_days))
    audit(db, a.id, "invitation_reissued", u.email); db.commit()
    return {"email": u.email, "full_name": u.full_name, "link": link, "mail_sent": ok, "mail_info": info}


@router.post("/graduates", status_code=201)
def create_graduate(data: AdminCreateGraduateIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    """Création manuelle exceptionnelle (hors liste) d'un compte candidat — tracée dans le journal d'audit."""
    lv = db.get(DegreeLevel, data.level_id)
    if not lv:
        raise HTTPException(422, "Niveau inconnu")
    inst = db.get(Organization, data.institution_id) if data.institution_id else None
    u, link = create_graduate_account(db, full_name=data.full_name.strip(), email=data.email, phone="", institution_id=inst.id if inst else None,
                                      degree_title=data.degree_title.strip(), level_id=lv.id, specialty_text=data.specialty_text, year=data.year,
                                      honors="", country="Bénin", institution_name=inst.name if inst else "",
                                      origin="institution" if inst else "admin")
    ok, info = send_mail(u.email, "Votre invitation AgriConnect", invitation_body(u.full_name, link, settings.activation_days))
    audit(db, a.id, "graduate_created_manually", u.email); db.commit()
    return {"user": _user_row(u), "link": link, "mail_sent": ok, "mail_info": info}


# ------------------------------------------------------------------ listes transmises
def _list(db: Session, lid: int) -> SubmittedList:
    l = db.get(SubmittedList, lid)
    if not l:
        raise HTTPException(404, "Liste introuvable")
    return l


def _row(db: Session, lid: int, rid: int) -> SubmittedRow:
    r = db.get(SubmittedRow, rid)
    if not r or r.list_id != lid:
        raise HTTPException(404, "Ligne introuvable")
    return r


@router.get("/lists")
def lists(status: str = "", db: Session = Depends(get_db)):
    q = select(SubmittedList).order_by(SubmittedList.id.desc())
    if status:
        q = q.where(SubmittedList.status == status)
    return [list_out(l) for l in db.scalars(q).all()]


@router.get("/lists/{lid}")
def get_list(lid: int, db: Session = Depends(get_db)):
    l = _list(db, lid)
    d = list_out(l, rows=True)
    d["institution"]["annual_quota"] = l.institution.annual_quota
    d["institution"]["status"] = l.institution.status
    return d


def _after(db: Session, l: SubmittedList, a: User, action: str, detail: str):
    db.flush(); db.refresh(l)
    before = l.status
    recompute_list_status(l)
    audit(db, a.id, action, detail)
    if l.status != before and l.status in ("validated", "partially_validated", "rejected"):
        notify(db, l.institution.owner_id, f"Votre liste « {l.title} » a été traitée : {l.status}.")


@router.put("/lists/{lid}/rows/{rid}")
def fix_row(lid: int, rid: int, data: RowIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    l, r = _list(db, lid), _row(db, lid, rid)
    if r.status == "account_created":
        raise HTTPException(409, "Un compte existe déjà pour cette ligne")
    for k, v in data.model_dump().items():
        setattr(r, k, v)
    errs = row_problems(db, data.email, data.level_code, data.year, exclude_row=r.id)
    r.status, r.message = ("invalid", "; ".join(errs)) if errs else ("pending", "")
    audit(db, a.id, "row_edited_by_admin", f"{lid}/{rid}"); db.commit()
    return row_out(r)


@router.post("/lists/{lid}/rows/{rid}/validate")
def validate_row(lid: int, rid: int, a: User = Depends(_admin), db: Session = Depends(get_db)):
    l, r = _list(db, lid), _row(db, lid, rid)
    if l.institution.status != "validated":
        raise HTTPException(409, "L'établissement n'est pas validé")
    if r.status not in ("pending", "invalid", "rejected"):
        raise HTTPException(409, f"Ligne déjà au statut « {r.status} »")
    errs = row_problems(db, r.email, r.level_code, r.year, exclude_row=r.id)
    if errs or not r.full_name or not r.degree_title:
        r.status, r.message = "invalid", "; ".join(errs) or "Données incomplètes"
        db.commit()
        raise HTTPException(409, "Ligne non validable : " + r.message)
    r.status, r.message = "validated", ""
    _after(db, l, a, "row_validated", f"{lid}/{rid}"); db.commit()
    return row_out(r)


@router.post("/lists/{lid}/rows/{rid}/reject")
def reject_row(lid: int, rid: int, data: RejectIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    l, r = _list(db, lid), _row(db, lid, rid)
    if r.status == "account_created":
        raise HTTPException(409, "Un compte existe déjà : suspendez-le depuis « Utilisateurs »")
    r.status, r.message = "rejected", data.reason
    _after(db, l, a, "row_rejected", f"{lid}/{rid}: {data.reason}")
    notify(db, l.institution.owner_id, f"Ligne {r.line_no} de « {l.title} » rejetée : {data.reason}. Vous pouvez la corriger.")
    db.commit()
    return row_out(r)


@router.post("/lists/{lid}/validate-all")
def validate_all(lid: int, a: User = Depends(_admin), db: Session = Depends(get_db)):
    """Valide toutes les lignes « en attente » sans erreur ; les lignes à corriger restent en l'état."""
    l = _list(db, lid)
    if l.institution.status != "validated":
        raise HTTPException(409, "L'établissement n'est pas validé")
    n = 0
    for r in l.rows:
        if r.status == "pending" and not row_problems(db, r.email, r.level_code, r.year, exclude_row=r.id):
            r.status = "validated"; n += 1
    _after(db, l, a, "list_validate_all", f"{lid}: {n} lignes")
    db.commit()
    return {"validated": n, **list_out(l)}


@router.post("/lists/{lid}/reject")
def reject_list(lid: int, data: RejectIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    l = _list(db, lid)
    for r in l.rows:
        if r.status in ("pending", "invalid"):
            r.status, r.message = "rejected", data.reason
    l.note = data.reason
    _after(db, l, a, "list_rejected", f"{lid}: {data.reason}")
    db.commit()
    return list_out(l)


@router.post("/lists/{lid}/note")
def list_note(lid: int, data: NoteIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    l = _list(db, lid); l.note = data.note; db.commit()
    return list_out(l)


@router.post("/lists/{lid}/create-accounts")
def create_accounts(lid: int, force: bool = False, a: User = Depends(_admin), db: Session = Depends(get_db)):
    """Crée MANUELLEMENT (déclenché par l'administrateur) les comptes des lignes validées. Les liens d'invitation ne sont affichés
    qu'à cet instant : le jeton en clair n'est jamais stocké (seule son empreinte l'est)."""
    l = _list(db, lid)
    inst = l.institution
    if inst.status != "validated":
        raise HTTPException(409, "L'établissement n'est pas validé")
    todo = [r for r in l.rows if r.status == "validated"]
    if not todo:
        raise HTTPException(409, "Aucune ligne validée à traiter")
    if inst.annual_quota is not None and not force:
        year = now().year
        used = db.scalar(select(func.count()).select_from(GraduateProfile).join(User, GraduateProfile.user_id == User.id)
                         .where(GraduateProfile.institution_id == inst.id, func.extract("year", User.created_at) == year)) or 0
        if used + len(todo) > inst.annual_quota:
            raise HTTPException(409, f"Quota annuel dépassé ({used} compte(s) déjà créé(s) + {len(todo)} pour un quota de {inst.annual_quota}). "
                                     "Relevez le quota de l'établissement ou relancez avec force=true.")
    out = []
    for r in todo:
        lid_ = level_id_by_code(db, r.level_code)
        try:
            u, link = create_graduate_account(db, full_name=r.full_name, email=r.email, phone=r.phone, institution_id=inst.id,
                                              degree_title=r.degree_title, level_id=lid_, specialty_text=r.specialty, year=r.year,
                                              honors=r.honors, country=r.country, institution_name=inst.name)
        except HTTPException as e:  # email devenu indisponible entre-temps
            r.status, r.message = "invalid", str(e.detail)
            out.append({"email": r.email, "full_name": r.full_name, "link": None, "mail_sent": False, "mail_info": r.message})
            continue
        r.user_id, r.status = u.id, "account_created"
        ok, info = send_mail(u.email, "Votre invitation AgriConnect", invitation_body(u.full_name, link, settings.activation_days))
        out.append({"email": u.email, "full_name": u.full_name, "link": link, "mail_sent": ok, "mail_info": info})
    _after(db, l, a, "accounts_created", f"{lid}: {sum(1 for o in out if o['link'])} comptes")
    notify(db, inst.owner_id, f"Des comptes candidats ont été créés à partir de votre liste « {l.title} ».")
    db.commit()
    return {"created": sum(1 for o in out if o["link"]), "invitations": out, "smtp_enabled": smtp_enabled(),
            "valid_days": settings.activation_days,
            "warning": "Copiez ou exportez ces liens maintenant : ils ne seront plus affichés (utilisez « Réémettre l'invitation » si besoin)."}


# ------------------------------------------------------------------ vérification des informations déclarées
@router.get("/verifications")
def verifications(db: Session = Depends(get_db)):
    degs = db.scalars(select(Degree).where(Degree.status.in_(["declared", "in_review", "to_complete"])).limit(200)).all()
    exps = db.scalars(select(Experience).where(Experience.status == "declared").limit(200)).all()
    sk = db.scalars(select(Skill).where(Skill.verified.is_(False)).limit(200)).all()
    name = lambda p: p.user.full_name
    return {"degrees": [{"id": d.id, "graduate": name(d.graduate), "title": d.title, "level": d.level.label, "year": d.year, "status": d.status, "source": d.source,
                         "institution_name": d.institution_name, "reference": d.reference} for d in degs],
            "experiences": [{"id": e.id, "graduate": name(e.graduate), "organization": e.organization, "role": e.role, "kind": e.kind,
                             "start_date": e.start_date.isoformat(), "end_date": e.end_date.isoformat() if e.end_date else None} for e in exps],
            "skills": [{"id": s.id, "graduate": name(s.graduate), "name": s.name} for s in sk]}


class VerifyIn(BaseModel):
    status: Literal["verified", "rejected", "to_complete", "in_review"] = "verified"


@router.post("/verify/degree/{did}")
def verify_degree(did: int, data: VerifyIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    d = db.get(Degree, did)
    if not d:
        raise HTTPException(404, "Diplôme introuvable")
    d.status = data.status
    notify(db, d.graduate.user_id, f"Votre diplôme « {d.title} » est maintenant au statut : {data.status}.")
    audit(db, a.id, "degree_status", f"{did}={data.status}"); db.commit()
    return {"id": d.id, "status": d.status}


@router.post("/verify/experience/{eid}")
def verify_exp(eid: int, data: VerifyIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    e = db.get(Experience, eid)
    if not e or data.status not in ("verified", "rejected"):
        raise HTTPException(404, "Expérience introuvable ou statut invalide")
    e.status = data.status
    audit(db, a.id, "experience_status", f"{eid}={data.status}"); db.commit()
    return {"id": e.id, "status": e.status}


@router.post("/verify/skill/{sid}")
def verify_skill(sid: int, a: User = Depends(_admin), db: Session = Depends(get_db)):
    s = db.get(Skill, sid)
    if not s:
        raise HTTPException(404, "Compétence introuvable")
    s.verified = True
    audit(db, a.id, "skill_verified", str(sid)); db.commit()
    return {"id": s.id, "verified": True}


# ------------------------------------------------------------------ référentiels : niveaux de diplôme et spécialités
def _lv(l: DegreeLevel) -> dict:
    return {"id": l.id, "code": l.code, "label": l.label, "family": l.family, "rank": l.rank, "active": l.active}


@router.get("/levels")
def levels(db: Session = Depends(get_db)):
    return [_lv(l) for l in db.scalars(select(DegreeLevel).order_by(DegreeLevel.rank, DegreeLevel.id)).all()]


@router.post("/levels", status_code=201)
def add_level(data: LevelIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    if db.scalar(select(DegreeLevel).where(DegreeLevel.code == data.code)):
        raise HTTPException(409, "Ce code existe déjà")
    l = DegreeLevel(**data.model_dump()); db.add(l); audit(db, a.id, "level_created", data.code); db.commit()
    return _lv(l)


@router.put("/levels/{lid}")
def edit_level(lid: int, data: LevelIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    l = db.get(DegreeLevel, lid)
    if not l:
        raise HTTPException(404, "Niveau introuvable")
    if data.code != l.code and db.scalar(select(DegreeLevel).where(DegreeLevel.code == data.code)):
        raise HTTPException(409, "Ce code existe déjà")
    for k, v in data.model_dump().items():
        setattr(l, k, v)
    audit(db, a.id, "level_updated", l.code); db.commit()
    return _lv(l)


@router.get("/specialties")
def specialties(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "domain": s.domain, "active": s.active} for s in db.scalars(select(Specialty).order_by(Specialty.name)).all()]


@router.post("/specialties", status_code=201)
def add_specialty(data: SpecialtyIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    if db.scalar(select(Specialty).where(func.lower(Specialty.name) == data.name.lower())):
        raise HTTPException(409, "Cette spécialité existe déjà")
    s = Specialty(**data.model_dump()); db.add(s); audit(db, a.id, "specialty_created", data.name); db.commit()
    return {"id": s.id, "name": s.name, "domain": s.domain, "active": s.active}


@router.put("/specialties/{sid}")
def edit_specialty(sid: int, data: SpecialtyIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    s = db.get(Specialty, sid)
    if not s:
        raise HTTPException(404, "Spécialité introuvable")
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    audit(db, a.id, "specialty_updated", s.name); db.commit()
    return {"id": s.id, "name": s.name, "domain": s.domain, "active": s.active}


# ------------------------------------------------------------------ offres, signalements, collaborations
class ModerationIn(BaseModel):
    moderation: Literal["ok", "suspended"]
    reason: str = ""


@router.get("/offers")
def offers(status: str = "", moderation: str = "", db: Session = Depends(get_db)):
    q = select(Opportunity).order_by(Opportunity.id.desc()).limit(300)
    if status:
        q = q.where(Opportunity.status == status)
    if moderation:
        q = q.where(Opportunity.moderation == moderation)
    return [opp_out(o) for o in db.scalars(q).all()]


class OfferReviewIn(BaseModel):
    action: Literal["approve", "request_changes", "reject"]
    reason: str = ""


@router.post("/offers/{oid}/review")
def review_offer(oid: int, data: OfferReviewIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    o = db.get(Opportunity, oid)
    if not o:
        raise HTTPException(404, "Offre introuvable")
    if o.status != "pending_review":
        raise HTTPException(409, "Cette offre n'est pas dans la file de validation")
    if data.action in ("request_changes", "reject") and len(data.reason.strip()) < 5:
        raise HTTPException(422, "Un motif précis d'au moins 5 caractères est requis")
    if data.action == "approve":
        if o.org.status != "validated":
            raise HTTPException(409, "L'entreprise doit être validée avant la publication")
        if o.moderation == "suspended":
            raise HTTPException(409, "Cette offre est suspendue : rétablissez-la avant de l'approuver")
        _check_publish(db, o.org, o.id, o.deadline)
        o.status, o.review_reason, o.reviewed_at = "published", "", now()
        # Snapshot privé du matching : seuls les candidats ayant donné leur accord sont évalués.
        db.query(OfferMatch).filter(OfferMatch.opportunity_id == o.id).delete(synchronize_session=False)
        candidates = db.scalars(select(GraduateProfile).join(User, User.id == GraduateProfile.user_id).where(
            GraduateProfile.matching_opt_in.is_(True), User.status == "active")).all()
        scored = []
        weights = match_weights(db)
        for profile in candidates:
            result = match(offer_criteria(o), candidate_data(profile), weights)
            scored.append((profile, result))
        scored.sort(key=lambda item: (-item[1]["score"], item[0].id))
        scored = [(profile, result) for profile, result in scored if result["score"] > 0]
        total = len(scored)
        previous_score, current_rank = None, 0
        for index, (profile, result) in enumerate(scored, 1):
            if result["score"] != previous_score:
                current_rank = index
                previous_score = result["score"]
            db.add(OfferMatch(opportunity_id=o.id, graduate_id=profile.id, score=result["score"], rank=current_rank,
                              total=total, criteria_json=json.dumps(result.get("criteria", []), ensure_ascii=False),
                              algorithm_version="1.0"))
            notify(db, profile.user_id, f"Nouvelle opportunité : « {o.title} ». Votre correspondance indicative est de {result['score']}/100 (rang {current_rank} sur {total} profils correspondants consentants). Consultez l'offre pour en savoir plus.")
        notify(db, o.org.owner_id, f"Votre offre « {o.title} » a été approuvée et publiée. {total} profil(s) consentant(s) ont été évalués par le matching.")
    elif data.action == "request_changes":
        o.status, o.review_reason, o.reviewed_at = "changes_requested", data.reason.strip(), now()
        notify(db, o.org.owner_id, f"Des corrections sont demandées pour votre offre « {o.title} » : {o.review_reason}")
    else:
        o.status, o.review_reason, o.reviewed_at = "archived", data.reason.strip(), now()
        notify(db, o.org.owner_id, f"Votre offre « {o.title} » n'a pas été retenue : {o.review_reason}")
    audit(db, a.id, "offer_review", f"{oid}={data.action} {data.reason}")
    db.commit()
    return {**opp_out(o), "matching_count": db.scalar(select(func.count()).select_from(OfferMatch).where(OfferMatch.opportunity_id == o.id)) or 0}


@router.post("/offers/{oid}/moderation")
def moderate_offer(oid: int, data: ModerationIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    o = db.get(Opportunity, oid)
    if not o:
        raise HTTPException(404, "Offre introuvable")
    o.moderation = data.moderation
    notify(db, o.org.owner_id, f"Votre offre « {o.title} » a été {'suspendue par l’administration' if data.moderation == 'suspended' else 'rétablie'}. {data.reason}")
    audit(db, a.id, "offer_moderation", f"{oid}={data.moderation} {data.reason}"); db.commit()
    return opp_out(o)


@router.get("/reports")
def reports(status: str = "", db: Session = Depends(get_db)):
    q = select(Report).order_by(Report.id.desc()).limit(300)
    if status:
        q = q.where(Report.status == status)
    out = []
    for r in db.scalars(q).all():
        tgt = ""
        if r.kind == "evaluation":
            e = db.get(Evaluation, r.target_id); tgt = f"Évaluation #{r.target_id} (moyenne {e.average:.1f}, {e.status}) : {e.comment}" if e else "supprimée"
        elif r.kind == "recommendation":
            x = db.get(Recommendation, r.target_id); tgt = f"Recommandation #{r.target_id} ({x.status}) : {x.text}" if x else "supprimée"
        elif r.kind == "offer":
            x = db.get(Opportunity, r.target_id); tgt = f"Offre #{r.target_id} : {x.title}" if x else "supprimée"
        elif r.kind == "profile":
            x = db.get(GraduateProfile, r.target_id); tgt = f"Profil #{r.target_id} : {x.user.full_name}" if x else "supprimé"
        out.append({"id": r.id, "kind": r.kind, "target_id": r.target_id, "target": tgt, "reason": r.reason, "status": r.status, "resolution": r.resolution,
                    "reporter": {"id": r.reporter.id, "full_name": r.reporter.full_name, "role": r.reporter.role}, "created_at": r.created_at.isoformat()})
    return out


@router.post("/reports/{rid}/resolve")
def resolve_report(rid: int, data: ResolveIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    r = db.get(Report, rid)
    if not r:
        raise HTTPException(404, "Signalement introuvable")
    if r.status != "open":
        raise HTTPException(409, "Signalement déjà traité")
    if data.action == "hide":
        if r.kind == "evaluation":
            e = db.get(Evaluation, r.target_id)
            if e: e.status = "hidden"
        elif r.kind == "recommendation":
            x = db.get(Recommendation, r.target_id)
            if x: x.status = "hidden"
        elif r.kind == "offer":
            x = db.get(Opportunity, r.target_id)
            if x: x.moderation = "suspended"
        elif r.kind == "profile":
            x = db.get(GraduateProfile, r.target_id)
            if x: x.visible = False
    elif data.action in ("keep", "restore") and r.kind == "evaluation":
        e = db.get(Evaluation, r.target_id)
        if e and e.status in ("contested", "hidden"):
            e.status = "published"
    r.status = "resolved" if data.action == "hide" else "dismissed"
    r.resolution = data.resolution or {"hide": "Contenu retiré", "keep": "Contenu maintenu", "restore": "Contenu rétabli"}[data.action]
    notify(db, r.reporter_id, f"Votre signalement #{r.id} a été traité : {r.resolution}")
    audit(db, a.id, "report_resolved", f"{rid}:{data.action}"); db.commit()
    return {"id": r.id, "status": r.status, "resolution": r.resolution}


@router.get("/collaborations")
def collabs(status: str = "", db: Session = Depends(get_db)):
    q = select(Collaboration).order_by(Collaboration.id.desc()).limit(300)
    if status:
        q = q.where(Collaboration.status == status)
    return [{"id": c.id, "company": c.company.name, "graduate": c.graduate.user.full_name, "title": c.title, "kind": c.kind, "source": c.source,
             "status": c.status, "start_date": c.start_date.isoformat(), "end_date": c.end_date.isoformat() if c.end_date else None}
            for c in db.scalars(q).all()]


class CollabDecision(BaseModel):
    approve: bool


@router.post("/collaborations/{cid}/verify")
def verify_collab(cid: int, data: CollabDecision, a: User = Depends(_admin), db: Session = Depends(get_db)):
    c = db.get(Collaboration, cid)
    if not c:
        raise HTTPException(404, "Collaboration introuvable")
    c.status = "verified" if data.approve else "rejected"
    notify(db, c.company.owner_id, f"Votre collaboration « {c.title} » a été {'vérifiée : vous pouvez évaluer ou recommander ce talent' if data.approve else 'refusée'}.")
    audit(db, a.id, "collab_verified", f"{cid}={c.status}"); db.commit()
    return {"id": c.id, "status": c.status}


# ------------------------------------------------------------------ abonnements, factures, paiements
@router.get("/plans")
def all_plans(db: Session = Depends(get_db)):
    return [plan_out(p) for p in db.scalars(select(Plan).order_by(Plan.sort, Plan.id)).all()]


@router.post("/plans", status_code=201)
def add_plan(data: PlanIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    if db.scalar(select(Plan).where(Plan.code == data.code)):
        raise HTTPException(409, "Ce code de formule existe déjà")
    p = Plan(**data.model_dump()); db.add(p); audit(db, a.id, "plan_created", data.code); db.commit()
    return plan_out(p)


@router.put("/plans/{pid}")
def edit_plan(pid: int, data: PlanIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    p = db.get(Plan, pid)
    if not p:
        raise HTTPException(404, "Formule introuvable")
    if data.code != p.code and db.scalar(select(Plan).where(Plan.code == data.code)):
        raise HTTPException(409, "Ce code de formule existe déjà")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    audit(db, a.id, "plan_updated", p.code); db.commit()  # les droits s'appliquent immédiatement (contrôlés à chaque requête)
    return plan_out(p)


@router.get("/subscriptions")
def subscriptions(db: Session = Depends(get_db)):
    rows = db.scalars(select(Subscription).order_by(Subscription.id.desc()).limit(300)).all()
    return [{**sub_out(s), "org": {"id": s.org.id, "name": s.org.name}} for s in rows]


class GrantIn(BaseModel):
    org_id: int
    plan_code: str
    months: int = 1
    reason: str = ""


@router.post("/subscriptions/grant", status_code=201)
def grant(data: GrantIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    """Octroi manuel (ex. règlement hors plateforme confirmé par l'administration, ou geste commercial). Facture à 0 XOF si offert."""
    o, plan = db.get(Organization, data.org_id), db.scalar(select(Plan).where(Plan.code == data.plan_code))
    if not o or o.kind != "company" or not plan or not 1 <= data.months <= 12:
        raise HTTPException(404, "Entreprise, formule ou durée invalide")
    sub = Subscription(org_id=o.id, plan_id=plan.id, status="pending_payment", months=data.months); db.add(sub); db.flush()
    inv = Invoice(org_id=o.id, subscription_id=sub.id, amount_xof=0, status="unpaid", description=f"Abonnement {plan.name} offert/manuel — {data.reason}"[:300])
    db.add(inv); db.flush(); inv.number = f"AC-{now().year}-{inv.id:05d}"
    pay = Payment(invoice_id=inv.id, org_id=o.id, provider="manual", mode="live", reference=new_reference(), amount_xof=0, status="pending")
    db.add(pay); db.flush()
    settle(db, pay, a.id, provider="manual")
    db.commit()
    return sub_out(sub)


@router.post("/subscriptions/{sid}/cancel")
def cancel_sub(sid: int, a: User = Depends(_admin), db: Session = Depends(get_db)):
    s = db.get(Subscription, sid)
    if not s:
        raise HTTPException(404, "Abonnement introuvable")
    s.status = "cancelled"
    notify(db, s.org.owner_id, f"Votre abonnement {s.plan.name} a été annulé par l'administration.")
    audit(db, a.id, "subscription_cancelled", str(sid)); db.commit()
    return sub_out(s)


@router.get("/payments")
def payments(status: str = "", db: Session = Depends(get_db)):
    q = select(Payment).order_by(Payment.id.desc()).limit(300)
    if status:
        q = q.where(Payment.status == status)
    return [{**payment_out(p), "org": {"id": p.org.id, "name": p.org.name}} for p in db.scalars(q).all()]


@router.get("/invoices")
def invoices(db: Session = Depends(get_db)):
    return [invoice_out(i) for i in db.scalars(select(Invoice).order_by(Invoice.id.desc()).limit(300)).all()]


@router.post("/payments/{reference}/mark-paid")
def mark_paid(reference: str, a: User = Depends(_admin), db: Session = Depends(get_db)):
    """Rapprochement manuel : l'administrateur atteste avoir reçu le règlement (virement, mobile money…). Non vérifié automatiquement."""
    p = db.scalar(select(Payment).where(Payment.reference == reference))
    if not p or p.status != "pending":
        raise HTTPException(404, "Paiement en attente introuvable")
    p.mode = "live" if p.mode == "live" else p.mode
    settle(db, p, a.id, provider="manual")
    db.commit()
    return payment_out(p)


# ------------------------------------------------------------------ paramètres, journal, messages
@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {"contact_email": get_setting(db, "contact_email"), "support_phone": get_setting(db, "support_phone"),
            "terms_version": get_setting(db, "terms_version", "1.0"), "matching_weights": match_weights(db), "default_weights": DEFAULT_WEIGHTS,
            "payment_mode": settings.payment_mode, "payment_provider": settings.payment_provider, "smtp_enabled": smtp_enabled(),
            "reputation_weights": json.loads(get_setting(db, "reputation_weights", "{}") or "{}")}


@router.put("/settings")
def put_settings(data: SettingsIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    for k, v in data.model_dump().items():
        set_setting(db, k, v)
    audit(db, a.id, "settings_updated"); db.commit()
    return {"ok": True}


@router.put("/settings/matching-weights")
def put_weights(data: WeightsIn, a: User = Depends(_admin), db: Session = Depends(get_db)):
    set_setting(db, "matching_weights", json.dumps(data.model_dump()))
    audit(db, a.id, "matching_weights_updated", json.dumps(data.model_dump())); db.commit()
    return {"matching_weights": data.model_dump()}


@router.get("/audit")
def audit_log(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [{"id": r.id, "actor_id": r.actor_id, "action": r.action, "detail": r.detail, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/contacts")
def contacts(db: Session = Depends(get_db)):
    rows = db.scalars(select(ContactMessage).order_by(ContactMessage.id.desc()).limit(200)).all()
    return [{"id": r.id, "name": r.name, "email": r.email, "message": r.message, "created_at": r.created_at.isoformat()} for r in rows]
