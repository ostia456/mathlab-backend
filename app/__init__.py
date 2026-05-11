from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

# ✅ FIX : load_dotenv() au niveau module, AVANT tout le reste
load_dotenv()

# Initialize extensions without app (factory pattern)
db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
migrate = Migrate()

def create_app(config_name='development'):
    """Application factory function"""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # ✅ MODIFICATION : Gérer automatiquement PostgreSQL sur Render
    database_url = os.getenv('DATABASE_URL', 'sqlite:///mathlab.db')
    # Render fournit DATABASE_URL en format postgres:// mais SQLAlchemy attend postgresql://
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')

    # Initialize extensions with app
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Configuration CORS
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000')
    origins_list = [o.strip() for o in cors_origins.split(",") if o.strip()]
    
    # ✅ AMÉLIORATION : Support credentials (cookies)
    cors.init_app(app, 
        resources={
            r"/api/*": {
                "origins": origins_list or ["*"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "supports_credentials": True,
                "expose_headers": ["Content-Range", "X-Content-Range"]
            }
        }
    )

    # Register blueprints - IMPORTS MUST BE INSIDE to avoid circular imports
    from app.api.auth import auth_bp, blacklist
    from app.api.dashboard import db_bp
    from app.api.dynamical_systems import ds_bp
    from app.api.exercises import ex_bp
    from app.api.graph_theory import gt_bp
    from app.api.linear_algebra import la_bp
    from app.api.numerical_methods import nm_bp
    from app.api.scenarios import sc_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(db_bp, url_prefix='/api/dashboard')
    app.register_blueprint(ds_bp, url_prefix='/api/dynamical-systems')
    app.register_blueprint(ex_bp, url_prefix='/api/exercises')
    app.register_blueprint(gt_bp, url_prefix='/api/graph-theory')
    app.register_blueprint(la_bp, url_prefix='/api/linear-algebra')
    app.register_blueprint(nm_bp, url_prefix='/api/numerical-methods')
    app.register_blueprint(sc_bp, url_prefix='/api/scenarios')

    # ✅ AJOUT : Route de santé pour Render
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'message': 'MathLab API is running'}, 200

    # JWT token blacklist check
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return jwt_payload['jti'] in blacklist

    return app

# Import models after db is defined to avoid circular imports
from app.models.user import User
from app.models.exercise import Exercise, ExerciseAttempt
from app.models.scenario import Scenario
from app.models.progress import UserProgress

__all__ = ['create_app', 'db', 'jwt', 'User', 'Exercise', 'ExerciseAttempt', 'Scenario', 'UserProgress']