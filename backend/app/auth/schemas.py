"""Request validation for the auth endpoints.

Hand-rolled rather than marshmallow/pydantic: this is the hand-engineered auth
core, and an explicit, readable validator is easier to security-review than a
declarative schema whose coercion rules live in a dependency.

Every validator returns (cleaned_value, error_message). Callers collect errors
into a field->message dict so the frontend can render them per-input.
"""

from email_validator import EmailNotValidError, validate_email

# NIST SP 800-63B favours length over composition rules. 10 is above the
# recommended 8 floor given this is health data; the cap exists because scrypt
# cost scales with input and an unbounded password is a cheap DoS.
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 120


def validate_registration(payload):
    """Validate a registration body. Returns (data, errors)."""
    if not isinstance(payload, dict):
        return None, {"_": "Request body must be a JSON object."}

    errors = {}
    data = {}

    full_name = (payload.get("fullName") or "").strip()
    if not full_name:
        errors["fullName"] = "Please enter your full name."
    elif len(full_name) < NAME_MIN_LENGTH:
        errors["fullName"] = "Name must be at least 2 characters."
    elif len(full_name) > NAME_MAX_LENGTH:
        errors["fullName"] = "Name must be under 120 characters."
    else:
        data["full_name"] = full_name

    email_raw = (payload.get("email") or "").strip()
    if not email_raw:
        errors["email"] = "Please enter your email address."
    else:
        try:
            # check_deliverability=False: no DNS lookup on the request path.
            # Syntax correctness is what we need here; bounce handling belongs
            # to the (not yet built) verification-email flow.
            result = validate_email(email_raw, check_deliverability=False)
            data["email"] = result.normalized.lower()
        except EmailNotValidError:
            errors["email"] = "Please enter a valid email address."

    password = payload.get("password") or ""
    if not password:
        errors["password"] = "Please choose a password."
    elif len(password) < PASSWORD_MIN_LENGTH:
        errors["password"] = f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    elif len(password) > PASSWORD_MAX_LENGTH:
        errors["password"] = f"Password must be under {PASSWORD_MAX_LENGTH} characters."
    elif password.strip() == "":
        errors["password"] = "Password cannot be only whitespace."
    else:
        data["password"] = password

    phone = (payload.get("phone") or "").strip()
    if phone:
        digits = phone.lstrip("+").replace(" ", "").replace("-", "")
        if not digits.isdigit() or not (7 <= len(digits) <= 15):
            errors["phone"] = "Please enter a valid phone number."
        else:
            data["phone"] = phone
    else:
        data["phone"] = None

    return (data, errors) if not errors else (None, errors)


def validate_login(payload):
    """Validate a login body. Deliberately lenient — no format rules on the
    password, since an old account may predate any policy change."""
    if not isinstance(payload, dict):
        return None, {"_": "Request body must be a JSON object."}

    errors = {}
    data = {}

    email = (payload.get("email") or "").strip().lower()
    if not email:
        errors["email"] = "Please enter your email address."
    else:
        data["email"] = email

    password = payload.get("password") or ""
    if not password:
        errors["password"] = "Please enter your password."
    else:
        data["password"] = password

    return (data, errors) if not errors else (None, errors)
