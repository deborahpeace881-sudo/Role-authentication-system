import os
from flask import Blueprint, render_template, session, current_app, request, redirect, url_for, flash
from werkzeug.utils import secure_filename  # <-- Add this import
from decorators import role_required 

student_bp = Blueprint("student", __name__, url_prefix="/student")

@student_bp.route("/dashboard")
@role_required("student")
def student_dashboard():
    db = current_app.db
    student_id = session.get("uid")
    student_name = session.get("email", "Student")

    # Get enrolled courses
    enrollments = db.collection("student_enrollments").where("student_id", "==", student_id).stream()
    enrolled_courses = []
    for enrollment in enrollments:
        course_id = enrollment.to_dict().get("course_id")
        if course_id:
            course_doc = db.collection("courses").document(course_id).get()
            if course_doc.exists:
                course = course_doc.to_dict()
                course["id"] = course_id
                enrolled_courses.append(course)

    # Example: Count assignments/tests (implement logic as needed)
    assignments_count = 0  # Replace with real count if you have assignments/tests

    return render_template(
        "student/student_dashboard.html",
        student_name=student_name,
        enrolled_courses=enrolled_courses,
        assignments_count=assignments_count
    )

@student_bp.route("/courses", methods=["GET", "POST"])
@role_required("student")
def student_courses():
    db = current_app.db
    student_id = session.get("uid")

    # Handle enroll/unenroll actions
    if request.method == "POST":
        action = request.form.get("action")
        course_id = request.form.get("course_id")
        if action == "enroll":
            # Check if already enrolled
            existing = db.collection("student_enrollments").where("student_id", "==", student_id).where("course_id", "==", course_id).stream()
            if not list(existing):
                db.collection("student_enrollments").add({
                    "student_id": student_id,
                    "course_id": course_id
                })
                flash("Enrolled in course.", "success")
        elif action == "unenroll":
            enrollments = db.collection("student_enrollments").where("student_id", "==", student_id).where("course_id", "==", course_id).stream()
            for doc in enrollments:
                db.collection("student_enrollments").document(doc.id).delete()
                flash("Unenrolled from course.", "success")
        return redirect(url_for("student.student_courses"))

    # Get all courses
    courses_ref = db.collection("courses").stream()
    all_courses = []
    for doc in courses_ref:
        course = doc.to_dict()
        course["id"] = doc.id
        all_courses.append(course)

    # Get enrolled courses
    enrollments = db.collection("student_enrollments").where("student_id", "==", student_id).stream()
    enrolled_course_ids = set()
    for enrollment in enrollments:
        course_id = enrollment.to_dict().get("course_id")
        if course_id:
            enrolled_course_ids.add(course_id)

    return render_template(
        "student/student_courses.html",
        all_courses=all_courses,
        enrolled_course_ids=enrolled_course_ids
    )

@student_bp.route("/materials")
@role_required("student")
def student_materials():
    db = current_app.db
    student_id = session.get("uid")

    # Get enrolled courses
    enrollments = db.collection("student_enrollments").where("student_id", "==", student_id).stream()
    course_names = []
    for enrollment in enrollments:
        course_id = enrollment.to_dict().get("course_id")
        if course_id:
            course_doc = db.collection("courses").document(course_id).get()
            if course_doc.exists:
                course = course_doc.to_dict()
                course_names.append(course.get("name", ""))

    # Get materials for enrolled courses
    materials = []
    if course_names:
        for course_name in course_names:
            mats = db.collection("materials").where("course_name", "==", course_name).stream()
            for mat in mats:
                material = mat.to_dict()
                materials.append(material)

    return render_template(
        "student/student_materials.html",
        materials=materials
    )

@student_bp.route("/assignments")
@role_required("student")
def student_assignments():
    db = current_app.db
    student_id = session.get("uid")

    # Get enrolled courses
    enrollments = db.collection("student_enrollments").where("student_id", "==", student_id).stream()
    course_ids = []
    for enrollment in enrollments:
        course_id = enrollment.to_dict().get("course_id")
        if course_id:
            course_ids.append(course_id)

    # Get assignments/tests for enrolled courses
    assignments = []
    if course_ids:
        for course_id in course_ids:
            course_doc = db.collection("courses").document(course_id).get()
            course_name = course_doc.to_dict().get("name") if course_doc.exists else ""
            assignments_ref = db.collection("assignments").where("course_id", "==", course_id).stream()
            for doc in assignments_ref:
                assignment = doc.to_dict()
                assignment["course_name"] = course_name
                assignments.append(assignment)

    return render_template("student/student_assignments.html", assignments=assignments)

@student_bp.route("/results")
@role_required("student")
def student_results():
    db = current_app.db
    student_id = session.get("uid")

    # Get enrolled courses
    enrollments = db.collection("student_enrollments").where("student_id", "==", student_id).stream()
    course_map = {}
    course_ids = []
    for enrollment in enrollments:
        course_id = enrollment.to_dict().get("course_id")
        if course_id:
            course_doc = db.collection("courses").document(course_id).get()
            if course_doc.exists:
                course = course_doc.to_dict()
                course["id"] = course_id
                course_map[course_id] = course
                course_ids.append(course_id)

    # Get results/scores for this student
    results = []
    if course_ids:
        scores = db.collection("scores").where("student_id", "==", student_id).stream()
        for score_doc in scores:
            score_data = score_doc.to_dict()
            course_id = score_data.get("course_id")
            course = course_map.get(course_id)
            if course:
                results.append({
                    "course_name": course.get("name", "Unknown"),
                    "course_code": course.get("code", ""),
                    "score": score_data.get("score")
                })

    return render_template("student/student_results.html", results=results)

@student_bp.route("/profile", methods=["GET", "POST"])
@role_required("student")
def student_profile():
    db = current_app.db
    student_id = session.get("uid")
    student_doc = db.collection("users").document(student_id).get()
    student = student_doc.to_dict() if student_doc.exists else {}

    # Handle profile picture upload
    if request.method == "POST" and "profile_picture" in request.files:
        file = request.files["profile_picture"]
        if file and file.filename:
            filename = f"{student_id}_profile_{secure_filename(file.filename)}"
            upload_folder = os.path.join("static", "uploads", "profile_pics")
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            # Save the path relative to 'static/' in Firestore
            db.collection("users").document(student_id).update({
                "profile_picture": f"uploads/profile_pics/{filename}"
            })
            flash("Profile picture updated successfully.", "success")
            return redirect(url_for("student.student_profile"))

    return render_template("student/student_profile.html", student=student)

@student_bp.route("/enrolled_courses")
@role_required("student")
def student_enrolled_courses():
    db = current_app.db
    student_id = session.get("uid")
    enrollments = db.collection("student_enrollments").where("student_id", "==", student_id).stream()
    enrolled_courses = []
    for enrollment in enrollments:
        course_id = enrollment.to_dict().get("course_id")
        if course_id:
            course_doc = db.collection("courses").document(course_id).get()
            if course_doc.exists:
                course = course_doc.to_dict()
                course["id"] = course_id
                enrolled_courses.append(course)
    return render_template("student/student_enrolled_courses.html", enrolled_courses=enrolled_courses)
