"""Modèle de données AgriConnect (SQLAlchemy 2.0)."""
from datetime import datetime, date, timezone
from sqlalchemy import String, Text, ForeignKey, Boolean, Date, DateTime, Integer, Float, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------- comptes
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # "!" = pas encore de mot de passe (invitation)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40), default="")
    role: Mapped[str] = mapped_column(String(20), index=True)  # graduate|company|institution|admin
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|pending_activation|suspended
    session_version: Mapped[int] = mapped_column(Integer, default=0)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    activation_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    activation_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reset_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class Organization(Base):
    """Entreprise (kind=company) ou établissement partenaire (kind=institution)."""
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sector: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    country: Mapped[str] = mapped_column(String(80), default="Bénin")
    website: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    registration_no: Mapped[str] = mapped_column(String(80), default="")  # IFU / RCCM
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|validated|rejected|suspended
    status_reason: Mapped[str] = mapped_column(Text, default="")
    annual_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)  # établissements
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    owner: Mapped[User] = relationship()

    @property
    def verified(self) -> bool:
        return self.status == "validated"


# ---------------------------------------------------------------- référentiels
class DegreeLevel(Base):
    __tablename__ = "degree_levels"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    family: Mapped[str] = mapped_column(String(120), default="")
    rank: Mapped[int] = mapped_column(Integer)  # ordre de comparaison (plus grand = cycle plus élevé)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Specialty(Base):
    __tablename__ = "specialties"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    domain: Mapped[str] = mapped_column(String(80), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------- talents
class GraduateProfile(Base):
    __tablename__ = "graduate_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), nullable=True, index=True)
    origin: Mapped[str] = mapped_column(String(30), default="institution")  # institution|company_recommended|admin
    headline: Mapped[str] = mapped_column(String(200), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    availability: Mapped[str] = mapped_column(String(30), default="available")  # available|employed_open|temporary_mission|unavailable
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    availability_updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    visible: Mapped[bool] = mapped_column(Boolean, default=True)       # visible des entreprises abonnées
    show_contact: Mapped[bool] = mapped_column(Boolean, default=False)  # coordonnées visibles
    show_cv: Mapped[bool] = mapped_column(Boolean, default=False)
    matching_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    matching_consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cv_path: Mapped[str] = mapped_column(String(255), default="")
    cv_name: Mapped[str] = mapped_column(String(255), default="")
    photo_path: Mapped[str] = mapped_column(String(255), default="")
    photo_name: Mapped[str] = mapped_column(String(255), default="")
    user: Mapped[User] = relationship()
    institution: Mapped[Organization | None] = relationship()
    degrees: Mapped[list["Degree"]] = relationship(back_populates="graduate", cascade="all, delete-orphan")
    experiences: Mapped[list["Experience"]] = relationship(back_populates="graduate", cascade="all, delete-orphan")
    skills: Mapped[list["Skill"]] = relationship(back_populates="graduate", cascade="all, delete-orphan")
    achievements: Mapped[list["Achievement"]] = relationship(back_populates="graduate", cascade="all, delete-orphan")


class Degree(Base):
    __tablename__ = "degrees"
    id: Mapped[int] = mapped_column(primary_key=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))  # intitulé EXACT
    level_id: Mapped[int] = mapped_column(ForeignKey("degree_levels.id"))
    specialty_id: Mapped[int | None] = mapped_column(ForeignKey("specialties.id"), nullable=True)
    specialty_text: Mapped[str] = mapped_column(String(200), default="")
    institution_name: Mapped[str] = mapped_column(String(200), default="")
    country: Mapped[str] = mapped_column(String(80), default="Bénin")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference: Mapped[str] = mapped_column(String(120), default="")
    honors: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="declared")  # declared|in_review|verified|rejected|to_complete
    source: Mapped[str] = mapped_column(String(20), default="self")  # self|institution
    graduate: Mapped[GraduateProfile] = relationship(back_populates="degrees")
    level: Mapped[DegreeLevel] = relationship()
    specialty: Mapped[Specialty | None] = relationship()


