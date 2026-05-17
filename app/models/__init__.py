from sqlalchemy.orm import declarative_base

# Base déclarative pour tous les modèles
Base = declarative_base()

# Importer les modèles pour qu'ils soient enregistrés dans Base
from app.models.visitor import VisitorStat
from app.models.user import User
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.scenario import Scenario
from app.models.progress import UserProgress

__all__ = ['Base', 'User', 'Exercise', 'ExerciseAttempt', 'Scenario', 'UserProgress']