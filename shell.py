"""
Shell interactif pour MathLab University (FastAPI)
Usage : python -i shell.py
"""
from app import SessionLocal
from app.models.user import User
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.scenario import Scenario
from app.models.progress import UserProgress

# Ouvre une session DB
db = SessionLocal()

print("=" * 50)
print("🐍 MathLab University - Shell Interactif")
print("=" * 50)
print("Variables disponibles :")
print("  db      → Session SQLAlchemy")
print("  User    → Modèle utilisateur")
print("  Exercise, ExerciseAttempt, Scenario, UserProgress")
print("=" * 50)