import os
from flask import Flask
from .extensions import db, login_manager, csrf


def create_app(config_class=None):
    app = Flask(__name__, instance_relative_config=True)

    if config_class is None:
        env = os.environ.get('FLASK_ENV', 'development')
        if env == 'production':
            from config import ProdConfig
            config_class = ProdConfig
        else:
            from config import DevConfig
            config_class = DevConfig

    app.config.from_object(config_class)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melde dich an.'
    login_manager.login_message_category = 'info'

    # User loader
    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .auth import auth_bp
    from .booking import booking_bp
    from .api import api_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Jinja2 filters
    @app.template_filter('format_price')
    def format_price(cents):
        if cents is None:
            cents = 0
        euros = cents / 100
        return f'{euros:,.2f} \u20ac'.replace(',', 'X').replace('.', ',').replace('X', '.')

    @app.template_filter('format_date_de')
    def format_date_de(date_obj):
        if date_obj is None:
            return ''
        days = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        return f'{days[date_obj.weekday()]} {date_obj.strftime("%d.%m.%Y")}'

    # Create tables
    with app.app_context():
        db.create_all()

    return app
