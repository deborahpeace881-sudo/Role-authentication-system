# app.py
from flask import Flask, render_template, redirect, url_for, flash, session, request
from functools import wraps

import firebase_admin
from firebase_admin import credentials, auth, firestore
from firebase_admin._auth_utils import UserNotFoundError

from forms import SignupForm

# Initialize Flask
app = Flask(__name__)
app.secret_key = "supersecretkey"  # replace with env var in production

# Initialize Firebase Admin SDK (ensure firebase_config.json is in project root)
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

# ----------- decorators -----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = session.get("role")
            if not role:
                flash("Please log in to continue.", "danger")
                return redirect(url_for("login"))
            if role != required_role:
                flash("You are not authorized to view that page.", "danger")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ----------- routes -----------
@app.route("/")
def home():
    return "Welcome to the Role-Based Authentication System (JPTS Ibadan case study)."

@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        chosen = form.role.data            # 'student' | 'lecturer' | 'admin'
        gender = form.gender.data
        dob = form.date_of_birth.data

        # Decide final role
        if chosen in ("student", "lecturer"):
            final_role = chosen
            admin_request_doc = None
        else:
            final_role = "pending_admin"
            admin_request_doc = {
                "email": email,
                "requested_role": "admin",
                "status": "pending",
                "created_at": firestore.SERVER_TIMESTAMP
            }

        try:
            # Prevent duplicate accounts
            try:
                auth.get_user_by_email(email)
                flash("An account with that email already exists. Please log in.", "danger")
                return redirect(url_for("signup"))
            except UserNotFoundError:
                pass

            # Create Firebase Auth user
            user = auth.create_user(email=email, password=password)

            # Save profile to Firestore
            profile = {
                "email": email,
                "role": final_role,
                "gender": gender,
                # store as ISO string so it's easy to read; Firestore SERVER_TIMESTAMP added below
                "date_of_birth": dob.isoformat() if dob else None,
                "created_at": firestore.SERVER_TIMESTAMP
            }
            db.collection("users").document(user.uid).set(profile)

            # If admin requested, create admin_requests doc
            if admin_request_doc is not None:
                admin_request_doc["requested_by"] = user.uid
                db.collection("admin_requests").document(user.uid).set(admin_request_doc)
                flash("Account created. Admin request submitted for review.", "success")
            else:
                flash("Account created successfully. Please log in.", "success")

            # Optional: generate email verification link (printed to console)
            try:
                link = auth.generate_email_verification_link(email)
                print("Email verification link:", link)
            except Exception as e:
                print("Could not generate verification link:", e)

            return redirect(url_for("home"))

        except Exception as e:
            print("Signup error:", e)
            flash("Registration failed. Please try again.", "danger")
            return redirect(url_for("signup"))

    return render_template("signup.html", form=form)

# Admin: list pending admin requests
@app.route("/admin/requests")
@login_required
@role_required("admin")
def admin_requests():
    docs = db.collection("admin_requests").where("status", "==", "pending").stream()
    requests = []
    for d in docs:
        doc = d.to_dict()
        doc["uid"] = d.id
        requests.append(doc)
    return render_template("admin_requests.html", requests=requests)

# Admin approve
@app.route("/admin/approve/<uid>", methods=["POST"])
@login_required
@role_required("admin")
def approve_admin(uid):
    try:
        db.collection("users").document(uid).update({"role": "admin"})
        db.collection("admin_requests").document(uid).update({
            "status": "approved",
            "approved_by": session.get("user_id"),
            "approved_at": firestore.SERVER_TIMESTAMP
        })
        flash("User approved as admin.", "success")
    except Exception as e:
        print("Approve error:", e)
        flash("Could not approve user.", "danger")
    return redirect(url_for("admin_requests"))

# Admin reject
@app.route("/admin/reject/<uid>", methods=["POST"])
@login_required
@role_required("admin")
def reject_admin(uid):
    try:
        db.collection("admin_requests").document(uid).update({
            "status": "rejected",
            "rejected_by": session.get("user_id"),
            "rejected_at": firestore.SERVER_TIMESTAMP
        })
        db.collection("users").document(uid).update({"role": "rejected_admin"})
        flash("Admin request rejected.", "info")
    except Exception as e:
        print("Reject error:", e)
        flash("Could not reject request.", "danger")
    return redirect(url_for("admin_requests"))

# Placeholder login/logout/dashboard (implement login next)
@app.route("/login")
def login():
    return "Login page (to be implemented)."

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("home"))

@app.route("/student_dashboard")
@login_required
@role_required("student")
def student_dashboard():
    return "Student dashboard (protected)."

@app.route("/lecturer_dashboard")
@login_required
@role_required("lecturer")
def lecturer_dashboard():
    return "Lecturer dashboard (protected)."

@app.route("/admin_dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    return "Admin dashboard (protected)."

if __name__ == "__main__":
    app.run(debug=True)
