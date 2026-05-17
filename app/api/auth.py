"""
Authentication API Routes - FastAPI
"""
import os
import requests
import random
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import secrets as secrets_module
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
# Stockage temporaire des tokens de réinitialisation
_reset_tokens: dict = {}
RESET_TOKEN_EXPIRY_MINUTES = 30
# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic (validation automatique)
# ─────────────────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    role: str = Field(default="student")
    country: str = Field(default='')

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
    """Envoie par SendGrid avec template optimisé anti-spam."""
    api_key = os.getenv('SENDGRID_API_KEY', '')

    if not api_key:
        print(f"\n{'='*40}")
        print(f"[DEV] Code de vérification pour {to_email} : {code}")
        print(f"{'='*40}\n")
        return

    # Lien de vérification direct
    verify_link = f"https://mathlab-backend.onrender.com/api/auth/verify-email/{to_email}-{code}"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <body style="font-family: Arial, Helvetica, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #333333; background-color: #ffffff;">

      <!-- En-tête -->
      <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2563eb; font-size: 22px; margin: 0;">MathLab University</h1>
        <p style="color: #666666; font-size: 13px; margin: 4px 0 0 0;">
          Département de Mathématiques-Informatique — UNSTIM
        </p>
      </div>

      <hr style="border: none; border-top: 1px solid #eeeeee; margin: 20px 0;">

      <!-- Corps -->
      <p style="font-size: 15px;">Bonjour <strong>{first_name}</strong>,</p>

      <p style="font-size: 15px;">
        Merci d'avoir créé un compte sur <strong>MathLab University</strong>.
        Pour activer votre compte, cliquez sur le bouton.
      </p>

      <!-- Bouton -->
      <div style="text-align: center; margin: 25px 0;">
        <a href="{verify_link}" style="background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 14px 35px; border-radius: 8px; font-size: 16px; font-weight: bold; display: inline-block;">
        Activer mon compte
        </a>
      </div>

      <p style="font-size: 13px; color: #888888;">
        Si vous n'avez pas créé de compte sur MathLab University, ignorez simplement cet email.
      </p>

      <hr style="border: none; border-top: 1px solid #eeeeee; margin: 30px 0 20px 0;">

      <!-- Pied de page conforme -->
      <div style="text-align: center;">
        <p style="font-size: 11px; color: #aaaaaa; margin: 0 0 4px 0;">
          MathLab University — UNSTIM, Bénin
        </p>
        <p style="font-size: 11px; color: #aaaaaa; margin: 0 0 4px 0;">
          <a href="mailto:mathlabuniversity@gmail.com" style="color: #aaaaaa;">mathlabuniversity@gmail.com</a>
        </p>
        <p style="font-size: 11px; color: #aaaaaa; margin: 0;">
          Vous recevez cet email car vous avez créé un compte sur MathLab University.
          <a href="https://mathlabuniversity.vercel.app/unsubscribe" style="color: #aaaaaa;">Se désabonner</a>
        </p>
      </div>

    </body>
    </html>
    """

    # Version texte (obligatoire pour anti-spam)
    text_body = f"""
MathLab University — UNSTIM, Bénin

Bonjour {first_name},

Merci d'avoir créé un compte sur MathLab University.

Votre code de vérification : {code}
Valable 15 minutes.

Ou activez votre compte en cliquant sur ce lien :
{verify_link}

Si vous n'avez pas créé de compte, ignorez cet email.

