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

db.commit()
db.close()
print("\n🎉 Tous les comptes sont prêts !")