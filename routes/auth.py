from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from firebase_admin import auth
import requests
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/")

FIREBASE_WEB_API_KEY = os.environ.get("FIREBASE_WEB_API_KEY")


# -----------------------------
# Firebase password verification
# -----------------------------
def verify_password_with_firebase(email, password):
    if not FIREBASE_WEB_API_KEY:
        return False, {"error": {"message": "Missing Firebase Web API Key"}}

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    resp = requests.post(url, json=payload)
    return resp.ok, resp.json()


# -----------------------------
# LOGIN
# -----------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    db = current_app.db

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            print("STEP 1: Login attempt started")
            print("Email:", email)

            ok, data = verify_password_with_firebase(email, password)

            print("STEP 2: Firebase response")
            print("OK:", ok)
            print("DATA:", data)

            if not ok:
                error_message = "Invalid login details."

                if isinstance(data, dict):
                    error = data.get("error")
                    if isinstance(error, dict):
                        error_message = error.get("message", error_message)

                print("STEP 3: Firebase auth failed:", error_message)
                flash(error_message, "danger")
                return render_template("auth/login.html")

            print("STEP 4: Firebase password verified")

            user = auth.get_user_by_email(email)
            print("STEP 5: Firebase user found:", user.uid)

            user_doc = db.collection("users").document(user.uid).get()

            if not user_doc.exists:
                print("STEP 6 ERROR: Firestore user not found")
                flash("User profile not found.", "danger")
                return render_template("auth/login.html")

            user_data = user_doc.to_dict()
            print("STEP 7: Firestore data:", user_data)

            role = user_data.get("role")

            if role == "pending": 
                flash("Your admin account is pending approval.", "warning")
                return render_template("auth/login.html")

            if role == "rejected":
                flash("Your admin account request was rejected.", "danger")
                return render_template("auth/login.html")

            session["uid"] = user.uid 
            session["email"] = user_data.get("email")
            session["role"] = role

            print("STEP 8: Session created, role =", role)

            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif role == "lecturer":
                return redirect(url_for("lecturer.dashboard"))
            elif role == "student":
                return redirect(url_for("student.student_dashboard"))

            print("STEP 9 ERROR: Unknown role")
            flash("Unknown user role.", "danger") 

        except Exception as e:
            print("🔥 LOGIN CRASHED 🔥")
            print("ERROR TYPE:", type(e))
            print("ERROR MESSAGE:", e)

            flash(f"Server error: {e}", "danger")

    return render_template("auth/login.html")


# -----------------------------
# SIGNUP (ONLY ADMIN & STUDENT)
# -----------------------------
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    db = current_app.db

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password")
        role = request.form.get("role")  # admin | student
        gender = request.form.get("gender")
        date_of_birth = request.form.get("date_of_birth")

        if role not in ["admin", "student"]:
            flash("Invalid role selected.", "danger")
            return render_template("auth/signup.html")

        try:
            user = auth.create_user(email=email, password=password) 

            # Admins must be approved
            user_role = "pending" if role == "admin" else "student"

            db.collection("users").document(user.uid).set({
                "email": email,
                "role": user_role,
                "gender": gender,
                "date_of_birth": date_of_birth
            }) 

            if role == "admin":
                flash("Admin account created. Awaiting approval.", "warning")
            else:
                flash("Account created successfully.", "success")

            return redirect(url_for("auth.login"))

        except Exception as e:
            flash("Signup failed. Email may already exist.", "danger")

    return render_template("auth/signup.html")


# -----------------------------
# LOGOUT
# -----------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login")) 