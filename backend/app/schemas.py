import re
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

from .communes import COMMUNES
from .security import password_problem

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CONTACT_LEAK = re.compile(r"(https?://|www\.|[\w.+-]+@[\w-]+\.[\w.]+|(?:\+?\d[\s.-]?){8,})", re.I)


def _email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL.match(v):
        raise ValueError("Email invalide")
    return v


def _loc(v):
    if v in ("", None):
        return v
    if v not in COMMUNES:
        raise ValueError("Commune inconnue : choisissez une commune du Bénin")
    return v


def _country(v: str) -> str:
    if v != "Bénin":
        raise ValueError("Seul le Bénin est disponible pour le moment")
    return v


def _strong(v: str) -> str:
    p = password_problem(v)
    if p:
        raise ValueError(p)
    return v


def _clean_comment(v: str) -> str:
    v = (v or "").strip()
    if CONTACT_LEAK.search(v):
        raise ValueError("Les commentaires ne doivent contenir ni coordonnées personnelles, ni adresse email, ni lien")
    return v


# ------------------------------------------------------------------ authentification
class RegisterOrgIn(BaseModel):
    """Inscription publique d’une entreprise ou d’un établissement."""
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: Literal["company", "institution"]
    org_name: str = Field(min_length=2, max_length=200)
    accept_terms: bool
    _e = field_validator("email")(_email)
    _p = field_validator("password")(_strong)


class LoginIn(BaseModel):
    email: str
    password: str
    _e = field_validator("email")(_email)


class ActivateIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    accept_terms: bool
    _p = field_validator("password")(_strong)


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    _p = field_validator("new_password")(_strong)


class PasswordResetRequestIn(BaseModel):
    email: str
    _e = field_validator("email")(_email)


class PasswordResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)
    _p = field_validator("new_password")(_strong)


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    message: str = Field(min_length=10, max_length=5000)
    _e = field_validator("email")(_email)


# ------------------------------------------------------------------ talents
Availability = Literal["available", "employed_open", "temporary_mission", "unavailable"]


class ProfileIn(BaseModel):
    headline: str = Field(default="", max_length=200)
    bio: str = Field(default="", max_length=5000)
    location: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=40)
    availability: Availability = "available"
    available_from: date | None = None
    visible: bool = True
    show_contact: bool = False
    show_cv: bool = False
    matching_opt_in: bool = False
    _l = field_validator("location")(_loc)


class DegreeIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    level_id: int
    specialty_id: int | None = None
    specialty_text: str = Field(default="", max_length=200)
    institution_name: str = Field(default="", max_length=200)
    country: str = Field(default="Bénin", max_length=80)
    year: int | None = Field(default=None, ge=1950, le=2100)
    reference: str = Field(default="", max_length=120)
    honors: str = Field(default="", max_length=80)


class ExperienceIn(BaseModel):
    kind: Literal["job", "internship", "apprenticeship", "mission"] = "job"
    organization: str = Field(min_length=2, max_length=200)
    role: str = Field(min_length=2, max_length=200)
    sector: str = Field(default="", max_length=120)
    start_date: date
    end_date: date | None = None
    description: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("La date de fin précède la date de début")
        if self.start_date > date.today():
            raise ValueError("La date de début est dans le futur")
        return self


class SkillIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class AchievementIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=3000)
    year: int | None = Field(default=None, ge=1950, le=2100)


# ------------------------------------------------------------------ organisations
class OrgIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    sector: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=120)
    country: str = Field(default="Bénin", max_length=80)
    website: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=40)
    registration_no: str = Field(default="", max_length=80)
    _c = field_validator("city")(_loc)
    _p = field_validator("country")(_country)


# ------------------------------------------------------------------ offres
OppType = Literal["job", "internship", "apprenticeship", "mission", "training"]
OppStatus = Literal["draft", "published", "pending_review", "paused", "archived"]
Contract = Literal["", "CDI", "CDD", "stage", "alternance", "mission", "freelance"]


class OppIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    sector: str = Field(default="", max_length=120)
    type: OppType
    contract_type: Contract = ""
    duration: str = Field(default="", max_length=80)
    salary_type: Literal["fixed", "range", "negotiable", "unpaid"] = "negotiable"
    salary_min: int | None = Field(default=None, ge=0, le=100000000)
    salary_max: int | None = Field(default=None, ge=0, le=100000000)
    salary_period: Literal["month", "day", "hour", "project"] = "month"
    salary_currency: Literal["XOF"] = "XOF"
    benefits: str = Field(default="", max_length=3000)
    location: str = Field(default="", max_length=120)
    degree_level_id: int  # OBLIGATOIRE : jamais déduit du titre
    degree_mandatory: bool = True
    accepted_level_codes: list[str] = Field(default_factory=list, max_length=10)
    accepted_titles: list[str] = Field(default_factory=list, max_length=20)
    allow_higher: bool = True
    allow_lower_alt: bool = False
    specialty_id: int | None = None
    specialty_required: bool = False
    min_experience_years: float = Field(default=0, ge=0, le=50)
    experience_mandatory: bool = False
    required_skills: list[str] = Field(default_factory=list, max_length=30)
    desired_skills: list[str] = Field(default_factory=list, max_length=30)
    requirements: str = Field(default="", max_length=5000)
    deadline: date | None = None
    status: OppStatus = "draft"
    _l = field_validator("location")(_loc)


