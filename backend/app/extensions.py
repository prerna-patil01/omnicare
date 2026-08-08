"""Extension singletons, instantiated bare and bound in the app factory.

Kept in their own module so models and blueprints can import `db` without
importing the factory, which would be circular.
"""

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
