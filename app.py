import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import firebase_admin 
from firebase_admin import credentials, auth, firestore 
from functools import wraps 

app = Flask(__name__) 
app.secret_key = "supersecretkey"

# ---------------- FIREBASE INIT ----------------
if os.environ.get("FIREBASE_CONFIG"):
    # Render / Production
    firebase_config = json.loads(os.environ.get("FIREBASE_CONFIG"))
    cred = credentials.Certificate(firebase_config)
else:
    # Local development
    cred = credentials.Certificate("firebase_config.json")

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()



# 4️⃣ HELPER FUNCTIONS / DECORATORS  👈 (VERY IMPORTANT)
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "uid" not in session:
                flash("Please login first.", "danger")
                return redirect(url_for("login"))

            if session.get("role") not in allowed_roles:
                flash("Unauthorized access.", "danger")
                return redirect(url_for("login"))

            return f(*args, **kwargs)
        return wrapped
    return decorator



# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        role = request.form.get("role")
        gender = request.form.get("gender")
        dob = request.form.get("dob")

        if not all([email, password, role, gender, dob]):
            flash("All fields are required.", "danger")
            return redirect(url_for("signup"))

        try:
            # Check if user already exists
            try:
                auth.get_user_by_email(email)
                flash("Email already registered.", "danger")
                return redirect(url_for("signup"))
            except:
                pass

            # Handle admin request
            if role == "admin":
                final_role = "pending_admin"
            else:
                final_role = role

            # Create Firebase Auth user
            user = auth.create_user(email=email, password=password)

            # Save user data to Firestore
            db.collection("users").document(user.uid).set({
                "email": email,
                "role": final_role,
                "gender": gender,
                "date_of_birth": dob
            })

            # Admin request record
            if role == "admin":
                db.collection("admin_requests").document(user.uid).set({
                    "email": email,
                    "status": "pending"
                })
                flash("Admin request submitted. Await approval.", "success")
            else:
                flash("Account created successfully. Please login.", "success")

            return redirect(url_for("login"))

        except Exception as e:
            print(e)
            flash("Signup failed. Try again.", "danger")
            return redirect(url_for("signup"))

    return render_template("signup.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()

        try:
            # Check if user exists in Firebase Authentication
            user = auth.get_user_by_email(email)

            # Fetch user profile from Firestore
            user_doc = db.collection("users").document(user.uid).get()
            if not user_doc.exists:
                flash("User profile not found.", "danger")
                return redirect(url_for("login"))

            user_data = user_doc.to_dict()

            # Create session
            session["uid"] = user.uid
            session["email"] = user_data["email"]
            session["role"] = user_data["role"]

            # Redirect based on role
            if user_data["role"] == "student":
                return redirect(url_for("student_dashboard"))

            elif user_data["role"] == "lecturer":
                return redirect(url_for("lecturer_dashboard"))

            elif user_data["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            elif user_data["role"] == "pending_admin":
                flash("Admin approval pending.", "info")
                return redirect(url_for("login"))

            else:
                flash("Unauthorized role.", "danger")
                return redirect(url_for("login"))

        except auth.UserNotFoundError:
            flash("Account not found.", "danger")
            return redirect(url_for("login"))

        except Exception as e:
            print("Login error:", e)
            flash("Login failed. Try again.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


# ---------------- DASHBOARDS ----------------
@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")



@app.route("/student/dashboard")
@role_required("student")
def student_dashboard():
    return "Student Dashboard – Login successful"


@app.route("/lecturer/dashboard")
@role_required("lecturer", "admin")
def lecturer_dashboard():
    return "Lecturer Dashboard – Login successful"


@app.route("/admin/students")
@role_required("admin")
def admin_students():
    students_ref = db.collection("users").where("role", "==", "student").stream()

    students = []
    for s in students_ref:
        data = s.to_dict()
        data["uid"] = s.id
        students.append(data)

    return render_template("admin_students.html", students=students)


@app.route("/admin/student/<uid>")
@role_required("admin")
def admin_student_profile(uid):
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        flash("Student not found", "danger")
        return redirect(url_for("admin_students"))

    student = doc.to_dict()
    return render_template("admin_student_profile.html", student=student)



@app.route("/admin/lecturers")
@role_required("admin")
def admin_lecturers():
    lecturers_ref = db.collection("users").where("role", "==", "lecturer").stream()

    lecturers = []
    for l in lecturers_ref:
        data = l.to_dict()
        data["uid"] = l.id
        lecturers.append(data)

    return render_template("admin_lecturers.html", lecturers=lecturers)


@app.route("/admin/lecturer/<uid>")
@role_required("admin")
def admin_lecturer_profile(uid):
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        flash("Lecturer not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    lecturer = doc.to_dict()
    lecturer["uid"] = uid
    return render_template("admin_lecturer_profile.html", lecturer=lecturer)



@app.route("/admin/requests") 
@role_required("admin")
def admin_requests():
    requests_ref = db.collection("admin_requests").stream()

    requests = []
    for r in requests_ref:
        data = r.to_dict()
        data["uid"] = r.id
        requests.append(data)

    return render_template("admin_request.html", requests=requests)


@app.route("/admin/request/<uid>")
@role_required("admin")
def admin_request_profile(uid):
    user_doc = db.collection("users").document(uid).get()
    if not user_doc.exists:
        flash("User not found.", "danger")
        return redirect(url_for("admin_requests"))

    user = user_doc.to_dict()
    user["uid"] = uid
    return render_template("admin_request_profile.html", user=user)




@app.route("/admin/approve/<uid>", methods=["POST"])
@role_required("admin") 
def approve_admin(uid):
    db.collection("users").document(uid).update({"role": "admin"})
    db.collection("admin_requests").document(uid).update({"status": "approved"})
    flash("Admin approved", "success")
    return redirect(url_for("admin_requests"))


@app.route("/admin/reject/<uid>", methods=["POST"])
@role_required("admin") 
def reject_admin(uid):
    db.collection("admin_requests").document(uid).update({"status": "rejected"})
    flash("Admin rejected", "danger")
    return redirect(url_for("admin_requests"))





# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
