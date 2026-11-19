import base64, hashlib, hmac, os, re, secrets, time
from .config import settings


def hash_password(p: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(p.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(p: str, stored: str) -> bool:
    try:
        _, s, h = stored.split("$")
        c = hashlib.scrypt(p.encode(), salt=bytes.fromhex(s), n=2**14, r=8, p=1)
        return hmac.compare_digest(c.hex(), h)
    except Exception:
        return False


def password_problem(p: str) -> str | None:
    """Retourne un message d'erreur si le mot de passe est trop faible, sinon None."""
    if len(p) < 8:
        return "Le mot de passe doit contenir au moins 8 caractères"
    if len(p) > 128:
        return "Le mot de passe est trop long (128 caractères maximum)"
    if not re.search(r"[A-Za-z]", p) or not re.search(r"\d", p):
        return "Le mot de passe doit contenir au moins une lettre et un chiffre"
    return None


def _sig(body: str) -> str:
    return hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()


def make_token(uid: int, ver: int = 0) -> str:
    body = f"{uid}:{int(time.time()) + settings.session_hours * 3600}:{ver}"
    return base64.urlsafe_b64encode(f"{body}:{_sig(body)}".encode()).decode()


def read_token(token: str) -> tuple[int, int] | None:
    """Retourne (id utilisateur, version de session) si le jeton est valide et non expiré."""
    try:
        uid, exp, ver, sig = base64.urlsafe_b64decode(token.encode()).decode().split(":")
        if hmac.compare_digest(sig, _sig(f"{uid}:{exp}:{ver}")) and int(exp) > time.time():
            return int(uid), int(ver)
    except Exception:
        pass
    return None


def new_activation_token() -> tuple[str, str]:
    """(jeton en clair à transmettre, empreinte SHA-256 à stocker). Le clair n'est jamais stocké."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def new_reset_token() -> tuple[str, str]:
    """Génère un jeton de récupération : seul son hash est conservé en base."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
