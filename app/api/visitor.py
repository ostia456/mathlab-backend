"""Visitor Stats API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app import SessionLocal
from app.models.visitor import VisitorStat
from sqlalchemy import func
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/track")
def track_visitor(db: Session = Depends(get_db)):
    """Incrémente le compteur visiteur du jour."""
    today = date.today()
    stat = db.query(VisitorStat).filter_by(date=today).first()
    if stat:
        stat.count += 1
    else:
        stat = VisitorStat(date=today, count=1)
        db.add(stat)
    db.commit()
    return {"message": "Visiteur comptabilisé", "count": stat.count}

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    today = date.today()
    week_ago = today - timedelta(days=6)

    week_stats = db.query(VisitorStat).filter(VisitorStat.date >= week_ago).all()
    stats_dict = {s.date: s.count for s in week_stats}

    # Remplit les jours manquants avec 0
    daily = []
    for i in range(7):
        d = week_ago + timedelta(days=i)
        daily.append({"date": str(d), "count": stats_dict.get(d, 0)})

    month_ago = today - timedelta(days=30)
    total = db.query(VisitorStat).with_entities(func.sum(VisitorStat.count)).scalar() or 0

    return {
        "today": stats_dict.get(today, 0),
        "this_week": sum(s.count for s in week_stats),
        "this_month": sum(s.count for s in db.query(VisitorStat).filter(VisitorStat.date >= month_ago).all()),
        "total": total,
        "daily": daily
    }