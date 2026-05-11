# email_verification.py
# À intégrer dans ton backend FastAPI existant
#
# Dépendances à installer :
#   pip install python-jose[cryptography] passlib[bcrypt] python-multipart
#   (déjà installées si tu as un backend FastAPI d'auth standard)
#
# Variables d'environnement à ajouter dans ton .env :
#   GMAIL_SENDER=ton.email@gmail.com
#   GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   ← App Password Gmail (voir SETUP.md)

import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
import os

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

# ── Adapte ces imports à ta structure existante ──────────────────────────────
# from .database import get_db
# from .models import User
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/auth", tags=["auth"])

# ─────────────────────────────────────────────────────────────────────────────
# Configuration Gmail
# ─────────────────────────────────────────────────────────────────────────────
GMAIL_SENDER       = os.getenv("GMAIL_SENDER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
SMTP_HOST          = "smtp.gmail.com"
SMTP_PORT          = 587

# ─────────────────────────────────────────────────────────────────────────────
# Stockage temporaire des codes (en mémoire)
# En production : utilise Redis ou une table DB dédiée
# Structure : { email: { code, expires_at, attempts } }
# ─────────────────────────────────────────────────────────────────────────────
_pending_verifications: dict[str, dict] = {}

CODE_EXPIRY_MINUTES = 15   # Le code expire après 15 min
MAX_ATTEMPTS        = 5    # Nombre max de tentatives avant invalidation


# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    first_name: str
    last_name:  str
    email:      EmailStr
    password:   str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code:  str

class ResendCodeRequest(BaseModel):
    email: EmailStr


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────────────
def _generate_code(length: int = 6) -> str:
    """Génère un code numérique aléatoire à 6 chiffres."""
    return ''.join(random.choices(string.digits, k=length))


def _send_verification_email(to_email: str, first_name: str, code: str) -> None:
    """Envoie l'email de vérification via SMTP Gmail."""
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        # Mode développement : affiche le code dans la console
        print(f"\n{'='*40}")
        print(f"[DEV] Code de vérification pour {to_email} : {code}")
        print(f"{'='*40}\n")
        return

    subject = "MathLab University — Vérification de votre adresse email"

    # Corps HTML de l'email
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <h1 style="color: #1a1a2e; font-size: 24px; margin: 0;">MathLab University</h1>
        <p style="color: #666; font-size: 14px; margin-top: 4px;">
          Département de Mathématiques-Informatique
        </p>
      </div>

      <div style="background: #f8f9ff; border-radius: 12px; padding: 32px; text-align: center;">
        <p style="color: #333; font-size: 16px;">Bonjour <strong>{first_name}</strong>,</p>
        <p style="color: #555; font-size: 14px; line-height: 1.6;">
          Merci de vous être inscrit sur MathLab University.<br/>
          Voici votre code de vérification :
        </p>

        <!-- Code principal -->
        <div style="
          display: inline-block;
          background: #ffffff;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          padding: 16px 32px;
          margin: 20px 0;
        ">
          <span style="
            font-family: 'Courier New', monospace;
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 12px;
            color: #1a1a2e;
          ">{code}</span>
        </div>

        <p style="color: #888; font-size: 13px;">
          Ce code est valable <strong>{CODE_EXPIRY_MINUTES} minutes</strong>.
        </p>
      </div>

      <div style="
        margin-top: 24px;
        padding: 16px;
        background: #fff3cd;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
      ">
        <p style="color: #856404; font-size: 13px; margin: 0;">
          ⚠️ Si vous n'êtes pas à l'origine de cette inscription, ignorez cet email.
          Votre adresse ne sera pas utilisée.
        </p>
      </div>

      <p style="
        color: #aaa;
        font-size: 12px;
        text-align: center;
        margin-top: 32px;
      ">
        © MathLab University — UNSTIM
      </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MathLab University <{GMAIL_SENDER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_SENDER, to_email, msg.as_string())


def _store_code(email: str, code: str) -> None:
    """Stocke le code avec son expiration."""
    _pending_verifications[email] = {
        "code":       code,
        "expires_at": datetime.utcnow() + timedelta(minutes=CODE_EXPIRY_MINUTES),
        "attempts":   0,
    }


def _validate_code(email: str, code: str) -> tuple[bool, str]:
    """
    Valide le code soumis.
    Retourne (success: bool, error_message: str)
    """
    record = _pending_verifications.get(email)

    if not record:
        return False, "Aucun code en attente pour cet email. Recommencez l'inscription."

    if datetime.utcnow() > record["expires_at"]:
        _pending_verifications.pop(email, None)
        return False, f"Le code a expiré. Cliquez sur « Renvoyer le code »."

    record["attempts"] += 1

    if record["attempts"] > MAX_ATTEMPTS:
        _pending_verifications.pop(email, None)
        return False, "Trop de tentatives. Recommencez l'inscription."

    if record["code"] != code:
        remaining = MAX_ATTEMPTS - record["attempts"]
        return False, f"Code incorrect. {remaining} tentative(s) restante(s)."

    # ✅ Code valide → on le supprime pour éviter la réutilisation
    _pending_verifications.pop(email, None)
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/register")
async def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),   # ← adapte à ton injection de dépendance
):
    """
    Étape 1 : Crée le compte en statut non vérifié et envoie le code par email.
    Le compte ne peut pas se connecter tant que is_verified = False.
    """
    # Vérifie si l'email est déjà pris
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing and existing.is_verified:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")
    if existing and not existing.is_verified:
        # Compte non vérifié existant → on renvoie juste un nouveau code
        pass
    else:
        # Crée le compte (adapte selon ton modèle User)
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        new_user = User(
            first_name  = payload.first_name,
            last_name   = payload.last_name,
            email       = payload.email,
            hashed_password = pwd_context.hash(payload.password),
            is_verified = False,   # ← champ à ajouter dans ton modèle User
        )
        db.add(new_user)
        db.commit()

    # Génère et envoie le code
    code = _generate_code()
    _store_code(payload.email, code)

    try:
        _send_verification_email(payload.email, payload.first_name, code)
    except Exception as e:
        print(f"[WARN] Échec envoi email : {e}")
        # On ne bloque pas l'inscription si l'email échoue en dev
        # En production, tu peux lever une HTTPException ici

    return {
        "message": "Compte créé. Vérifiez votre email.",
        "email":   payload.email,
    }