class OppPatch(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    sector: str | None = Field(default=None, max_length=120)
    type: OppType | None = None
    contract_type: Contract | None = None
    duration: str | None = Field(default=None, max_length=80)
    salary_type: Literal["fixed", "range", "negotiable", "unpaid"] | None = None
    salary_min: int | None = Field(default=None, ge=0, le=100000000)
    salary_max: int | None = Field(default=None, ge=0, le=100000000)
    salary_period: Literal["month", "day", "hour", "project"] | None = None
    salary_currency: Literal["XOF"] | None = None
    benefits: str | None = Field(default=None, max_length=3000)
    location: str | None = None
    degree_level_id: int | None = None
    degree_mandatory: bool | None = None
    accepted_level_codes: list[str] | None = None
    accepted_titles: list[str] | None = None
    allow_higher: bool | None = None
    allow_lower_alt: bool | None = None
    specialty_id: int | None = None
    specialty_required: bool | None = None
    min_experience_years: float | None = Field(default=None, ge=0, le=50)
    experience_mandatory: bool | None = None
    required_skills: list[str] | None = None
    desired_skills: list[str] | None = None
    requirements: str | None = None
    deadline: date | None = None
    status: OppStatus | None = None
    _l = field_validator("location")(_loc)


class ApplyIn(BaseModel):
    cover_letter: str = Field(default="", max_length=5000)


class StatusIn(BaseModel):
    status: Literal["received", "under_review", "shortlisted", "interview", "accepted", "rejected"]
    comment: str = Field(default="", max_length=2000)


# ------------------------------------------------------------------ listes d'établissements
class RowIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: str
    phone: str = Field(default="", max_length=40)
    degree_title: str = Field(min_length=2, max_length=200)
    level_code: str = Field(min_length=1, max_length=30)
    specialty: str = Field(default="", max_length=200)
    year: int | None = Field(default=None, ge=1970, le=2100)
    honors: str = Field(default="", max_length=80)
    country: str = Field(default="Bénin", max_length=80)
    _e = field_validator("email")(_email)


class ListMeta(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    academic_year: str = Field(default="", max_length=20)


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class NoteIn(BaseModel):
    note: str = Field(default="", max_length=2000)


# ------------------------------------------------------------------ collaborations, évaluations
Kind = Literal["job", "internship", "apprenticeship", "mission"]


class CollabIn(BaseModel):
    graduate_id: int
    kind: Kind = "job"
    title: str = Field(min_length=3, max_length=200)
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("La date de fin précède la date de début")
        return self


def Rating():
    return Field(ge=1, le=5)


class EvalIn(BaseModel):
    collaboration_id: int
    technical: int = Rating()
    deadlines: int = Rating()
    adaptability: int = Rating()
    professionalism: int = Rating()
    teamwork: int = Rating()
    results: int = Rating()
    comment: str = Field(default="", max_length=600)
    _c = field_validator("comment")(_clean_comment)


class RecoIn(BaseModel):
    collaboration_id: int
    text: str = Field(min_length=20, max_length=1000)
    _c = field_validator("text")(_clean_comment)


class SelectTalentsIn(BaseModel):
    offer_id: int = Field(gt=0)
    graduate_ids: list[int] = Field(min_length=1, max_length=100)


class ResponseIn(BaseModel):
    response: str = Field(min_length=3, max_length=600)
    _c = field_validator("response")(_clean_comment)


class ReportIn(BaseModel):
    kind: Literal["evaluation", "recommendation", "offer", "profile"]
    target_id: int
    reason: str = Field(min_length=10, max_length=2000)


class ResolveIn(BaseModel):
    action: Literal["hide", "keep", "restore"]
    resolution: str = Field(default="", max_length=2000)


# ------------------------------------------------------------------ abonnements
class SubscribeIn(BaseModel):
    plan_code: str = Field(min_length=2, max_length=30)
    months: int = Field(default=12, ge=12, le=12)
    auto_renew: bool = False


class PlanIn(BaseModel):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=1000)
    price_xof: int = Field(ge=0, le=100_000_000)
    duration_days: int = Field(default=30, ge=1, le=366)
    max_active_offers: int | None = Field(default=None, ge=0)
    profile_views_per_month: int | None = Field(default=None, ge=0)
    can_search: bool = False
    can_advanced_filters: bool = False
    can_see_matching: bool = False
    can_see_contacts: bool = False
    active: bool = True
    sort: int = 0


# ------------------------------------------------------------------ administration
class LevelIn(BaseModel):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Z0-9_]+$")
    label: str = Field(min_length=2, max_length=120)
    family: str = Field(default="", max_length=120)
    rank: int = Field(ge=1, le=20)
    active: bool = True


class SpecialtyIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    domain: str = Field(default="", max_length=80)
    active: bool = True


class OrgStatusIn(BaseModel):
    status: Literal["validated", "rejected", "suspended", "pending"]
    reason: str = Field(default="", max_length=1000)
    annual_quota: int | None = Field(default=None, ge=0, le=100000)


class AdminCreateGraduateIn(BaseModel):
    """Création manuelle d'un compte candidat hors liste (cas exceptionnel, tracé dans le journal)."""
    full_name: str = Field(min_length=2, max_length=160)
    email: str
    institution_id: int | None = None
    degree_title: str = Field(min_length=2, max_length=200)
    level_id: int
    specialty_text: str = Field(default="", max_length=200)
    year: int | None = Field(default=None, ge=1970, le=2100)
    _e = field_validator("email")(_email)


class WeightsIn(BaseModel):
    degree: int = Field(ge=0, le=100)
    specialty: int = Field(ge=0, le=100)
    skills: int = Field(ge=0, le=100)
    experience: int = Field(ge=0, le=100)
    location: int = Field(ge=0, le=100)
    availability: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _sum(self):
        if sum(self.model_dump().values()) <= 0:
            raise ValueError("La somme des pondérations doit être positive")
        return self


class SettingsIn(BaseModel):
    contact_email: str = Field(default="", max_length=255)
    support_phone: str = Field(default="", max_length=40)
    terms_version: str = Field(default="1.0", max_length=20)
