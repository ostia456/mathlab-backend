"""
Exercise and ExerciseAttempt Models
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import Base


class Exercise(Base):
    __tablename__ = 'exercises'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    module = Column(String(50), nullable=False)
    difficulty = Column(Integer, default=1)
    problem_data = Column(JSON, nullable=False)
    solution_data = Column(JSON, nullable=False)
    hints = Column(JSON, default=list)
    time_limit = Column(Integer, default=0)
    points = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    attempts = relationship('ExerciseAttempt', back_populates='exercise', lazy='dynamic')

    def to_dict(self, include_solution=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'module': self.module,
            'difficulty': self.difficulty,
            'problem_data': self.problem_data,
            'hints': self.hints,
            'time_limit': self.time_limit,
            'points': self.points,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_solution:
            data['solution_data'] = self.solution_data
        return data


class ExerciseAttempt(Base):
    __tablename__ = 'exercise_attempts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    answer_data = Column(JSON)
    is_correct = Column(Boolean)
    score = Column(Float)
    feedback = Column(Text)
    time_spent = Column(Integer)
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship('User', back_populates='exercise_attempts')
    exercise = relationship('Exercise', back_populates='attempts')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'exercise_id': self.exercise_id,
            'answer_data': self.answer_data,
            'is_correct': self.is_correct,
            'score': self.score,
            'feedback': self.feedback,
            'time_spent': self.time_spent,
            'attempt_number': self.attempt_number,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }