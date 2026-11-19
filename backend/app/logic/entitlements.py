"""Droits liés aux abonnements (fonctions pures ; l'application serveur les appelle à chaque action)."""
from __future__ import annotations
from datetime import date, datetime


def month_key(d: date | datetime | None = None) -> str:
    d = d or date.today()
    return f"{d.year:04d}-{d.month:02d}"


def subscription_is_current(status: str, start: date | None, end: date | None, today: date | None = None) -> bool:
    today = today or date.today()
    return status == "active" and start is not None and end is not None and start <= today <= end


def quota_left(limit: int | None, used: int) -> int | None:
    """None = illimité ; sinon nombre d'unités restantes (jamais négatif)."""
    return None if limit is None else max(0, limit - used)


def quota_allows(limit: int | None, used: int) -> bool:
    return limit is None or used < limit


def extend_end(current_end: date | None, today: date, days: int) -> date:
    """Renouvellement : la nouvelle période commence à la fin de la période en cours si elle n'est pas échue."""
    from datetime import timedelta
    base = current_end if current_end and current_end >= today else today
    return base + timedelta(days=days)
