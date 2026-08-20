from flask import Flask
from config import Config

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.principal import principal_bp
from routes.student import student_bp
from routes.parent import parent_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(principal_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(parent_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
