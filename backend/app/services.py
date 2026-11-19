"""Services métier partagés par les routes (accès base de données)."""
import json
from datetime import date, datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from .config import settings
from .models import (User, Organization, DegreeLevel, Specialty, GraduateProfile, Degree, Experience, Skill, Opportunity,
                     Subscription, Plan, ProfileView, Evaluation, Recommendation, Setting, SubmittedRow, SubmittedList, now)
from .security import new_activation_token
from .logic import matching as M, reputation as R
from .logic.entitlements import subscription_is_current, month_key, quota_left
from .logic.text import norm, csv_list
from .deps import notify, audit

AVAIL = M.AVAILABILITY_LABEL


# ------------------------------------------------------------------ réglages
def get_setting(db: Session, key: str, default: str = "") -> str:
    s = db.get(Setting, key)
    return s.value if s else default


def set_setting(db: Session, key: str, value: str):
    s = db.get(Setting, key)
    if s:
        s.value = value
    else:
        db.add(Setting(key=key, value=value))


def match_weights(db: Session) -> dict:
    try:
        return {**M.DEFAULT_WEIGHTS, **json.loads(get_setting(db, "matching_weights", "{}") or "{}")}
    except ValueError:
        return dict(M.DEFAULT_WEIGHTS)


# ------------------------------------------------------------------ diplômes, profils, matching
def level_lookup(db: Session) -> dict[str, str]:
    out = {}
    for lv in db.scalars(select(DegreeLevel).where(DegreeLevel.active)).all():
        out[norm(lv.code)] = lv.code
        out[norm(lv.label)] = lv.code
    # intitulés courants qui désignent un niveau du référentiel (jamais une équivalence académique officielle)
    for alias, code in {"deat": "TECH", "beat": "TECH", "cap": "TECH", "bts": "BTS_DUT", "dut": "BTS_DUT", "deust": "BTS_DUT",
                        "licence": "LIC_ACAD", "ingenieur": "INGENIEUR", "doctorat": "DOCTORAT", "phd": "DOCTORAT"}.items():
        if db.scalar(select(func.count()).select_from(DegreeLevel).where(DegreeLevel.code == code)):
            out.setdefault(alias, code)
    return out


def specialty_name(d: Degree) -> str | None:
    return d.specialty.name if d.specialty else (d.specialty_text or None)


def candidate_data(p: GraduateProfile, today: date | None = None) -> M.CandidateData:
    degs = [M.DegreeInfo(d.title, d.level.code, d.level.rank, specialty_name(d), d.specialty.domain if d.specialty else None, d.status)
            for d in p.degrees]
    periods = [(e.start_date, e.end_date) for e in p.experiences if e.status != "rejected"]
    return M.CandidateData(degs, {norm(s.name) for s in p.skills}, M.experience_years(periods, today), p.location, p.availability)


def offer_criteria(o: Opportunity) -> M.OfferCriteria:
    return M.OfferCriteria(
        level_code=o.level.code, level_rank=o.level.rank, degree_mandatory=o.degree_mandatory,
        accepted_level_codes=csv_list(o.accepted_level_codes), accepted_titles=csv_list(o.accepted_titles),
        allow_higher=o.allow_higher, allow_lower_alt=o.allow_lower_alt,
        specialty=o.specialty.name if o.specialty else None, specialty_domain=o.specialty.domain if o.specialty else None,
        specialty_required=o.specialty_required, min_experience_years=o.min_experience_years or 0,
        experience_mandatory=o.experience_mandatory, required_skills=csv_list(o.required_skills),
        desired_skills=csv_list(o.desired_skills), location=o.location)


def reputation_of(db: Session, p: GraduateProfile) -> dict:
    ev = db.scalars(select(Evaluation).where(Evaluation.graduate_id == p.id, Evaluation.status == "published")).all()
    recos = db.scalar(select(func.count()).select_from(Recommendation).where(Recommendation.graduate_id == p.id, Recommendation.status == "published"))
    try:
        w = json.loads(get_setting(db, "reputation_weights", "{}") or "{}")
    except ValueError:
        w = {}
    return R.reputation_score([(e.average, e.created_at.date()) for e in ev], sum(1 for s in p.skills if s.verified), len(p.skills),
                              any(d.status == "verified" for d in p.degrees), p.origin == "institution" and p.institution_id is not None,
                              len(p.achievements), recos or 0, weights=w or None)


