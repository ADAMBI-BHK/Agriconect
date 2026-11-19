from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db import get_db
from .config import settings
from .models import Plan, Subscription, Invoice, Payment, Organization, User, now
from .schemas import SubscribeIn
from .deps import company_ok, notify, audit
from .services import entitlements, plan_out, activate_subscription
from .payments import get_provider, new_reference, NotConfigured

router = APIRouter(prefix="/api", tags=["billing"])


def invoice_out(i: Invoice) -> dict:
    return {"id": i.id, "number": i.number, "description": i.description, "amount_xof": i.amount_xof, "status": i.status,
            "issued_at": i.issued_at.isoformat(), "paid_at": i.paid_at.isoformat() if i.paid_at else None,
            "org": {"name": i.org.name, "registration_no": i.org.registration_no, "city": i.org.city},
            "demo": settings.payment_mode != "live"}


def payment_out(p: Payment) -> dict:
    return {"id": p.id, "reference": p.reference, "provider": p.provider, "mode": p.mode, "amount_xof": p.amount_xof, "currency": p.currency,
            "status": p.status, "created_at": p.created_at.isoformat(), "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "invoice_number": p.invoice.number}


def sub_out(s: Subscription) -> dict:
    return {"id": s.id, "plan": s.plan.name, "plan_code": s.plan.code, "status": s.status, "months": s.months,
            "start_date": s.start_date.isoformat() if s.start_date else None, "end_date": s.end_date.isoformat() if s.end_date else None,
            "auto_renew": s.auto_renew, "created_at": s.created_at.isoformat()}


@router.get("/plans")
def plans(db: Session = Depends(get_db)):
    rows = db.scalars(select(Plan).where(Plan.active).order_by(Plan.sort, Plan.id)).all()
    return {"plans": [plan_out(p) for p in rows], "currency": "XOF", "payment_mode": settings.payment_mode,
            "note": "Les modalités d'accès sont configurables par l'administration."}


@router.get("/billing/overview")
def overview(o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    subs = db.scalars(select(Subscription).where(Subscription.org_id == o.id).order_by(Subscription.id.desc())).all()
    invs = db.scalars(select(Invoice).where(Invoice.org_id == o.id).order_by(Invoice.id.desc())).all()
    pays = db.scalars(select(Payment).where(Payment.org_id == o.id).order_by(Payment.id.desc())).all()
    return {"entitlements": entitlements(db, o), "subscriptions": [sub_out(s) for s in subs], "invoices": [invoice_out(i) for i in invs],
            "payments": [payment_out(p) for p in pays], "payment_mode": settings.payment_mode}


@router.post("/billing/subscribe", status_code=201)
def subscribe(data: SubscribeIn, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    plan = db.scalar(select(Plan).where(Plan.code == data.plan_code, Plan.active))
    if not plan:
        raise HTTPException(404, "Formule introuvable")
    try:
        provider = get_provider()
    except NotConfigured as e:
        raise HTTPException(501, str(e))
    amount = plan.price_xof
    sub = Subscription(org_id=o.id, plan_id=plan.id, status="pending_payment", months=12, auto_renew=data.auto_renew)
    db.add(sub); db.flush()
    demo = settings.payment_mode != "live"
    inv = Invoice(org_id=o.id, subscription_id=sub.id, amount_xof=amount, status="unpaid",
                  description=f"Accès annuel {plan.name} — première année")
    db.add(inv); db.flush()
    inv.number = f"AC-{now().year}-{inv.id:05d}"
    pay = Payment(invoice_id=inv.id, org_id=o.id, provider=provider.name, mode="demo" if demo else "live", reference=new_reference(),
                  amount_xof=amount, status="pending")
    db.add(pay); db.flush()
    checkout = provider.create_checkout(pay.reference, amount, inv.description)
    audit(db, o.owner_id, "subscribe_requested", f"{plan.code} x{data.months} ({pay.reference})")
    db.commit()
    return {"subscription": sub_out(sub), "invoice": invoice_out(inv), "payment": payment_out(pay), "checkout": checkout}


def settle(db: Session, pay: Payment, by: int | None, provider: str | None = None):
    """Marque un paiement comme réglé, la facture comme payée, et active l'abonnement."""
    pay.status, pay.paid_at = "succeeded", now()
    if provider:
        pay.provider = provider
    pay.invoice.status, pay.invoice.paid_at = "paid", now()
    activate_subscription(db, pay.invoice.subscription)
    notify(db, pay.org.owner_id, f"Paiement confirmé ({pay.reference}) : abonnement {pay.invoice.subscription.plan.name} actif jusqu'au {pay.invoice.subscription.end_date}.")
    audit(db, by, "payment_settled", f"{pay.reference} mode={pay.mode}")


@router.post("/billing/payments/{reference}/confirm-demo")
def confirm_demo(reference: str, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    """Simulation de règlement. Désactivée dès que PAYMENT_MODE=live : on ne peut jamais « s'offrir » un abonnement en production."""
    if settings.payment_mode == "live":
        raise HTTPException(403, "La confirmation de règlement n'est pas disponible pour ce mode")
    pay = db.scalar(select(Payment).where(Payment.reference == reference, Payment.org_id == o.id))
    if not pay:
        raise HTTPException(404, "Paiement introuvable")
    if pay.status != "pending":
        raise HTTPException(409, "Ce paiement n'est plus en attente")
    settle(db, pay, o.owner_id)
    db.commit()
    return {"payment": payment_out(pay), "entitlements": entitlements(db, o)}


@router.post("/billing/payments/{reference}/cancel")
def cancel_payment(reference: str, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    pay = db.scalar(select(Payment).where(Payment.reference == reference, Payment.org_id == o.id))
    if not pay or pay.status != "pending":
        raise HTTPException(404, "Paiement en attente introuvable")
    pay.status = "failed"; pay.invoice.status = "void"; pay.invoice.subscription.status = "cancelled"
    db.commit()
    return {"ok": True}


@router.post("/billing/auto-renew/{flag}")
def auto_renew(flag: bool, o: Organization = Depends(company_ok), db: Session = Depends(get_db)):
    """Simple indicateur : aucun prélèvement automatique n'existe. Un rappel est envoyé avant l'échéance (non implémenté : voir README)."""
    sub = db.scalar(select(Subscription).where(Subscription.org_id == o.id, Subscription.status == "active").order_by(Subscription.end_date.desc()))
    if not sub:
        raise HTTPException(404, "Aucun abonnement actif")
    sub.auto_renew = flag; db.commit()
    return {"auto_renew": flag}


@router.post("/billing/webhook")
async def webhook(request: Request):
    """Point d'entrée des notifications d'une passerelle réelle. Non implémenté tant qu'aucune passerelle n'est configurée."""
    raise HTTPException(501, "Aucune passerelle de paiement réelle n'est configurée (voir README, section Paiements).")
