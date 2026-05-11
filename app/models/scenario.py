"""
Scenario Model - Teacher-created learning scenarios
"""
from app import db
from datetime import datetime

class Scenario(db.Model):
    __tablename__ = 'scenarios'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    module = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Scenario configuration
    config = db.Column(db.JSON, nullable=False)  # Module-specific configuration
    locked_params = db.Column(db.JSON, default=list)  # Parameters students cannot modify
    instructions = db.Column(db.Text)  # Instructions for students
    
    # Sharing
    is_public = db.Column(db.Boolean, default=False)
    share_code = db.Column(db.String(20), unique=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'module': self.module,
            'config': self.config,
            'locked_params': self.locked_params,
            'instructions': self.instructions,
            'is_public': self.is_public,
            'share_code': self.share_code,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
