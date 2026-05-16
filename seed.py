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
    admin.set_password('12345678')
    db.add(admin)
    print(f"✅ Créé : {admin.email} (super_admin)")

db.commit()
db.close()
print("\n🎉 Tous les comptes sont prêts !")