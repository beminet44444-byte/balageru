from dotenv import load_dotenv
load_dotenv()  # loads .env if present, before anything reads os.environ

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from config import Config
import storage


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    storage.init_storage()
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from routes.auth_routes import auth_bp
    from routes.menu_routes import menu_bp
    from routes.order_routes import order_bp
    from routes.table_routes import table_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(table_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "storage": "json-files"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=Config.DEBUG, port=5000)
