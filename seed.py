"""
Script pour créer les comptes de test
Usage : python seed.py
"""
from app import SessionLocal, engine
from app.models import Base
from app.models.user import User

# Crée les tables si elles n'existent pas
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Liste des comptes à créer
users_data = [
    {
        'email': 'ostiadedo456@gmail.com',
        'password': '12345678',
        'first_name': 'Ostia',
        'last_name': 'Dedo',
        'role': 'student',
    },
    {
        'email': 'testsimplement@gmail.com',
        'password': '12345678',
        'first_name': 'Test',
        'last_name': 'Simplement',
        'role': 'student',
    },
    {
        'email': 'professeur@mathlab.edu',
        'password': '12345678',
        'first_name': 'Jean',
        'last_name': 'Dupont',
        'role': 'teacher',
    },
    {
        'email': 'admin@mathlab.edu',
        'password': '12345678',
        'first_name': 'Admin',
        'last_name': 'MathLab',
        'role': 'admin',
    },
]

for data in users_data:
    # Vérifie si l'utilisateur existe déjà
    existing = db.query(User).filter_by(email=data['email']).first()
    if existing:
        print(f"⚠️ {data['email']} existe déjà → ignoré")
        continue
    
    user = User(
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data['role'],
        is_verified=True,  # Pas besoin de vérification email
        is_active=True,
    )
    user.set_password(data['password'])
    db.add(user)
    print(f"✅ {data['email']} créé ({data['role']})")

# ══════════════════════════════════════════════════════
# SUPER ADMIN
# ══════════════════════════════════════════════════════
super_admin_email = 'ostiadedo456@gmail.com'
admin = db.query(User).filter_by(email=super_admin_email).first()

if admin:
    admin.role = 'super_admin'
    admin.is_verified = True
    admin.is_active = True
    print(f"✅ {admin.email} → SUPER_ADMIN")
else:
    admin = User(
        email=super_admin_email,
        first_name='Ostia',
        last_name='Dedo',
        role='super_admin',
        is_verified=True,
        is_active=True,
    )
    admin.set_password('TonMotDePasseIci')
    db.add(admin)
    print(f"✅ Créé : {admin.email} (super_admin)")

db.commit()
db.close()
print("\n🎉 Tous les comptes sont prêts !")