import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError

# ------------------------------
# 1. Configuration de base
# ------------------------------
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///mathlab.db')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000')
origins_list = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]

# ------------------------------
# 2. Base de données (SQLAlchemy pur)
# ------------------------------
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ------------------------------
# 3. Gestion du cycle de vie
# ------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    yield
    # À l'arrêt
    pass

# ------------------------------
# 4. Application FastAPI
# ------------------------------
app = FastAPI(
    title="MathLab University API",
    description="Plateforme pédagogique de mathématiques appliquées",
    version="2.0.0",
    lifespan=lifespan
)

# ------------------------------
# 5. Middleware CORS
# ------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["Content-Range", "X-Content-Range"],
)

# ------------------------------
# 6. Inclusion des routeurs
# ------------------------------
from app.api.auth import router as auth_router, blacklist
from app.api.dashboard import router as dashboard_router
from app.api.dynamical_systems import router as ds_router
from app.api.exercises import router as ex_router
from app.api.graph_theory import router as gt_router
from app.api.linear_algebra import router as la_router
from app.api.numerical_methods import router as nm_router
from app.api.scenarios import router as sc_router

app.include_router(auth_router, prefix="/api/auth", tags=["Authentification"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(ds_router, prefix="/api/dynamical-systems", tags=["Systèmes Dynamiques"])
app.include_router(ex_router, prefix="/api/exercises", tags=["Exercices"])
app.include_router(gt_router, prefix="/api/graph-theory", tags=["Théorie des Graphes"])
app.include_router(la_router, prefix="/api/linear-algebra", tags=["Algèbre Linéaire"])
app.include_router(nm_router, prefix="/api/numerical-methods", tags=["Méthodes Numériques"])
app.include_router(sc_router, prefix="/api/scenarios", tags=["Scénarios"])

# ------------------------------
# 7. Routes de base
# ------------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "MathLab API is running"}

# ------------------------------
# 8. Dépendance de session DB
# ------------------------------
def get_db():
    """Utilitaire pour injecter la session DB dans les routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()