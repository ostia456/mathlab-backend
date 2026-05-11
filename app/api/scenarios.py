"""
Scenarios API Routes
Gestion des scénarios pédagogiques par les enseignants
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import secrets
import string
from app import db
from app.models.scenario import Scenario
from app.models.user import User

sc_bp = Blueprint('scenarios', __name__)

def generate_share_code():
    """Generate a random share code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

@sc_bp.route('/', methods=['GET'])
@jwt_required()
def list_scenarios():
    """List all scenarios for the current user"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if user.is_teacher():
        # Teachers see their own scenarios and public ones
        scenarios = Scenario.query.filter(
            (Scenario.created_by == user_id) | (Scenario.is_public == True)
        ).all()
    else:
        # Students see public scenarios and those shared with them
        scenarios = Scenario.query.filter_by(is_public=True).all()
    
    return jsonify({'scenarios': [s.to_dict() for s in scenarios]})

@sc_bp.route('/', methods=['POST'])
@jwt_required()
def create_scenario():
    """Create a new scenario"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.is_teacher():
        return jsonify({'error': 'Only teachers can create scenarios'}), 403
    
    data = request.get_json()
    
    scenario = Scenario(
        title=data.get('title', 'Nouveau scénario'),
        description=data.get('description', ''),
        module=data.get('module', 'dynamical_systems'),
        created_by=user_id,
        config=data.get('config', {}),
        locked_params=data.get('locked_params', []),
        instructions=data.get('instructions', ''),
        is_public=data.get('is_public', False),
        share_code=generate_share_code()
    )
    
    db.session.add(scenario)
    db.session.commit()
    
    return jsonify({
        'message': 'Scenario created successfully',
        'scenario': scenario.to_dict()
    }), 201

@sc_bp.route('/<int:scenario_id>', methods=['GET'])
@jwt_required()
def get_scenario(scenario_id):
    """Get a specific scenario"""
    scenario = Scenario.query.get(scenario_id)
    
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    return jsonify({'scenario': scenario.to_dict()})

@sc_bp.route('/<int:scenario_id>', methods=['PUT'])
@jwt_required()
def update_scenario(scenario_id):
    """Update a scenario"""
    user_id = int(get_jwt_identity())
    scenario = Scenario.query.get(scenario_id)
    
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    if scenario.created_by != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    scenario.title = data.get('title', scenario.title)
    scenario.description = data.get('description', scenario.description)
    scenario.config = data.get('config', scenario.config)
    scenario.locked_params = data.get('locked_params', scenario.locked_params)
    scenario.instructions = data.get('instructions', scenario.instructions)
    scenario.is_public = data.get('is_public', scenario.is_public)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Scenario updated successfully',
        'scenario': scenario.to_dict()
    })

@sc_bp.route('/<int:scenario_id>', methods=['DELETE'])
@jwt_required()
def delete_scenario(scenario_id):
    """Delete a scenario"""
    user_id = int(get_jwt_identity())
    scenario = Scenario.query.get(scenario_id)
    
    if not scenario:
        return jsonify({'error': 'Scenario not found'}), 404
    
    if scenario.created_by != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(scenario)
    db.session.commit()
    
    return jsonify({'message': 'Scenario deleted successfully'})

@sc_bp.route('/join/<string:share_code>', methods=['POST'])
@jwt_required()
def join_scenario(share_code):
    """Join a scenario using share code"""
    scenario = Scenario.query.filter_by(share_code=share_code).first()
    
    if not scenario:
        return jsonify({'error': 'Invalid share code'}), 404
    
    return jsonify({
        'scenario': scenario.to_dict()
    })

@sc_bp.route('/<int:scenario_id>/clone', methods=['POST'])
@jwt_required()
def clone_scenario(scenario_id):
    """Clone an existing scenario"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.is_teacher():
        return jsonify({'error': 'Only teachers can clone scenarios'}), 403
    
    original = Scenario.query.get(scenario_id)
    
    if not original:
        return jsonify({'error': 'Scenario not found'}), 404
    
    cloned = Scenario(
        title=f"{original.title} (Copie)",
        description=original.description,
        module=original.module,
        created_by=user_id,
        config=original.config,
        locked_params=original.locked_params,
        instructions=original.instructions,
        is_public=False,
        share_code=generate_share_code()
    )
    
    db.session.add(cloned)
    db.session.commit()
    
    return jsonify({
        'message': 'Scenario cloned successfully',
        'scenario': cloned.to_dict()
    }), 201
