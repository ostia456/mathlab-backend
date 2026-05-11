#!/usr/bin/env python3
"""
MathLab University - Database Seeding Script
Crée des utilisateurs par défaut pour les tests
"""
from app import create_app, db
from app.models.user import User
from app.models.exercise import Exercise
from app.models.progress import UserProgress
from datetime import datetime

app = create_app()

def seed_database():
    with app.app_context():
        print("🌱 Seeding database...")
        
        # Create tables
        db.create_all()
        
        # Check if users already exist
        if User.query.filter_by(email='ostiadedo456@gmail.com').first():
            print("✅ Users already exist, skipping seed...")
            return
        
        # Create default users
        users_data = [
            {
                'email': 'ostiadedo456@gmail.com',
                'password': '12345678',
                'first_name': 'Ostia',
                'last_name': 'DEDO',
                'role': 'student'
            },
            {
                'email': 'testsimplement@gmail.com',
                'password': '12345678',
                'first_name': 'Test',
                'last_name': 'User',
                'role': 'student'
            },
            {
                'email': 'professeur@mathlab.edu',
                'password': '12345678',
                'first_name': 'Jean',
                'last_name': 'Professeur',
                'role': 'teacher'
            },
            {
                'email': 'admin@mathlab.edu',
                'password': '12345678',
                'first_name': 'Admin',
                'last_name': 'System',
                'role': 'admin'
            }
        ]
        
        created_users = []
        for user_data in users_data:
            user = User(
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role'],
                is_active=True,
                last_login=datetime.utcnow()
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            created_users.append(user)
            print(f"  ✓ Created user: {user_data['email']} ({user_data['role']})")
        
        db.session.commit()
        
        # Create progress entries for each user
        modules = ['dynamical_systems', 'numerical_methods', 'linear_algebra', 'graph_theory']
        for user in created_users:
            for module in modules:
                progress = UserProgress(
                    user_id=user.id,
                    module=module,
                    exercises_completed=0,
                    exercises_attempted=0,
                    total_points=0,
                    time_spent=0,
                    current_difficulty=1,
                    success_rate=0.0,
                    topic_progress={}
                )
                db.session.add(progress)
        
        db.session.commit()
        
        print("\n✅ Database seeded successfully!")
        print("\n📧 Default users created:")
        print("  • ostiadedo456@gmail.com / 12345678 (student)")
        print("  • testsimplement@gmail.com / 12345678 (student)")
        print("  • professeur@mathlab.edu / 12345678 (teacher)")
        print("  • admin@mathlab.edu / 12345678 (admin)")

if __name__ == '__main__':
    seed_database()