MathLab University · UNSTIM, Bénin
mathlabuniversity@gmail.com
Se désabonner : https://mathlabuniversity.vercel.app/unsubscribe
"""

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json={
                "personalizations": [{
                    "to": [{"email": to_email}],
                    "subject": "Votre code de vérification - MathLab University"
                }],
                "from": {
                    "email": "mathlabuniversity@gmail.com",
                    "name": "MathLab University"
                },
                "subject": "Votre code de vérification - MathLab University",
                "content": [
                    {"type": "text/html", "value": html_body},
                    {"type": "text/plain", "value": text_body}
                ]
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        if response.status_code in [200, 202]:
            print(f"[INFO] Email envoyé à {to_email}")
        else:
            print(f"[ERROR] SendGrid: {response.status_code} - {response.text}")
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
        country=data.country,
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
# ─────────────────────────────────────────────────────────────────────────────
# VERIFY EMAIL VIA LINK — Activation par clic dans l'email
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/verify-email/{token}")
def verify_email_link(token: str, db: Session = Depends(get_db)):
    """Active le compte en cliquant sur le lien reçu par email."""
    # Le token contient l'email et le code séparés par un tiret
    try:
        email, code = token.rsplit('-', 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Lien invalide.")
    
    ok, error_msg = _validate_code(email, code)
    if not ok:
        raise HTTPException(status_code=400, detail=error_msg)
    
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    
    user.is_verified = True
    db.commit()
    
    # Redirige vers la page de connexion avec un message de succès
    return RedirectResponse(
        url="https://mathlabuniversity.vercel.app/login?verified=true",
        status_code=302
    )
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
            'exp': datetime.now(timezone.utc) + timedelta(minutes=30)
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

# ─────────────────────────────────────────────────────────────────────────────
# FORGOT PASSWORD — Envoie un lien de réinitialisation
# ─────────────────────────────────────────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Envoie un lien de réinitialisation par email."""
    email = data.email.lower()
    user = db.query(User).filter_by(email=email).first()

    if not user:
        return {"message": "Si un compte existe, un email a été envoyé."}

    # Génère un token unique
    token = secrets_module.token_urlsafe(32)
    _reset_tokens[email] = {
        'token': token,
        'expires_at': datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    }

    # Lien de réinitialisation
    reset_link = f"https://mathlabuniversity.vercel.app/reset-password?token={token}&email={email}"

    # Contenu de l'email
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 30px;">
        <h1 style="color: #1a1a2e;">MathLab University</h1>
        <p>Bonjour <strong>{user.first_name}</strong>,</p>
        <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
        <p>Cliquez sur le bouton ci-dessous :</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}"
               style="background-color: #2563eb; color: white; padding: 14px 28px;
                      text-decoration: none; border-radius: 8px; font-weight: bold;">
                Réinitialiser mon mot de passe
            </a>
        </div>
        <p style="font-size: 12px; color: gray;">
            Ce lien est valable {RESET_TOKEN_EXPIRY_MINUTES} minutes.
        </p>
    </div>
    """

    # Envoie l'email via SendGrid
    api_key = os.getenv('SENDGRID_API_KEY', '')
    if not api_key:
        print(f"[DEV] Reset link for {email}: {reset_link}")
        return {"message": "Si un compte existe, un email a été envoyé."}

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json={
                "personalizations": [{"to": [{"email": email}]}],
                "from": {"email": "mathlabuniversity@gmail.com", "name": "MathLab University"},
                "subject": "MathLab University - Réinitialisation du mot de passe",
                "content": [{"type": "text/html", "value": html_body}]
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        if response.status_code in [200, 202]:
            print(f"[INFO] Reset email envoyé à {email}")
        else:
            print(f"[ERROR] SendGrid: {response.text}")
    except Exception as e:
        print(f"[WARN] Reset email failed: {e}")

    return {"message": "Si un compte existe, un email a été envoyé."}
# ─────────────────────────────────────────────────────────────────────────────
# RESET PASSWORD — Change le mot de passe avec le token
# ─────────────────────────────────────────────────────────────────────────────
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=6)

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Réinitialise le mot de passe avec le token reçu par email."""
    email = data.email.lower()

    # Vérifie le token
    record = _reset_tokens.get(email)
    if not record:
        raise HTTPException(status_code=400, detail="Aucune demande de réinitialisation trouvée.")
    if datetime.now(timezone.utc) > record['expires_at']:
        _reset_tokens.pop(email, None)
        raise HTTPException(status_code=400, detail="Le lien a expiré. Faites une nouvelle demande.")
    if record['token'] != data.token:
        raise HTTPException(status_code=400, detail="Token invalide.")

    # Change le mot de passe
    user = db.query(User).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    user.set_password(data.new_password)
    db.commit()

    # Supprime le token
    _reset_tokens.pop(email, None)

    return {"message": "Mot de passe réinitialisé avec succès. Vous pouvez vous connecter."}

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)

@router.put("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change le mot de passe de l'utilisateur connecté."""
    if not current_user.check_password(data.old_password):
        raise HTTPException(status_code=400, detail="Ancien mot de passe incorrect.")
    
    current_user.set_password(data.new_password)
    db.commit()
    return {"message": "Mot de passe modifié avec succès."}