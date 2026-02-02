from functools import wraps
from flask import session, abort

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get("role")
            if user_role != required_role:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
