"""
FriScan — Application principale FastAPI
Point d'entrée du serveur backend.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from server.database import init_db
from server.routers import products, scanner, recipes, fresh_products


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base de données au démarrage."""
    init_db()
    print("✅ FriScan — Base de données initialisée")
    print("🌐 Interface disponible sur http://localhost:8000")
    yield
    print("👋 FriScan — Arrêt du serveur")


app = FastAPI(
    title="FriScan",
    description="Gestionnaire intelligent de frigo avec scanner de codes-barres et suggestions de recettes",
    version="1.0.0",
    lifespan=lifespan,
)

# Enregistrement des routers API
app.include_router(products.router)
app.include_router(scanner.router)
app.include_router(recipes.router)
app.include_router(fresh_products.router)

# Servir les fichiers statiques (frontend)
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Sert la page d'accueil."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health_check():
    """Vérification de santé du serveur."""
    return {"status": "ok", "service": "FriScan"}
