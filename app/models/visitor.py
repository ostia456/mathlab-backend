"""Visitor Stats Model"""
from datetime import date, datetime, timezone
from sqlalchemy import Column, Integer, Date, DateTime
from app.models import Base

class VisitorStat(Base):
    __tablename__ = 'visitor_stats'

    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False, default=date.today)
    count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))