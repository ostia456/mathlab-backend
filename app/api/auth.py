"""
Authentication API Routes - FastAPI
"""
import os
import resend
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app import SessionLocal
from app.models.user import User

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# Token blacklist for logout
blacklist = set()

# OAuth2 scheme for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# ─────────────────────────────────────────────────────────────────────────────
# Stockage temporaire des codes de vérification
# ─────────────────────────────────────────────────────────────────────────────
_pending_verifications: dict = {}
CODE_EXPIRY_MINUTES = 15
MAX_ATTEMPTS = 5

# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic (validation automatique)
# ─────────────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    role: str = Field(default="student")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None

# ─────────────────────────────────────────────────────────────────────────────
# Dépendance DB
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────────────────────
# Dépendance JWT (utilisateur courant)
# ─────────────────────────────────────────────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Récupère l'utilisateur à partir du token JWT."""
    if not token:
        raise HTTPException(status_code=401, detail="Token manquant")
    
    # Vérifie blacklist
    try:
        payload = jwt.decode(token, os.getenv('JWT_SECRET_KEY', 'jwt-secret'), algorithms=['HS256'])
        jti = payload.get('jti')
        if jti and jti in blacklist:
            raise HTTPException(status_code=401, detail="Token révoqué")
        
        user_id = int(payload.get('sub'))
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalide")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
    return user

def get_current_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Vérifie que l'utilisateur est un enseignant/admin."""
    if not current_user.is_teacher():
        raise HTTPException(status_code=403, detail="Accès réservé aux enseignants")
    return current_user

# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires email (inchangés)
# ─────────────────────────────────────────────────────────────────────────────
def _generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))

def _store_code(email: str, code: str):
    _pending_verifications[email] = {
        'code': code,
        'expires_at': datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES),
        'attempts': 0,
    }

def _validate_code(email: str, code: str) -> tuple:
    """Retourne (success: bool, error_message: str)"""
    record = _pending_verifications.get(email)
    if not record:
        return False, "Aucun code en attente pour cet email. Recommencez l'inscription."
    if datetime.now(timezone.utc) > record['expires_at']:
        _pending_verifications.pop(email, None)
        return False, "Le code a expiré. Cliquez sur « Renvoyer le code »."
    record['attempts'] += 1
    if record['attempts'] > MAX_ATTEMPTS:
        _pending_verifications.pop(email, None)
        return False, "Trop de tentatives. Recommencez l'inscription."
    if record['code'] != code:
        remaining = MAX_ATTEMPTS - record['attempts']
        return False, f"Code incorrect. {remaining} tentative(s) restante(s)."
    _pending_verifications.pop(email, None)
    return True, ""

def _send_verification_email(to_email: str, first_name: str, code: str):
    """Envoie le code par email via Resend API."""
    resend_api_key = os.getenv('RESEND_API_KEY', '')

    if not resend_api_key:
        # Mode développement : affiche le code dans la console
        print(f"\n{'='*40}")
        print(f"[DEV] Code de vérification pour {to_email} : {code}")
        print(f"{'='*40}\n")
        return

    resend.api_key = resend_api_key

    subject = "MathLab University — Vérification de votre adresse email"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
      <div style="text-align: center; margin-bottom: 32px;">
        <h1 style="color: #1a1a2e; font-size: 24px; margin: 0;">MathLab University</h1>
        <p style="color: #666; font-size: 14px; margin-top: 4px;">
          Département de Mathématiques-Informatique — UNSTIM
        </p>
      </div>

      <div style="background: #f8f9ff; border-radius: 12px; padding: 32px; text-align: center;">
        <p style="color: #333; font-size: 16px;">Bonjour <strong>{first_name}</strong>,</p>
        <p style="color: #555; font-size: 14px; line-height: 1.6;">
          Merci de vous être inscrit sur MathLab University.<br/>
          Voici votre code de vérification :
        </p>

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
        margin-top: 24px; padding: 16px;
        background: #fff3cd; border-radius: 8px;
        border-left: 4px solid #ffc107;
      ">
        <p style="color: #856404; font-size: 13px; margin: 0;">
          ⚠️ Si vous n'êtes pas à l'origine de cette inscription, ignorez cet email.
        </p>
      </div>

      <p style="color: #aaa; font-size: 12px; text-align: center; margin-top: 32px;">
        © MathLab University — UNSTIM
      </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": "MathLab University <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        })
        print(f"[INFO] Email envoyé à {to_email}")
    except Exception as e:
        print(f"[WARN] Email send failed: {e}")
        print(f"[DEV] Code de vérification pour {to_email} : {code}")

