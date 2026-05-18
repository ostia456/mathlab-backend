"""Programming Challenge Models"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.models import Base


class ProgrammingChallenge(Base):
    __tablename__ = 'programming_challenges'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String(20), default='Facile')  # Facile, Moyen, Difficile
    example_input = Column(Text)
    example_output = Column(Text)
    test_cases = Column(JSON, default=list)  # [{input: ..., expected: ...}]
    starter_code = Column(Text)  # Code de départ
    solution_code = Column(Text)  # Solution de référence
    points = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    submissions = relationship('ProgrammingSubmission', back_populates='challenge', lazy='dynamic')

    def to_dict(self, include_solution=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'difficulty': self.difficulty,
            'example_input': self.example_input,
            'example_output': self.example_output,
            'starter_code': self.starter_code,
            'points': self.points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_solution:
            data['solution_code'] = self.solution_code
            data['test_cases'] = self.test_cases
        return data


class ProgrammingSubmission(Base):
    __tablename__ = 'programming_submissions'

    id = Column(Integer, primary_key=True)
    challenge_id = Column(Integer, ForeignKey('programming_challenges.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    code = Column(Text, nullable=False)
    language = Column(String(20), default='python')
    status = Column(String(20), default='pending')  # pending, success, failed, error
    score = Column(Float, default=0)
    execution_time = Column(Float)  # en ms
    memory_used = Column(Float)  # en ko
    output = Column(Text)
    error_message = Column(Text)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    challenge = relationship('ProgrammingChallenge', back_populates='submissions')

    def to_dict(self):
        return {
            'id': self.id,
            'challenge_id': self.challenge_id,
            'user_id': self.user_id,
            'status': self.status,
            'score': self.score,
            'execution_time': self.execution_time,
            'memory_used': self.memory_used,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
        }