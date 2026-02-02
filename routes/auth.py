from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from firebase_admin import auth
import requests
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/")

FIREBASE_WEB_API_KEY = os.environ.get("FIREBASE_WEB_API_KEY")  # Set this in your environment

def verify_password_with_firebase(email, password):
    if not FIREBASE_WEB_API_KEY:
        return False, {"error": "Missing Firebase Web API Key"}
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    resp = requests.post(url, json=payload)
    return resp.ok, resp.json() if resp.ok else resp.json()

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    db = current_app.db

    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        try:
            flash(f"DEBUG: Attempting login for {email}", "info")
            ok, data = verify_password_with_firebase(email, password)

            if not ok:
                error_message = data.get("error", {}).get("message", "Invalid login details.")
                flash(f"DEBUG: Firebase password check failed: {error_message}", "warning")
                if error_message == "Missing Firebase Web API Key":
                    flash("Server error: Firebase Web API Key not set.", "danger")
                elif error_message == "EMAIL_NOT_FOUND":
                    flash("No account found with this email.", "danger")
                elif error_message == "INVALID_PASSWORD":
                    flash("Incorrect password.", "danger")
                else:
                    flash("Invalid login details.", "danger")
                return render_template("auth/login.html")

            flash("DEBUG: Firebase password check passed", "info")
            user = auth.get_user_by_email(email)
            user_doc = db.collection("users").document(user.uid).get()

            if not user_doc.exists:
                flash("DEBUG: User profile not found in Firestore.", "warning")
                flash("User profile not found.", "danger")
                return redirect(url_for("auth.login"))

            user_data = user_doc.to_dict()
            flash(f"DEBUG: User Firestore data: {user_data}", "info")

            # Block login for pending or rejected admins
            if user_data["role"] == "pending":
                flash("Your admin account is pending approval.", "warning")
                return render_template("auth/login.html")
            elif user_data["role"] == "rejected":
                flash("Your admin account request was rejected.", "danger")
                return render_template("auth/login.html")

            session["uid"] = user.uid
            session["email"] = user_data["email"]
            session["role"] = user_data["role"]

            # Redirect by role
            if user_data["role"] == "admin":
                flash("DEBUG: Redirecting to admin dashboard", "info")
                return redirect(url_for("admin.dashboard"))
            elif user_data["role"] == "lecturer":
                flash("DEBUG: Redirecting to lecturer dashboard", "info")
                return redirect(url_for("lecturer.dashboard"))
            elif user_data["role"] == "student":
                flash("DEBUG: Redirecting to student dashboard", "info")
                return redirect(url_for("student.student_dashboard"))
            else:
                flash(f"DEBUG: Unknown user role: {user_data['role']}", "warning")
                flash("Unknown user role.", "danger")
                return render_template("auth/login.html")

        except Exception as e:
            flash(f"DEBUG: Exception occurred: {str(e)}", "danger")
            flash("Invalid login details.", "danger")

    return render_template("auth/login.html")



@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    db = current_app.db

    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        role = request.form.get("role")
        gender = request.form.get("gender")
        date_of_birth = request.form.get("date_of_birth")

        try:
            flash(f"DEBUG: Creating user {email} with role {role}", "info")
            user = auth.create_user(email=email, password=password)
            flash(f"DEBUG: Firebase user created: {user.uid}", "info")

            # Set role to 'pending' for new admins, otherwise use selected role
            user_role = "pending" if role == "admin" else role

            db.collection("users").document(user.uid).set({
                "email": email,
                "role": user_role,
                "gender": gender,
                "date_of_birth": date_of_birth
            })
            flash("DEBUG: User profile created in Firestore", "info")

            flash("Account created successfully.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            flash(f"DEBUG: Signup exception: {str(e)}", "danger")
            flash("Signup failed.", "danger")

    return render_template("auth/signup.html")



@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))