def degree_out(d: Degree) -> dict:
    return {"id": d.id, "title": d.title, "level": {"id": d.level.id, "code": d.level.code, "label": d.level.label},
            "specialty_id": d.specialty_id, "specialty": specialty_name(d) or "", "institution_name": d.institution_name,
            "country": d.country, "year": d.year, "reference": d.reference, "honors": d.honors, "status": d.status, "source": d.source}


def exp_out(e: Experience) -> dict:
    return {"id": e.id, "kind": e.kind, "organization": e.organization, "role": e.role, "sector": e.sector,
            "start_date": e.start_date.isoformat(), "end_date": e.end_date.isoformat() if e.end_date else None,
            "description": e.description, "status": e.status}


def completeness(p: GraduateProfile) -> int:
    checks = [bool(p.headline), bool(p.bio), bool(p.location), bool(p.degrees), bool(p.experiences), bool(p.skills),
              bool(p.achievements), bool(p.cv_path)]
    return round(100 * sum(checks) / len(checks))


def talent_summary(db: Session, p: GraduateProfile, offer_match: dict | None = None, weights: dict | None = None) -> dict:
    """Vue « carte » : diplôme, expérience, réputation, disponibilité — toujours séparés (jamais fusionnés)."""
    cd = candidate_data(p)
    top = max(p.degrees, key=lambda d: (d.level.rank, d.status == "verified"), default=None)
    rep = reputation_of(db, p)
    out = {"id": p.id, "full_name": p.user.full_name, "headline": p.headline, "location": p.location,
           "degree": degree_out(top) if top else None,
           "experience": {"years": cd.experience_years, "category": M.experience_category(cd.experience_years)},
           "reputation": {"score": rep["score"], "provisional": rep["provisional"], "evaluations_count": rep["evaluations_count"]},
           "availability": {"status": p.availability, "label": AVAIL.get(p.availability, p.availability),
                            "updated_at": p.availability_updated_at.date().isoformat()},
           "skills": [s.name for s in p.skills], "origin": p.origin,
           "institution": p.institution.name if p.institution else None}
    if offer_match is not None:
        out["match"] = offer_match
    return out


# ------------------------------------------------------------------ abonnements
def current_subscription(db: Session, org_id: int) -> Subscription | None:
    today = date.today()
    subs = db.scalars(select(Subscription).where(Subscription.org_id == org_id, Subscription.status == "active")).all()
    for s in subs:
        if s.end_date and s.end_date < today:
            s.status = "expired"
    cur = [s for s in subs if subscription_is_current(s.status, s.start_date, s.end_date, today)]
    db.flush()
    return max(cur, key=lambda s: s.end_date) if cur else None


def views_used(db: Session, org_id: int) -> int:
    return db.scalar(select(func.count()).select_from(ProfileView).where(ProfileView.company_id == org_id, ProfileView.month == month_key())) or 0


def active_offers_count(db: Session, org_id: int, exclude_id: int | None = None) -> int:
    q = select(func.count()).select_from(Opportunity).where(Opportunity.org_id == org_id, Opportunity.status == "published")
    if exclude_id:
        q = q.where(Opportunity.id != exclude_id)
    return db.scalar(q) or 0


def entitlements(db: Session, org: Organization) -> dict:
    sub = current_subscription(db, org.id)
    plan = sub.plan if sub else (db.scalar(select(Plan).where(Plan.code == "business", Plan.active)) if not settings.billing_enabled else None)
    used_v, used_o = views_used(db, org.id), active_offers_count(db, org.id)
    return {
        "active": bool(plan), "plan": plan_out(plan) if plan else None,
        "start_date": sub.start_date.isoformat() if sub else None, "end_date": sub.end_date.isoformat() if sub else None,
        "auto_renew": sub.auto_renew if sub else False,
        "can_search": bool(plan and plan.can_search), "can_advanced_filters": bool(plan and plan.can_advanced_filters),
        "can_see_matching": bool(plan and plan.can_see_matching), "can_see_contacts": bool(plan and plan.can_see_contacts),
        "offers": {"used": used_o, "limit": plan.max_active_offers if plan else 0, "left": quota_left(plan.max_active_offers, used_o) if plan else 0},
        "views": {"used": used_v, "limit": plan.profile_views_per_month if plan else 0, "left": quota_left(plan.profile_views_per_month, used_v) if plan else 0},
    }


