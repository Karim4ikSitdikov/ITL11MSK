from flask import Flask, jsonify, send_from_directory
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from config import Config
from database.db import Database

# Import blueprints
from routes.auth import auth_bp
from routes.preferences import preferences_bp
from routes.chat import chat_bp
from routes.lotteries import lotteries_bp
from routes.analytics import analytics_bp
from routes.test import test_bp


def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Initialize extensions
    jwt = JWTManager(app)
    CORS(app)
    
    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[Config.RATELIMIT_DEFAULT],
        storage_uri=Config.RATELIMIT_STORAGE_URL
    )
    
    # Apply specific rate limit to chat endpoint
    limiter.limit(Config.RATELIMIT_CHAT)(chat_bp)
    
    # Initialize database
    Database.initialize()
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(preferences_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(lotteries_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(test_bp)
    
    # Serve static files
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('static', filename)
    
    # Serve templates (HTML pages)
    @app.route('/')
    def index():
        return send_from_directory('templates', 'landing.html')
    
    @app.route('/register')
    def register_page():
        return send_from_directory('templates', 'register.html')
    
    @app.route('/dashboard')
    def dashboard_page():
        return send_from_directory('templates', 'dashboard.html')
    
    @app.route('/lotteries')
    def lotteries_page():
        return send_from_directory('templates', 'lotteries.html')
    
    @app.route('/chat')
    def chat_page():
        return send_from_directory('templates', 'chat.html')
    
    @app.route('/test-chat')
    def test_chat_page():
        return send_from_directory('templates', 'test_chat.html')
    
    # Health check endpoint
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    # JWT error handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({'error': 'Missing or invalid token'}), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({'error': 'Invalid token'}), 401
    
    return app


def init_database():
    """Initialize database schema"""
    try:
        Database.init_schema()
        print("✓ Database schema initialized")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        print("  Make sure PostgreSQL is running and DATABASE_URL is correctly configured")


if __name__ == '__main__':
    import sys
    import os
    
    # Check if --init-db flag was passed
    if '--init-db' in sys.argv:
        print("Initializing database...")
        init_database()
        sys.exit(0)
    
    # Create and run app
    app = create_app()
    
    print("\n" + "="*60)
    print("STOLOTO LOTTERY ASSISTANT - STARTING")
    print("="*60)
    print(f"Environment: {Config.DEBUG and 'Development' or 'Production'}")
    print(f"Server: http://localhost:{os.getenv('PORT', 5000)}")
    print(f"Database: {Config.DATABASE_URL.split('@')[1] if '@' in Config.DATABASE_URL else 'configured'}")
    print(f"Ollama: {Config.OLLAMA_HOST} (model: {Config.OLLAMA_MODEL})")
    print("="*60 + "\n")
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
