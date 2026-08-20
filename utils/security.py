from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

hash_password = generate_password_hash
verify_password = check_password_hash


def login_required(role):
    """Restrict a route to a signed-in user of a specific role.
    role is one of: 'institution', 'principal', 'student', 'parent'
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                flash("Please log in to continue.", "error")
                return redirect(url_for("auth.login"))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
