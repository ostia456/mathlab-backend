#!/usr/bin/env python3
"""
Initialize database and create default users
"""
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.exercise import Exercise
from app.models.scenario import Scenario
from app.models.progress import UserProgress
from datetime import datetime

def init_database():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Tables created!")
        
        # Check if default users exist
        if User.query.filter_by(email='ostiadedo456@gmail.com').first():
            print("\nDefault users already exist!")
            return
        
        print("\nCreating default users...")
        
        # Create student user
        student = User(
            email='ostiadedo456@gmail.com',
            first_name='Ostia',
            last_name='DEDO',
            role='student',
            is_active=True
        )
        student.set_password('12345678')
        db.session.add(student)
        
        # Create test user
        test_user = User(
            email='testsimplement@gmail.com',
            first_name='Test',
            last_name='User',
            role='student',
            is_active=True
        )
        test_user.set_password('12345678')
        db.session.add(test_user)
        
        # Create teacher user
        teacher = User(
            email='professeur@mathlab.edu',
            first_name='Jean',
            last_name='Professeur',
            role='teacher',
            is_active=True
        )
        teacher.set_password('12345678')
        db.session.add(teacher)
        
        # Create admin user
        admin = User(
            email='admin@mathlab.edu',
            first_name='Admin',
            last_name='System',
            role='admin',
            is_active=True
        )
        admin.set_password('12345678')
        db.session.add(admin)
        
        db.session.commit()
        
        print("\nDefault users created successfully!")
        print("\n" + "="*60)
        print("LOGIN CREDENTIALS:")
        print("="*60)
        print("\nSTUDENT accounts:")
        print("   Email: ostiadedo456@gmail.com")
        print("   Password: 12345678")
        print("\n   Email: testsimplement@gmail.com")
        print("   Password: 12345678")
        print("\nTEACHER account:")
        print("   Email: professeur@mathlab.edu")
        print("   Password: 12345678")
        print("\nADMIN account:")
        print("   Email: admin@mathlab.edu")
        print("   Password: 12345678")
        print("="*60)

if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