@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """
    Étape 2 : Vérifie le code à 6 chiffres et active le compte.
    """
    ok, error_msg = _validate_code(payload.email, payload.code.strip())

    if not ok:
        raise HTTPException(status_code=400, detail=error_msg)

    # Active le compte
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    user.is_verified = True
    db.commit()

    return {"message": "Email vérifié avec succès. Vous pouvez vous connecter."}


@router.post("/resend-verification")
async def resend_verification(
    payload: ResendCodeRequest,
    db: Session = Depends(get_db),
):
    """
    Renvoie un nouveau code de vérification (avec délai anti-spam de 60s).
    """
    # Vérifie qu'il n'y a pas de code récent (anti-spam)
    existing = _pending_verifications.get(payload.email)
    if existing:
        elapsed = (existing["expires_at"] - timedelta(minutes=CODE_EXPIRY_MINUTES))
        seconds_since = (datetime.utcnow() - elapsed).total_seconds()
        if seconds_since < 60:
            wait = int(60 - seconds_since)
            raise HTTPException(
                status_code=429,
                detail=f"Veuillez attendre {wait} secondes avant de renvoyer."
            )

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email introuvable.")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Ce compte est déjà vérifié.")

    code = _generate_code()
    _store_code(payload.email, code)

    try:
        _send_verification_email(payload.email, user.first_name, code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec d'envoi email : {e}")

    return {"message": "Nouveau code envoyé."}


# ─────────────────────────────────────────────────────────────────────────────
# Migration du modèle User
# ─────────────────────────────────────────────────────────────────────────────
#
# Ajoute ce champ à ton modèle SQLAlchemy User :
#
#   is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
#
# Et dans ton endpoint /login, bloque les comptes non vérifiés :
#
#   if not user.is_verified:
#       raise HTTPException(
#           status_code=403,
#           detail="Veuillez vérifier votre email avant de vous connecter."
#       )
#
# ─────────────────────────────────────────────────────────────────────────────
