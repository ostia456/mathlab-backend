"""
Scenario Model - Teacher-created learning scenarios
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import Base


class Scenario(Base):
    __tablename__ = 'scenarios'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    module = Column(String(50), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Scenario configuration
    config = Column(JSON, nullable=False)
    locked_params = Column(JSON, default=list)
    instructions = Column(Text)

    # Sharing
    is_public = Column(Boolean, default=False)
    share_code = Column(String(20), unique=True)

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationship
    creator = relationship('User', back_populates='scenarios')

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