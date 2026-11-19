"""Téléversement sécurisé des CV : extension, taille, signature réelle du fichier, nom aléatoire, stockage hors dossier public."""
import secrets
from pathlib import Path
from fastapi import HTTPException, UploadFile
from .config import settings

ALLOWED = {".pdf": b"%PDF", ".docx": b"PK\x03\x04"}
MIME = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
PHOTO_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


async def read_limited(file: UploadFile, max_mb: int | None = None) -> bytes:
    limit = (max_mb or settings.max_upload_mb) * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"Fichier trop volumineux (maximum {max_mb or settings.max_upload_mb} Mo)")
    if not data:
        raise HTTPException(422, "Fichier vide")
    return data


def save_cv(filename: str, data: bytes) -> tuple[str, str]:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED or not data.startswith(ALLOWED[ext]):
        raise HTTPException(422, "Format refusé : seuls les fichiers PDF et DOCX valides sont acceptés")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored = secrets.token_hex(16) + ext
    (settings.upload_dir / stored).write_bytes(data)
    safe = "".join(c for c in Path(filename).stem if c.isalnum() or c in "-_ ")[:60].strip() or "cv"
    return stored, safe + ext


def cv_path(stored: str) -> Path:
    p = (settings.upload_dir / stored).resolve()
    if settings.upload_dir.resolve() not in p.parents or not p.exists():  # anti « path traversal »
        raise HTTPException(404, "Document introuvable")
    return p


def delete_cv(stored: str):
    try:
        if stored:
            cv_path(stored).unlink(missing_ok=True)
    except HTTPException:
        pass


def save_photo(filename: str, data: bytes) -> tuple[str, str]:
    """Valide et stocke une photo de profil hors du dossier public."""
    ext = Path(filename or "").suffix.lower()
    signatures = {".jpg": (b"\xff\xd8\xff",), ".jpeg": (b"\xff\xd8\xff",), ".png": (b"\x89PNG\r\n\x1a\n",), ".webp": (b"RIFF",)}
    if ext not in PHOTO_MIME or not any(data.startswith(sig) for sig in signatures[ext]):
        raise HTTPException(422, "Format refusé : utilisez une image JPG, PNG ou WEBP valide")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored = "photo-" + secrets.token_hex(16) + ext
    (settings.upload_dir / stored).write_bytes(data)
    safe = "".join(c for c in Path(filename).stem if c.isalnum() or c in "-_ ")[:60].strip() or "photo"
    return stored, safe + ext


def photo_path(stored: str) -> Path:
    p = (settings.upload_dir / stored).resolve()
    if settings.upload_dir.resolve() not in p.parents or not p.exists() or not p.name.startswith("photo-"):
        raise HTTPException(404, "Photo introuvable")
    return p


def delete_photo(stored: str):
    try:
        if stored:
            photo_path(stored).unlink(missing_ok=True)
    except HTTPException:
        pass
