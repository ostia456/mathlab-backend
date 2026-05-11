"""
User Progress Model
"""
from app import db
from datetime import datetime

class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module = db.Column(db.String(50), nullable=False)  # dynamical_systems, numerical_methods, etc.
    
    # Progress metrics
    exercises_completed = db.Column(db.Integer, default=0)
    exercises_attempted = db.Column(db.Integer, default=0)
    total_points = db.Column(db.Integer, default=0)
    time_spent = db.Column(db.Integer, default=0)  # in seconds
    
    # Skill levels (adaptive difficulty)
    current_difficulty = db.Column(db.Integer, default=1)  # 1-5
    success_rate = db.Column(db.Float, default=0.0)  # 0-100
    
    # Detailed progress by topic
    topic_progress = db.Column(db.JSON, default=dict)  # {topic: {completed: n, total: m}}
    
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
