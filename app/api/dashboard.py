"""
Dashboard API Routes
Tableau de bord enseignant avec statistiques
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc
from app import db
from app.models.user import User
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.progress import UserProgress
from app.models.scenario import Scenario

db_bp = Blueprint('dashboard', __name__)

@db_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """Get dashboard statistics for teachers"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # User statistics
    total_students = User.query.filter_by(role='student').count()
    total_teachers = User.query.filter(User.role.in_(['teacher', 'admin'])).count()
    
    # Exercise statistics
    total_exercises = Exercise.query.count()
    total_attempts = ExerciseAttempt.query.count()
    
    # Success rate
    correct_attempts = ExerciseAttempt.query.filter_by(is_correct=True).count()
    success_rate = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
    
    # Module statistics
    module_stats = db.session.query(
        Exercise.module,
        func.count(ExerciseAttempt.id).label('attempts'),
        func.avg(ExerciseAttempt.score).label('avg_score')
    ).outerjoin(ExerciseAttempt).group_by(Exercise.module).all()
    
    # Recent activity
    recent_attempts = ExerciseAttempt.query.order_by(
        desc(ExerciseAttempt.created_at)
    ).limit(10).all()
    
    # Top students
    top_students = db.session.query(
        User,
        func.sum(ExerciseAttempt.score).label('total_score'),
        func.count(ExerciseAttempt.id).label('attempt_count')
    ).join(ExerciseAttempt).group_by(User.id).order_by(
        desc('total_score')
    ).limit(10).all()
    
    return jsonify({
        'overview': {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_exercises': total_exercises,
            'total_attempts': total_attempts,
            'success_rate': round(success_rate, 2)
        },
        'module_stats': [
            {
                'module': m.module,
                'attempts': m.attempts,
                'avg_score': round(m.avg_score, 2) if m.avg_score else 0
            } for m in module_stats
        ],
        'recent_activity': [a.to_dict() for a in recent_attempts],
        'top_students': [
            {
                'user': s.User.to_dict(),
                'total_score': s.total_score,
                'attempt_count': s.attempt_count
            } for s in top_students
        ]
    })

@db_bp.route('/students', methods=['GET'])
@jwt_required()
def get_students():
    """Get detailed student information"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403
    
    students = User.query.filter_by(role='student').all()
    
    result = []
    for student in students:
        progress = UserProgress.query.filter_by(user_id=student.id).all()
        attempts = ExerciseAttempt.query.filter_by(user_id=student.id).count()
        correct = ExerciseAttempt.query.filter_by(user_id=student.id, is_correct=True).count()
        
        result.append({
            'student': student.to_dict(),
            'progress': [p.to_dict() for p in progress],
            'stats': {
                'total_attempts': attempts,
                'correct_attempts': correct,
                'success_rate': round(correct / attempts * 100, 2) if attempts > 0 else 0
            }
        })
    
    return jsonify({'students': result})

@db_bp.route('/student/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student_detail(student_id):
    """Get detailed information about a specific student"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403
    
    student = User.query.get(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # Get all attempts
    attempts = ExerciseAttempt.query.filter_by(
        user_id=student_id
    ).order_by(desc(ExerciseAttempt.created_at)).all()
    
    # Get progress
    progress = UserProgress.query.filter_by(user_id=student_id).all()
    
    # Time spent per module
    time_per_module = {}
    for p in progress:
        time_per_module[p.module] = p.time_spent
    
    return jsonify({
        'student': student.to_dict(),
        'attempts': [a.to_dict() for a in attempts],
        'progress': [p.to_dict() for p in progress],
        'time_per_module': time_per_module
    })

@db_bp.route('/exercises', methods=['GET'])
@jwt_required()
def get_exercise_stats():
    """Get exercise statistics"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403
    
    exercises = Exercise.query.all()
    
    result = []
    for exercise in exercises:
        attempts = ExerciseAttempt.query.filter_by(exercise_id=exercise.id)
        total = attempts.count()
        correct = attempts.filter_by(is_correct=True).count()
        avg_score = attempts.with_entities(func.avg(ExerciseAttempt.score)).scalar()
        avg_time = attempts.with_entities(func.avg(ExerciseAttempt.time_spent)).scalar()
        
        result.append({
            'exercise': exercise.to_dict(),
            'stats': {
                'total_attempts': total,
                'correct_attempts': correct,
                'success_rate': round(correct / total * 100, 2) if total > 0 else 0,
                'avg_score': round(avg_score, 2) if avg_score else 0,
                'avg_time': round(avg_time, 2) if avg_time else 0
            }
        })
    
    return jsonify({'exercises': result})

@db_bp.route('/scenarios', methods=['GET'])
@jwt_required()
def get_scenario_stats():
    """Get scenario usage statistics"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403
    
    scenarios = Scenario.query.filter_by(created_by=user_id).all()
    
    return jsonify({
        'scenarios': [s.to_dict() for s in scenarios]
    })
