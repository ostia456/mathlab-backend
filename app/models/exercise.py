"""
Exercise and ExerciseAttempt Models
"""
from app import db
from datetime import datetime
import json

class Exercise(db.Model):
    __tablename__ = 'exercises'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(50), nullable=False)  # dynamical_systems, numerical_methods, linear_algebra, graph_theory
    difficulty = db.Column(db.Integer, default=1)  # 1-5
    problem_data = db.Column(db.JSON, nullable=False)  # Generated problem parameters
    solution_data = db.Column(db.JSON, nullable=False)  # Correct solution
    hints = db.Column(db.JSON, default=list)
    time_limit = db.Column(db.Integer, default=0)  # 0 = no limit, in seconds
    points = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attempts = db.relationship('ExerciseAttempt', backref='exercise', lazy='dynamic')
    
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

class ExerciseAttempt(db.Model):
    __tablename__ = 'exercise_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.id'), nullable=False)
    answer_data = db.Column(db.JSON)  # User's answer
    is_correct = db.Column(db.Boolean)
    score = db.Column(db.Float)  # 0-100
    feedback = db.Column(db.Text)  # Personalized feedback
    time_spent = db.Column(db.Integer)  # in seconds
    attempt_number = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
