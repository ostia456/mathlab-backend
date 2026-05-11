#!/usr/bin/env python3
"""
MathLab University - Backend Entry Point
"""
import os
from app import create_app, db
from app.models import User, Exercise, ExerciseAttempt, Scenario, UserProgress

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Exercise': Exercise,
        'ExerciseAttempt': ExerciseAttempt,
        'Scenario': Scenario,
        'UserProgress': UserProgress
    }

if __name__ == '__main__':
    # ✅ MODIFICATION : Port dynamique pour Render
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)