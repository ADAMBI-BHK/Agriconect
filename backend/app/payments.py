"""Passerelles de paiement.

Seul le mode DÉMONSTRATION est implémenté : il n'encaisse aucun argent et toute interface l'indique.
Pour un paiement réel (FedaPay, KkiaPay, CinetPay, PayDunya…), implémentez une classe qui respecte PaymentProvider,
enregistrez-la dans PROVIDERS, renseignez PAYMENT_MODE=live, PAYMENT_PROVIDER et les clés (voir README, section « Paiements »).
Aucune API externe n'est appelée par ce code : il n'a donc JAMAIS été éprouvé contre une vraie passerelle.
"""
import secrets
from .config import settings


class NotConfigured(Exception):
    pass


class PaymentProvider:
    name = "base"
    live = False

    def create_checkout(self, reference: str, amount_xof: int, description: str) -> dict:
        raise NotImplementedError

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        raise NotImplementedError


class DemoProvider(PaymentProvider):
    name = "demo"

    def create_checkout(self, reference, amount_xof, description):
        return {"mode": "demo", "reference": reference,
                "message": "Le règlement est en attente de confirmation. La passerelle de paiement sera connectée selon les modalités retenues."}


PROVIDERS: dict[str, type[PaymentProvider]] = {"demo": DemoProvider}


def get_provider() -> PaymentProvider:
    if settings.payment_mode != "live":
        return DemoProvider()
    cls = PROVIDERS.get(settings.payment_provider)
    if cls is None or not settings.payment_api_key:
        raise NotConfigured("Paiement réel non configuré : passerelle non implémentée ou clé API absente (voir README).")
    return cls()


def new_reference() -> str:
    return "ACPAY-" + secrets.token_hex(6).upper()