class Experience(Base):
    __tablename__ = "experiences"
    id: Mapped[int] = mapped_column(primary_key=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="job")  # job|internship|apprenticeship|mission
    organization: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(120), default="")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # None = en cours
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="declared")  # declared|verified|rejected
    graduate: Mapped[GraduateProfile] = relationship(back_populates="experiences")


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("graduate_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    graduate: Mapped[GraduateProfile] = relationship(back_populates="skills")


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graduate: Mapped[GraduateProfile] = relationship(back_populates="achievements")


# ---------------------------------------------------------------- listes d'établissements
class SubmittedList(Base):
    __tablename__ = "submitted_lists"
    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    academic_year: Mapped[str] = mapped_column(String(20), default="")
    filename: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(24), default="received", index=True)  # received|in_review|validated|partially_validated|rejected
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    institution: Mapped[Organization] = relationship()
    rows: Mapped[list["SubmittedRow"]] = relationship(back_populates="list", cascade="all, delete-orphan", order_by="SubmittedRow.line_no")


class SubmittedRow(Base):
    __tablename__ = "submitted_rows"
    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("submitted_lists.id"), index=True)
    line_no: Mapped[int] = mapped_column(Integer)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    degree_title: Mapped[str] = mapped_column(String(200), default="")
    level_code: Mapped[str] = mapped_column(String(30), default="")
    specialty: Mapped[str] = mapped_column(String(200), default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    honors: Mapped[str] = mapped_column(String(80), default="")
    country: Mapped[str] = mapped_column(String(80), default="Bénin")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|invalid|validated|rejected|account_created
    message: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    list: Mapped[SubmittedList] = relationship(back_populates="rows")
    user: Mapped[User | None] = relationship()


# ---------------------------------------------------------------- offres et candidatures
class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(String(120), default="")
    type: Mapped[str] = mapped_column(String(20), index=True)
    contract_type: Mapped[str] = mapped_column(String(30), default="")
    duration: Mapped[str] = mapped_column(String(80), default="")
    salary_type: Mapped[str] = mapped_column(String(20), default="negotiable")
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_period: Mapped[str] = mapped_column(String(20), default="month")
    salary_currency: Mapped[str] = mapped_column(String(8), default="XOF")
    benefits: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(120), default="", index=True)
    # --- exigences (saisies par l'entreprise, jamais déduites du titre) ---
    degree_level_id: Mapped[int] = mapped_column(ForeignKey("degree_levels.id"))
    degree_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    accepted_level_codes: Mapped[str] = mapped_column(String(300), default="")  # CSV de codes de niveau
    accepted_titles: Mapped[str] = mapped_column(Text, default="")             # CSV d'intitulés acceptés
    allow_higher: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_lower_alt: Mapped[bool] = mapped_column(Boolean, default=False)
    specialty_id: Mapped[int | None] = mapped_column(ForeignKey("specialties.id"), nullable=True)
    specialty_required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_experience_years: Mapped[float] = mapped_column(Float, default=0)
    experience_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    required_skills: Mapped[str] = mapped_column(Text, default="")
    desired_skills: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)  # draft|pending_review|changes_requested|published|paused|archived
    review_reason: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    moderation: Mapped[str] = mapped_column(String(20), default="ok")  # ok|suspended (administration)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    org: Mapped[Organization] = relationship()
    level: Mapped[DegreeLevel] = relationship()
    specialty: Mapped[Specialty | None] = relationship()


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("opportunity_id", "graduate_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"), index=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    opportunity: Mapped[Opportunity] = relationship()
    graduate: Mapped[User] = relationship()


