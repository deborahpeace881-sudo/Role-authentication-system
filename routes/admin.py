from flask import (
    Blueprint,
    render_template,
    current_app,
    redirect,
    url_for,
    flash,
    abort,
    request
)
from decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    db = current_app.db

    # Use positional arguments for .where() to avoid ValueError
    students = list(db.collection("users").where("role", "==", "student").stream())
    total_students = len(students)

    lecturers = list(db.collection("users").where("role", "==", "lecturer").stream())
    total_lecturers = len(lecturers)

    requests = list(db.collection("users").where("role", "==", "pending").stream())
    pending_requests = len(requests)

    stats = {
        "total_students": total_students,
        "total_lecturers": total_lecturers,
        "pending_requests": pending_requests
    }

    return render_template("admin/dashboard.html", stats=stats)

@admin_bp.route("/students")
@role_required("admin")
def admin_students():
    db = current_app.db

    students_ref = db.collection("users").where("role", "==", "student").stream()
    students = []

    for doc in students_ref:
        data = doc.to_dict()
        data["uid"] = doc.id   # 👈 THIS IS THE UID
        students.append(data)

    return render_template(
        "admin/admin_students.html",
        students=students
    )

@admin_bp.route("/lecturers")
@role_required("admin")
def admin_lecturers():
    db = current_app.db

    lecturers_ref = db.collection("users").where("role", "==", "lecturer").stream()
    lecturers = []

    for doc in lecturers_ref:
        data = doc.to_dict()
        data["uid"] = doc.id
        lecturers.append(data)

    return render_template(
        "admin/admin_lecturers.html",
        lecturers=lecturers
    )


@admin_bp.route("/requests")
@role_required("admin")
def admin_requests():
    db = current_app.db
    # Fetch all users with role 'pending'
    requests_ref = db.collection("users").where("role", "==", "pending").stream()
    requests = []
    for doc in requests_ref:
        data = doc.to_dict()
        data["uid"] = doc.id
        requests.append(data)
    return render_template("admin/admin_requests.html", requests=requests)

@admin_bp.route("/requests/<request_id>")
@role_required("admin")
def admin_request_profile(request_id):
    db = current_app.db
    user_doc = db.collection("users").document(request_id).get()
    if not user_doc.exists:
        abort(404)
    user = user_doc.to_dict()
    user["id"] = request_id
    return render_template("admin/admin_request_profile.html", request=user, user=user)

@admin_bp.route("/requests/<request_id>/approve", methods=["POST"])
@role_required("admin")
def approve_admin(request_id):
    db = current_app.db
    user_ref = db.collection("users").document(request_id)
    if not user_ref.get().exists:
        abort(404)
    user_ref.update({"role": "admin"})
    flash("Admin request approved", "success")
    return redirect(url_for("admin.admin_requests"))

@admin_bp.route("/requests/<request_id>/reject", methods=["POST"])
@role_required("admin")
def reject_admin(request_id):
    db = current_app.db
    user_ref = db.collection("users").document(request_id)
    if not user_ref.get().exists:
        abort(404)
    user_ref.update({"role": "rejected"})
    flash("Admin request rejected", "warning")
    return redirect(url_for("admin.admin_requests"))


@admin_bp.route("/students/<uid>")
@role_required("admin")
def admin_student_profile(uid):
    db = current_app.db

    student_doc = db.collection("users").document(uid).get()
    if not student_doc.exists:
        return "Student not found", 404

    student = student_doc.to_dict()
    student["uid"] = uid

    return render_template(
        "admin/admin_student_profile.html",
        student=student
    )


@admin_bp.route("/lecturers/<uid>")
@role_required("admin")
def admin_lecturer_profile(uid):
    db = current_app.db

    lecturer_doc = db.collection("users").document(uid).get()
    if not lecturer_doc.exists:
        return "Lecturer not found", 404

    lecturer = lecturer_doc.to_dict()
    lecturer["uid"] = uid

    return render_template(
        "admin/admin_lecturer_profile.html",
        lecturer=lecturer
    )


@admin_bp.route("/students/<uid>/delete", methods=["POST"])
@role_required("admin")
def delete_student(uid):
    db = current_app.db
    db.collection("users").document(uid).delete()
    flash("Student deleted successfully", "success")
    return redirect(url_for("admin.admin_students"))


@admin_bp.route("/lecturers/<uid>/delete", methods=["POST"])
@role_required("admin")
def delete_lecturer(uid):
    db = current_app.db
    db.collection("users").document(uid).delete()
    flash("Lecturer deleted successfully", "success")
    return redirect(url_for("admin.admin_lecturers"))


@admin_bp.route("/create-lecturer", methods=["GET", "POST"])
@role_required("admin")
def create_lecturer():
    if request.method == "POST":
        db = current_app.db
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")
        gender = request.form.get("gender")
        dob = request.form.get("dob")
        
        try:
            # Create Firebase user
            from firebase_admin import auth
            user = auth.create_user(email=email, password=password)
            
            # Store in Firestore
            db.collection("users").document(user.uid).set({
                "email": email,
                "name": name,
                "gender": gender,
                "date_of_birth": dob,
                "role": "lecturer"
            })
            
            flash("Lecturer account created successfully", "success")
            return redirect(url_for("admin.admin_lecturers"))
        except Exception as e:
            flash(f"Error creating account: {str(e)}", "error")
    
    return render_template("admin/create_lecturer.html")


@admin_bp.route("/students/<uid>/results", methods=["GET", "POST"])
@role_required("admin")
def admin_override_results(uid):
    db = current_app.db

    # Get student info
    student_doc = db.collection("users").document(uid).get()
    if not student_doc.exists:
        return "Student not found", 404
    student = student_doc.to_dict()
    student["uid"] = uid

    # Get all scores for this student
    scores_ref = db.collection("scores").where("student_id", "==", uid).stream()
    results = []
    for doc in scores_ref:
        score = doc.to_dict()
        score["id"] = doc.id
        # Get course name
        course_doc = db.collection("courses").document(score.get("course_id")).get()
        score["course_name"] = course_doc.to_dict().get("name") if course_doc.exists else "Unknown"
        results.append(score)

    # Handle override (update) or delete
    if request.method == "POST":
        action = request.form.get("action")
        score_id = request.form.get("score_id")
        if action == "update":
            new_score = request.form.get("new_score")
            db.collection("scores").document(score_id).update({"score": new_score})
            flash("Score updated successfully.", "success")
        elif action == "delete":
            db.collection("scores").document(score_id).delete()
            flash("Score deleted successfully.", "warning")
        return redirect(url_for("admin.admin_override_results", uid=uid))

    return render_template(
        "admin/admin_override_results.html",
        student=student,
        results=results
    )