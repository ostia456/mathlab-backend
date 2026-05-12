"""
Scenarios API Routes - FastAPI
Gestion des scénarios pédagogiques par les enseignants
"""
import secrets
import string
from typing import Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app import SessionLocal
from app.models.scenario import Scenario
from app.models.user import User
from app.api.auth import get_current_user

# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────
class CreateScenarioRequest(BaseModel):
    title: str = Field(default='Nouveau scénario')
    description: Optional[str] = ''
    module: str = Field(default='dynamical_systems')
    config: dict = Field(default_factory=dict)
    locked_params: list = Field(default_factory=list)
    instructions: Optional[str] = ''
    is_public: bool = False

class UpdateScenarioRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    locked_params: Optional[list] = None
    instructions: Optional[str] = None
    is_public: Optional[bool] = None

# ─────────────────────────────────────────────────────────────────────────────
# Dépendance DB
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────────────────────
# Utilitaire
# ─────────────────────────────────────────────────────────────────────────────
def generate_share_code():
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/")
def list_scenarios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all scenarios for the current user"""
    if current_user.is_teacher():
        scenarios = db.query(Scenario).filter(
            or_(Scenario.created_by == current_user.id, Scenario.is_public == True)
        ).all()
    else:
        scenarios = db.query(Scenario).filter_by(is_public=True).all()
    return {'scenarios': [s.to_dict() for s in scenarios]}

@router.post("/", status_code=201)
def create_scenario(
    data: CreateScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new scenario"""
    if not current_user.is_teacher():
        raise HTTPException(status_code=403, detail="Only teachers can create scenarios")
    
    scenario = Scenario(
        title=data.title,
        description=data.description or '',
        module=data.module,
        created_by=current_user.id,
        config=data.config,
        locked_params=data.locked_params,
        instructions=data.instructions or '',
        is_public=data.is_public,
        share_code=generate_share_code()
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return {'message': 'Scenario created successfully', 'scenario': scenario.to_dict()}

@router.get("/{scenario_id}")
def get_scenario(
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific scenario"""
    scenario = db.query(Scenario).get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {'scenario': scenario.to_dict()}

@router.put("/{scenario_id}")
def update_scenario(
    scenario_id: int,
    data: UpdateScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a scenario"""
    scenario = db.query(Scenario).get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if scenario.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(scenario, key, value)
    
    db.commit()
    return {'message': 'Scenario updated successfully', 'scenario': scenario.to_dict()}

@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a scenario"""
    scenario = db.query(Scenario).get(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if scenario.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db.delete(scenario)
    db.commit()
    return {'message': 'Scenario deleted successfully'}

@router.post("/join/{share_code}")
def join_scenario(
    share_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a scenario using share code"""
    scenario = db.query(Scenario).filter_by(share_code=share_code).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Invalid share code")
    return {'scenario': scenario.to_dict()}

@router.post("/{scenario_id}/clone", status_code=201)
def clone_scenario(
    scenario_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clone an existing scenario"""
    if not current_user.is_teacher():
        raise HTTPException(status_code=403, detail="Only teachers can clone scenarios")
    
    original = db.query(Scenario).get(scenario_id)
    if not original:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    cloned = Scenario(
        title=f"{original.title} (Copie)",
        description=original.description,
        module=original.module,
        created_by=current_user.id,
        config=original.config,
        locked_params=original.locked_params,
        instructions=original.instructions,
        is_public=False,
        share_code=generate_share_code()
    )
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    return {'message': 'Scenario cloned successfully', 'scenario': cloned.to_dict()}