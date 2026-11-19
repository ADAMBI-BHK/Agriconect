from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import SessionLocal, Base, engine
from . import models  # noqa: F401  (enregistre les tables)
from .seed import seed_reference, ensure_admin, seed_demo
from . import (routes_auth, routes_graduate, routes_company, routes_institution, routes_admin, routes_billing, routes_misc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Le schéma est créé par les migrations Alembic (« python -m app.cli init-db »). Pour une installation SQLite locale
    # sans migration préalable, on crée les tables manquantes : sans effet si elles existent déjà.
    Base.metadata.create_all(engine)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        seed_reference(db)
        ensure_admin(db)
        if settings.seed_demo:
            seed_demo(db)
    yield


app = FastAPI(title="AgriConnect API", version="1.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-Requested-With"])


@app.middleware("http")
async def security(request: Request, call_next):
    # Protection CSRF : toute écriture doit porter l'en-tête personnalisé (les formulaires inter-sites ne peuvent pas l'envoyer).
    # Les envois de fichiers (multipart) sont inclus : le frontend ajoute l'en-tête à tous ses appels.
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.headers.get("x-requested-with") != "agriconnect":
        return JSONResponse({"detail": "En-tête de sécurité manquant"}, status_code=403)
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("Cache-Control", "no-store")
    return resp


for r in (routes_auth.router, routes_graduate.pub, routes_graduate.router, routes_company.router, routes_institution.router,
          routes_admin.router, routes_billing.router, routes_misc.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}
