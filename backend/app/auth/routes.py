"""Authentication endpoints: register, login, refresh, me.

Response shape is uniform so the frontend has one thing to parse:
  success -> {"data": {...}}
  failure -> {"message": "...", "errors": {"field": "..."}}
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User
from .schemas import validate_login, validate_registration

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Pre-computed so the "no such user" branch of login does the same scrypt work
# as the real branch. Without this, response latency tells an attacker which
# emails are registered.
_DUMMY_HASH = generate_password_hash("timing-equalisation-placeholder", method="scrypt")


def _issue_tokens(user):
    return {
        "accessToken": create_access_token(identity=user.id),
        "refreshToken": create_refresh_token(identity=user.id),
    }


@bp.post("/register")
def register():
    data, errors = validate_registration(request.get_json(silent=True))
    if errors:
        return jsonify({"message": "Please correct the highlighted fields.",
                        "errors": errors}), 400

    email = User.normalize_email(data["email"])

    # Cheap pre-check for the common case; the unique constraint below is what
    # actually guarantees correctness under concurrent signups.
    if db.session.query(User.id).filter_by(email=email).first():
        return jsonify({
            "message": "An account with this email already exists.",
            "errors": {"email": "This email is already registered."},
        }), 409

    user = User(email=email, full_name=data["full_name"], phone=data.get("phone"))
    user.set_password(data["password"])

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Lost the race between the pre-check and the commit.
        db.session.rollback()
        return jsonify({
            "message": "An account with this email already exists.",
            "errors": {"email": "This email is already registered."},
        }), 409

    # Only consent scopes are created for a new account. A new user has no
    # clinical data because they have not entered any — the app shows empty
    # states until they do, rather than inventing readings to fill them.
    from ..seed import provision_consent

    provision_consent(user)

    return jsonify({"data": {"user": user.to_dict(), **_issue_tokens(user)}}), 201


@bp.post("/login")
def login():
    data, errors = validate_login(request.get_json(silent=True))
    if errors:
        return jsonify({"message": "Please correct the highlighted fields.",
                        "errors": errors}), 400

    user = db.session.query(User).filter_by(
        email=User.normalize_email(data["email"])
    ).first()

    if user is None:
        # Burn equivalent CPU, then fail identically to a wrong password.
        check_password_hash(_DUMMY_HASH, data["password"])
        return jsonify({"message": "Incorrect email or password."}), 401

    if not user.check_password(data["password"]):
        return jsonify({"message": "Incorrect email or password."}), 401

    if not user.is_active:
        return jsonify({"message": "This account has been deactivated."}), 403

    return jsonify({"data": {"user": user.to_dict(), **_issue_tokens(user)}}), 200


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return jsonify({"message": "Account is no longer active."}), 401
    return jsonify({"data": {"accessToken": create_access_token(identity=user.id)}}), 200


@bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, get_jwt_identity())
    if user is None:
        return jsonify({"message": "Account not found."}), 404
    return jsonify({"data": {"user": user.to_dict()}}), 200