class ApplicationEvent(Base):
    __tablename__ = "application_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class OfferMatch(Base):
    """Instantané privé du matching calculé à la validation d'une offre."""
    __tablename__ = "offer_matches"
    __table_args__ = (UniqueConstraint("opportunity_id", "graduate_id", name="uq_offer_matches_opportunity_graduate"), Index("ix_offer_matches_offer_rank", "opportunity_id", "rank"))
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), index=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    rank: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    criteria_json: Mapped[str] = mapped_column(Text, default="[]")
    algorithm_version: Mapped[str] = mapped_column(String(30), default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class TalentSelection(Base):
    """Talent choisi par une entreprise depuis le classement d'une offre."""
    __tablename__ = "talent_selections"
    __table_args__ = (UniqueConstraint("company_id", "opportunity_id", "graduate_id", name="uq_talent_selection"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), index=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


# ---------------------------------------------------------------- collaborations, évaluations, recommandations
class Collaboration(Base):
    __tablename__ = "collaborations"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="job")  # job|internship|apprenticeship|mission
    title: Mapped[str] = mapped_column(String(200))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="declared")  # declared|platform (embauche via AgriConnect)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|verified|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    company: Mapped[Organization] = relationship()
    graduate: Mapped[GraduateProfile] = relationship()


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (UniqueConstraint("collaboration_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    collaboration_id: Mapped[int] = mapped_column(ForeignKey("collaborations.id"))
    company_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    technical: Mapped[int] = mapped_column(Integer)
    deadlines: Mapped[int] = mapped_column(Integer)
    adaptability: Mapped[int] = mapped_column(Integer)
    professionalism: Mapped[int] = mapped_column(Integer)
    teamwork: Mapped[int] = mapped_column(Integer)
    results: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(600), default="")
    response: Mapped[str] = mapped_column(String(600), default="")  # droit de réponse du talent
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)  # published|contested|hidden
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    company: Mapped[Organization] = relationship()
    collaboration: Mapped[Collaboration] = relationship()

    @property
    def average(self) -> float:
        v = [self.technical, self.deadlines, self.adaptability, self.professionalism, self.teamwork, self.results]
        return sum(v) / len(v)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("collaboration_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    collaboration_id: Mapped[int] = mapped_column(ForeignKey("collaborations.id"))
    company_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    text: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="published")  # published|hidden
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    company: Mapped[Organization] = relationship()


class Report(Base):
    """Signalement ou contestation : kind = evaluation|recommendation|offer|profile."""
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)
    target_id: Mapped[int] = mapped_column(Integer)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)  # open|resolved|dismissed
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    reporter: Mapped[User] = relationship()


# ---------------------------------------------------------------- abonnements et paiements
class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    price_xof: Mapped[int] = mapped_column(Integer, default=0)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    max_active_offers: Mapped[int | None] = mapped_column(Integer, nullable=True)       # None = illimité
    profile_views_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = illimité
    can_search: Mapped[bool] = mapped_column(Boolean, default=False)
    can_advanced_filters: Mapped[bool] = mapped_column(Boolean, default=False)
    can_see_matching: Mapped[bool] = mapped_column(Boolean, default=False)
    can_see_contacts: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending_payment", index=True)  # pending_payment|active|expired|cancelled|replaced
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    months: Mapped[int] = mapped_column(Integer, default=1)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)  # indicateur : aucun prélèvement automatique n'est implémenté
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    org: Mapped[Organization] = relationship()
    plan: Mapped[Plan] = relationship()


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30), default="", index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))
    description: Mapped[str] = mapped_column(String(300), default="")
    amount_xof: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="unpaid")  # unpaid|paid|void
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    org: Mapped[Organization] = relationship()
    subscription: Mapped[Subscription] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="demo")
    mode: Mapped[str] = mapped_column(String(10), default="demo")  # demo|live
    reference: Mapped[str] = mapped_column(String(80), unique=True)
    amount_xof: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(5), default="XOF")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|succeeded|failed|refunded
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    invoice: Mapped[Invoice] = relationship()
    org: Mapped[Organization] = relationship()


class ProfileView(Base):
    """Une entreprise consulte un profil complet : compté une seule fois par mois et par profil."""
    __tablename__ = "profile_views"
    __table_args__ = (UniqueConstraint("company_id", "graduate_id", "month"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    graduate_id: Mapped[int] = mapped_column(ForeignKey("graduate_profiles.id"), index=True)
    month: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


# ---------------------------------------------------------------- transverse
class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(String(500))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
