import sys
from pathlib import Path

import pytest
from flask_jwt_extended import create_access_token

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app import config as app_config
from app.extensions import db
from app.models import User


@pytest.fixture()
def app(tmp_path, monkeypatch):
    # Report uploads are deliberately written to a temporary directory so test
    # files cannot leak into the developer's real report store.
    monkeypatch.setattr(app_config, "BASE_DIR", tmp_path)
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(app):
    with app.app_context():
        user = User(email="vitals@example.com", full_name="Vitals Tester")
        user.set_password("not-used-in-this-test")
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=user.id)
    return {"Authorization": f"Bearer {token}"}