# ─────────────────────────────────────────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and send verification email"""
    email = data.email.lower()
    
    existing = db.query(User).filter_by(email=email).first()
    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=409, detail="Email déjà utilisé")
        code = _generate_code()
        _store_code(email, code)
        try:
            _send_verification_email(email, existing.first_name, code)
        except Exception as e:
            print(f"[WARN] Email send failed: {e}")
        return {"message": "Code de vérification renvoyé. Vérifiez votre boîte mail.", "email": email}
    
    user = User(
        email=email,
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        is_verified=False,
    )
    user.set_password(data.password)
    db.add(user)
    db.commit()
    
    code = _generate_code()
    _store_code(email, code)
    try:
        _send_verification_email(email, user.first_name, code)
    except Exception as e:
        print(f"[WARN] Email send failed: {e}")
    
    return {"message": "Compte créé. Vérifiez votre boîte mail pour le code.", "email": email}

# ─────────────────────────────────────────────────────────────────────────────
# VERIFY EMAIL
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with 6-digit code"""
    email = data.email.lower()
    code = data.code.strip()
    
    ok, error_msg = _validate_code(email, code)
    if not ok:
        raise HTTPException(status_code=400, detail=error_msg)
    
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    
    user.is_verified = True
    db.commit()
    
    return {"message": "Email vérifié avec succès. Vous pouvez vous connecter."}

# ─────────────────────────────────────────────────────────────────────────────
# RESEND CODE
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/resend-verification")
def resend_verification(data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification code"""
    email = data.email.lower()
    
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email introuvable")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Ce compte est déjà vérifié")
    
    existing = _pending_verifications.get(email)
    if existing:
        elapsed = (datetime.now(timezone.utc) - (existing['expires_at'] - timedelta(minutes=CODE_EXPIRY_MINUTES))).total_seconds()
        if elapsed < 60:
            wait = int(60 - elapsed)
            raise HTTPException(status_code=429, detail=f"Veuillez patienter {wait} secondes.")
    
    code = _generate_code()
    _store_code(email, code)
    try:
        _send_verification_email(email, user.first_name, code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Échec de l'envoi : {str(e)}")
    
    return {"message": "Code de vérification renvoyé."}

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Login user"""
    email = data.email.lower()
    user = db.query(User).filter_by(email=email).first()
    
    if not user or not user.check_password(data.password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Veuillez vérifier votre email avant de vous connecter."
        )
    
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    access_token = jwt.encode(
        {
            'sub': str(user.id),
            'iat': datetime.now(timezone.utc),
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        },
        os.getenv('JWT_SECRET_KEY', 'jwt-secret'),
        algorithm='HS256'
    )
    
    return {
        'message': 'Connexion réussie',
        'user': user.to_dict(),
        'access_token': access_token
    }

# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout (invalidate token)"""
    # FastAPI ne donne pas accès direct au jti via Depends.
    # Solution : le frontend supprime le token localement.
    # Le token expirera naturellement (24h).
    return {"message": "Déconnexion réussie"}

# ─────────────────────────────────────────────────────────────────────────────
# ME
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {"user": current_user.to_dict()}

# ─────────────────────────────────────────────────────────────────────────────
# UPDATE PROFILE
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/profile")
def update_profile(data: UpdateProfileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update user profile"""
    if data.first_name is not None:
        current_user.first_name = data.first_name
    if data.last_name is not None:
        current_user.last_name = data.last_name
    if data.password is not None:
        current_user.set_password(data.password)
    
    db.commit()
    return {"message": "Profil mis à jour", "user": current_user.to_dict()}

# ─────────────────────────────────────────────────────────────────────────────
# LIST USERS (teacher/admin only)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """List all users (teacher/admin only)"""
    users = db.query(User).all()
    return {"users": [u.to_dict() for u in users]}