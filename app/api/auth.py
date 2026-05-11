"""
Authentication API Routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from app import db
from app.models.user import User
from datetime import datetime, timedelta
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

auth_bp = Blueprint('auth', __name__)

# Token blacklist for logout
blacklist = set()

# ─────────────────────────────────────────────────────────────────────────────
# Stockage temporaire des codes de vérification
# Structure : { email: { code, expires_at, attempts } }
# ─────────────────────────────────────────────────────────────────────────────
_pending_verifications: dict = {}

CODE_EXPIRY_MINUTES = 15
MAX_ATTEMPTS        = 5


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires email
# ─────────────────────────────────────────────────────────────────────────────
def _generate_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


def _store_code(email: str, code: str):
    _pending_verifications[email] = {
        'code':       code,
        'expires_at': datetime.utcnow() + timedelta(minutes=CODE_EXPIRY_MINUTES),
        'attempts':   0,
    }


def _validate_code(email: str, code: str) -> tuple:
    """Retourne (success: bool, error_message: str)"""
    record = _pending_verifications.get(email)

    if not record:
        return False, "Aucun code en attente pour cet email. Recommencez l'inscription."

    if datetime.utcnow() > record['expires_at']:
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
    """Envoie le code par email via Gmail SMTP."""
    gmail_sender   = os.getenv('GMAIL_SENDER', '')
    gmail_password = os.getenv('GMAIL_APP_PASSWORD', '')

    if not gmail_sender or not gmail_password:
        # Mode développement : affiche le code dans la console
        print(f"\n{'='*40}")
        print(f"[DEV] Code de vérification pour {to_email} : {code}")
        print(f"{'='*40}\n")
        return

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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MathLab University <{gmail_sender}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(gmail_sender, gmail_password)
        smtp.sendmail(gmail_sender, to_email, msg.as_string())


# ─────────────────────────────────────────────────────────────────────────────
# REGISTER — Étape 1 : crée le compte + envoie le code
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user and send verification email"""
    data = request.get_json()

    # Validation
    required_fields = ['email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    email = data['email'].lower()

    # Vérifie si l'email existe déjà
    existing = User.query.filter_by(email=email).first()
    if existing:
        if existing.is_verified:
            return jsonify({'error': 'Email already registered'}), 409
        # Compte non vérifié → on renvoie juste un nouveau code
        code = _generate_code()
        _store_code(email, code)
        try:
            _send_verification_email(email, existing.first_name, code)
        except Exception as e:
            print(f"[WARN] Email send failed: {e}")
        return jsonify({
            'message': 'Verification code resent. Please check your email.',
            'email': email,
        }), 200

    # Crée le nouveau compte (is_verified=False par défaut)
    user = User(
        email=email,
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data.get('role', 'student'),
        is_verified=False,
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    # Génère et envoie le code
    code = _generate_code()
    _store_code(email, code)
    try:
        _send_verification_email(email, user.first_name, code)
    except Exception as e:
        print(f"[WARN] Email send failed: {e}")

    return jsonify({
        'message': 'Account created. Please check your email for the verification code.',
        'email': email,
    }), 201


# ─────────────────────────────────────────────────────────────────────────────
# VERIFY EMAIL — Étape 2 : valide le code + active le compte
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """Verify email with 6-digit code"""
    data  = request.get_json()
    email = data.get('email', '').lower()
    code  = data.get('code', '').strip()

    if not email or not code:
        return jsonify({'error': 'Email and code are required'}), 400

    ok, error_msg = _validate_code(email, code)
    if not ok:
        return jsonify({'error': error_msg}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_verified = True
    db.session.commit()

    return jsonify({'message': 'Email verified successfully. You can now log in.'}), 200


# ─────────────────────────────────────────────────────────────────────────────
# RESEND CODE — Renvoie un nouveau code (anti-spam 60s)
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification code"""
    data  = request.get_json()
    email = data.get('email', '').lower()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Email not found'}), 404
    if user.is_verified:
        return jsonify({'error': 'This account is already verified'}), 400

    # Anti-spam : vérifie qu'il n'y a pas de code récent (< 60s)
    existing = _pending_verifications.get(email)
    if existing:
        elapsed = (datetime.utcnow() - (existing['expires_at'] - timedelta(minutes=CODE_EXPIRY_MINUTES))).total_seconds()
        if elapsed < 60:
            wait = int(60 - elapsed)
            return jsonify({'error': f'Please wait {wait} seconds before resending.'}), 429

    code = _generate_code()
    _store_code(email, code)

    try:
        _send_verification_email(email, user.first_name, code)
    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500

    return jsonify({'message': 'Verification code resent.'}), 200


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN — bloque les comptes non vérifiés
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()

    email    = data.get('email', '').lower()
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403

    # ← NOUVEAU : bloque si l'email n'est pas vérifié
    if not user.is_verified:
        return jsonify({
            'error': 'Please verify your email before logging in.',
            'email': email,
            'needs_verification': True,   # ← le frontend peut détecter ça
        }), 403

    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token
    })


# ─────────────────────────────────────────────────────────────────────────────
# Routes existantes — inchangées
# ─────────────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (invalidate token)"""
    jti = get_jwt()['jti']
    blacklist.add(jti)
    return jsonify({'message': 'Successfully logged out'})


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user.to_dict()})


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'password' in data:
        user.set_password(data['password'])

    db.session.commit()

    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict()
    })


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """List all users (teacher/admin only)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403

    users = User.query.all()
    return jsonify({'users': [u.to_dict() for u in users]})
