"""Challenge Models"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models import Base

class Challenge(Base):
    __tablename__ = 'challenges'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500))
    module = Column(String(50), nullable=False)
    period = Column(String(20), nullable=False)  # 'weekly', 'monthly', 'sprint'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    exercises = relationship('ChallengeExercise', back_populates='challenge', lazy='dynamic')
    submissions = relationship('ChallengeSubmission', back_populates='challenge', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'module': self.module,
            'period': self.period,
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ChallengeExercise(Base):
    __tablename__ = 'challenge_exercises'

    id = Column(Integer, primary_key=True)
    challenge_id = Column(Integer, ForeignKey('challenges.id'), nullable=False)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    points = Column(Integer, default=10)
    order_num = Column(Integer, default=1)

    challenge = relationship('Challenge', back_populates='exercises')

    def to_dict(self):
        return {
            'id': self.id,
            'challenge_id': self.challenge_id,
            'exercise_id': self.exercise_id,
            'points': self.points,
            'order_num': self.order_num,
        }


class ChallengeSubmission(Base):
    __tablename__ = 'challenge_submissions'

    id = Column(Integer, primary_key=True)
    challenge_id = Column(Integer, ForeignKey('challenges.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    exercise_id = Column(Integer, ForeignKey('exercises.id'), nullable=False)
    score = Column(Float, default=0)
    is_correct = Column(Boolean, default=False)
    time_spent = Column(Integer, default=0)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    challenge = relationship('Challenge', back_populates='submissions')

    def to_dict(self):
        return {
            'id': self.id,
            'challenge_id': self.challenge_id,
            'user_id': self.user_id,
            'exercise_id': self.exercise_id,
            'score': self.score,
            'is_correct': self.is_correct,
            'time_spent': self.time_spent,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
        }