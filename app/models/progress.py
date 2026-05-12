"""
User Progress Model
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import Base


class UserProgress(Base):
    __tablename__ = 'user_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    module = Column(String(50), nullable=False)

    # Progress metrics
    exercises_completed = Column(Integer, default=0)
    exercises_attempted = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    time_spent = Column(Integer, default=0)

    # Skill levels (adaptive difficulty)
    current_difficulty = Column(Integer, default=1)
    success_rate = Column(Float, default=0.0)

    # Detailed progress by topic
    topic_progress = Column(JSON, default=dict)

    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    user = relationship('User', back_populates='progress')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'module': self.module,
            'exercises_completed': self.exercises_completed,
            'exercises_attempted': self.exercises_attempted,
            'total_points': self.total_points,
            'time_spent': self.time_spent,
            'current_difficulty': self.current_difficulty,
            'success_rate': self.success_rate,
            'topic_progress': self.topic_progress,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def update_success_rate(self):
        if self.exercises_attempted > 0:
            self.success_rate = (self.exercises_completed / self.exercises_attempted) * 100

    def adjust_difficulty(self):
        """Adjust difficulty based on success rate"""
        if self.success_rate >= 80 and self.current_difficulty < 5:
            self.current_difficulty += 1
        elif self.success_rate < 40 and self.current_difficulty > 1:
            self.current_difficulty -= 1