def require_subscription(db: Session, org: Organization) -> Plan:
    if not settings.billing_enabled:
        plan = db.scalar(select(Plan).where(Plan.code == "business", Plan.active))
        if plan:
            return plan
    sub = current_subscription(db, org.id)
    if not sub:
        raise HTTPException(402, "Abonnement requis : aucun abonnement actif. Choisissez une formule dans « Abonnement ».")
    return sub.plan


def plan_out(p: Plan) -> dict:
    return {"id": p.id, "code": p.code, "name": p.name, "description": p.description, "price_xof": p.price_xof,
            "duration_days": p.duration_days, "max_active_offers": p.max_active_offers,
            "profile_views_per_month": p.profile_views_per_month, "can_search": p.can_search,
            "can_advanced_filters": p.can_advanced_filters, "can_see_matching": p.can_see_matching,
            "can_see_contacts": p.can_see_contacts, "active": p.active, "sort": p.sort}


# ------------------------------------------------------------------ création de comptes candidats (administration)
def issue_invitation(user: User) -> str:
    raw, h = new_activation_token()
    user.activation_hash = h
    user.activation_expires = now() + timedelta(days=settings.activation_days)
    return f"{settings.app_url}/activation?token={raw}"


def create_graduate_account(db: Session, *, full_name: str, email: str, phone: str, institution_id: int | None, degree_title: str,
                            level_id: int, specialty_text: str, year: int | None, honors: str, country: str, institution_name: str,
                            origin: str = "institution") -> tuple[User, str]:
    """Crée un compte en attente d'activation + profil + diplôme VÉRIFIÉ par l'administration. Retourne (user, lien)."""
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, f"Un compte existe déjà pour {email}")
    u = User(email=email, password_hash="!", full_name=full_name, phone=phone, role="graduate", status="pending_activation")
    db.add(u); db.flush()
    spec = db.scalar(select(Specialty).where(func.lower(Specialty.name) == specialty_text.strip().lower())) if specialty_text else None
    p = GraduateProfile(user_id=u.id, institution_id=institution_id, origin=origin, phone=phone, visible=False)
    db.add(p); db.flush()
    db.add(Degree(graduate_id=p.id, title=degree_title, level_id=level_id, specialty_id=spec.id if spec else None,
                  specialty_text=specialty_text, institution_name=institution_name, country=country or "Bénin", year=year,
                  honors=honors, status="verified", source="institution"))
    link = issue_invitation(u)
    return u, link


def level_id_by_code(db: Session, code: str) -> int | None:
    lv = db.scalar(select(DegreeLevel).where(DegreeLevel.code == code))
    return lv.id if lv else None


def list_counts(l: SubmittedList) -> dict:
    c = {"pending": 0, "invalid": 0, "validated": 0, "rejected": 0, "account_created": 0}
    for r in l.rows:
        c[r.status] = c.get(r.status, 0) + 1
    c["total"] = len(l.rows)
    return c


def recompute_list_status(l: SubmittedList):
    """received → in_review dès qu'une ligne est traitée ; validated / partially_validated / rejected quand tout est traité."""
    c = list_counts(l)
    open_ = c["pending"] + c["invalid"]
    ok = c["validated"] + c["account_created"]
    if c["total"] == 0:
        return
    if open_ > 0:
        if ok + c["rejected"] > 0:
            l.status = "in_review"
        return
    l.status = "rejected" if ok == 0 else ("partially_validated" if c["rejected"] > 0 else "validated")
    l.reviewed_at = now()


# ------------------------------------------------------------------ activation d'un abonnement après paiement confirmé
def activate_subscription(db: Session, sub: Subscription):
    from .logic.entitlements import extend_end
    today = date.today()
    days = sub.plan.duration_days * (sub.months or 1)
    existing = current_subscription(db, sub.org_id)
    if existing and existing.id != sub.id and existing.plan_id == sub.plan_id:  # renouvellement : à la suite de la période en cours
        sub.start_date = existing.end_date + timedelta(days=1)
        sub.end_date = extend_end(existing.end_date, today, days)
    else:  # première souscription ou changement de formule : démarre aujourd'hui (pas de prorata, voir README)
        if existing and existing.id != sub.id:
            existing.status = "replaced"
        sub.start_date = today
        sub.end_date = today + timedelta(days=days - 1)
    sub.status = "active"
