from flask import Blueprint, render_template, session, current_app, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
import csv
from flask import Response

lecturer_bp = Blueprint("lecturer", __name__, url_prefix="/lecturer")

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
UPLOAD_FOLDER = "uploads/materials"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@lecturer_bp.route("/dashboard")
def dashboard():
    db = current_app.db
    lecturer_email = session.get("email", "Lecturer")
    lecturer_id = session.get("uid")  # assuming uid is stored in session at login

    assigned_courses = []
    if lecturer_id:
        # Fetch assigned courses for this lecturer
        assignments = db.collection("course_lecturers").where("lecturer_id", "==", lecturer_id).stream()
        for doc in assignments:
            course_id = doc.to_dict().get("course_id")
            if course_id:
                course_doc = db.collection("courses").document(course_id).get()
                if course_doc.exists:
                    course = course_doc.to_dict()
                    course["id"] = course_id
                    assigned_courses.append(course)

    return render_template(
        "lecturer/dashboard.html",
        lecturer_name=lecturer_email,
        assigned_courses=assigned_courses
    )

@lecturer_bp.route("/courses")
def courses():
    db = current_app.db
    lecturer_id = session.get("uid")
    assigned_courses = []
    if lecturer_id:
        assignments = db.collection("course_lecturers").where("lecturer_id", "==", lecturer_id).stream()
        for doc in assignments:
            course_id = doc.to_dict().get("course_id")
            if course_id:
                course_doc = db.collection("courses").document(course_id).get()
                if course_doc.exists:
                    course = course_doc.to_dict()
                    course["id"] = course_id
                    assigned_courses.append(course)
    return render_template("lecturer/courses.html", assigned_courses=assigned_courses)

@lecturer_bp.route("/materials", methods=["GET", "POST"])
def materials():
    db = current_app.db
    lecturer_id = session.get("uid")
    lecturer_email = session.get("email", "Lecturer")

    # Fetch courses assigned to this lecturer for the dropdown
    assigned_courses = []
    if lecturer_id:
        assignments = db.collection("course_lecturers").where("lecturer_id", "==", lecturer_id).stream()
        for doc in assignments:
            course_id = doc.to_dict().get("course_id")
            if course_id:
                course_doc = db.collection("courses").document(course_id).get()
                if course_doc.exists:
                    course = course_doc.to_dict()
                    course["id"] = course_id
                    assigned_courses.append(course)

    # Handle file upload
    if request.method == "POST":
        file = request.files.get("material_file")
        course_name = request.form.get("course_name")
        if file and allowed_file(file.filename) and course_name:
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            # Store metadata in Firestore
            db.collection("materials").add({
                "lecturer_id": lecturer_id,
                "filename": filename,
                "filepath": filepath,
                "course_name": course_name
            })
            flash("Material uploaded successfully.", "success")
            return redirect(url_for("lecturer.materials"))
        else:
            flash("Invalid file type or course not selected.", "danger")

    # List uploaded materials for this lecturer
    materials_ref = db.collection("materials").where("lecturer_id", "==", lecturer_id).stream()
    materials = []
    for doc in materials_ref:
        data = doc.to_dict()
        data["url"] = url_for("lecturer.download_material", filename=data["filename"])
        materials.append(data)

    return render_template(
        "lecturer/lecturer_materials.html",
        materials=materials,
        courses=assigned_courses
    )

@lecturer_bp.route("/materials/download/<filename>")
def download_material(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@lecturer_bp.route("/students")
def students():
    db = current_app.db
    lecturer_id = session.get("uid")
    students = []

    if lecturer_id:
        # Get all courses assigned to this lecturer
        assignments = db.collection("course_lecturers").where("lecturer_id", "==", lecturer_id).stream()
        course_map = {}
        course_ids = []
        for doc in assignments:
            course_id = doc.to_dict().get("course_id")
            if course_id:
                course_doc = db.collection("courses").document(course_id).get()
                if course_doc.exists:
                    course = course_doc.to_dict()
                    course["id"] = course_id
                    course_map[course_id] = course.get("name", "Unknown Course")
                    course_ids.append(course_id)

        # For each course, get enrolled students
        for course_id in course_ids:
            enrollments = db.collection("student_enrollments").where("course_id", "==", course_id).stream()
            for enrollment in enrollments:
                student_id = enrollment.to_dict().get("student_id")
                if student_id:
                    student_doc = db.collection("users").document(student_id).get()
                    if student_doc.exists:
                        student_data = student_doc.to_dict()
                        students.append({
                            "course_name": course_map.get(course_id, "Unknown Course"),
                            "student_name": student_data.get("name", "Unknown"),
                            "student_email": student_data.get("email", "Unknown"),
                            "student_id": student_id,
                            "course_id": course_id
                        })

    return render_template("lecturer/lecturer_students.html", students=students)

@lecturer_bp.route("/results", methods=["GET", "POST"])
def results():
    db = current_app.db
    lecturer_id = session.get("uid")
    selected_course_id = request.args.get("course_id")
    courses = []
    results = []

    # Get all courses assigned to this lecturer
    assignments = db.collection("course_lecturers").where("lecturer_id", "==", lecturer_id).stream()
    course_ids = []
    for doc in assignments:
        course_id = doc.to_dict().get("course_id")
        if course_id:
            course_doc = db.collection("courses").document(course_id).get()
            if course_doc.exists:
                course = course_doc.to_dict()
                course["id"] = course_id
                courses.append(course)
                course_ids.append(course_id)

    # Filter results by selected course or show all
    score_query = db.collection("scores")
    if selected_course_id:
        score_query = score_query.where("course_id", "==", selected_course_id)
        filtered_course_ids = [selected_course_id]
    else:
        filtered_course_ids = course_ids

    scores = score_query.stream()
    for score_doc in scores:
        score_data = score_doc.to_dict()
        if score_data.get("course_id") in filtered_course_ids:
            student_id = score_data.get("student_id")
            student_doc = db.collection("users").document(student_id).get()
            student = student_doc.to_dict() if student_doc.exists else {}
            results.append({
                "student_name": student.get("name", "Unknown"),
                "student_email": student.get("email", "Unknown"),
                "score": score_data.get("score")
            })

    return render_template(
        "lecturer/lecturer_results.html",
        courses=courses,
        results=results,
        selected_course_id=selected_course_id
    )

@lecturer_bp.route("/profile", methods=["GET", "POST"])
def profile():
    db = current_app.db
    lecturer_id = session.get("uid")
    lecturer_doc = db.collection("users").document(lecturer_id).get()
    lecturer = lecturer_doc.to_dict() if lecturer_doc.exists else {}

    # Handle profile picture upload
    if request.method == "POST" and "profile_picture" in request.files:
        file = request.files["profile_picture"]
        if file and file.filename:
            filename = f"{lecturer_id}_profile_{secure_filename(file.filename)}"
            upload_folder = os.path.join("static", "uploads", "profile_pics")
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            # Save the path relative to 'static/' in Firestore
            db.collection("users").document(lecturer_id).update({
                "profile_picture": f"uploads/profile_pics/{filename}"
            })
            flash("Profile picture updated successfully.", "success")
            return redirect(url_for("lecturer.profile"))

    return render_template("lecturer/lecturer_profile.html", lecturer=lecturer)

@lecturer_bp.route("/enter_score/<student_id>/<course_id>", methods=["GET", "POST"])
def enter_score(student_id, course_id):
    db = current_app.db

    # Fetch student and course info
    student_doc = db.collection("users").document(student_id).get()
    course_doc = db.collection("courses").document(course_id).get()
    student = student_doc.to_dict() if student_doc.exists else {}
    course = course_doc.to_dict() if course_doc.exists else {}

    # Fetch or initialize score
    score_query = db.collection("scores") \
        .where("student_id", "==", student_id) \
        .where("course_id", "==", course_id) \
        .limit(1).stream()
    score_doc = next(score_query, None)
    score_data = score_doc.to_dict() if score_doc else {}

    if request.method == "POST":
        new_score = request.form.get("score")
        if score_doc:
            db.collection("scores").document(score_doc.id).update({"score": new_score})
            flash("Score updated successfully and student result updated.", "success")
        else:
            db.collection("scores").add({
                "student_id": student_id,
                "course_id": course_id,
                "score": new_score
            })
            flash("Score entered successfully and student result updated.", "success")
        # Redirect to results page after saving
        return redirect(url_for("lecturer.results"))

    return render_template(
        "lecturer/enter_score.html",
        student=student,
        course=course,
        score=score_data.get("score")
    )

@lecturer_bp.route("/export_results")
def export_results():
    db = current_app.db
    lecturer_id = session.get("uid")
    # Get all courses assigned to this lecturer
    assignments = db.collection("course_lecturers").where("lecturer_id", "==", lecturer_id).stream()
    course_ids = [doc.to_dict().get("course_id") for doc in assignments if doc.to_dict().get("course_id")]

    # Get all scores for these courses
    scores = db.collection("scores").stream()
    rows = [("Course", "Student Name", "Student Email", "Score")]
    for score_doc in scores:
        score_data = score_doc.to_dict()
        if score_data.get("course_id") in course_ids:
            student_id = score_data.get("student_id")
            course_id = score_data.get("course_id")
            student_doc = db.collection("users").document(student_id).get()
            course_doc = db.collection("courses").document(course_id).get()
            student = student_doc.to_dict() if student_doc.exists else {}
            course = course_doc.to_dict() if course_doc.exists else {}
            rows.append((
                course.get("name", "Unknown"),
                student.get("name", "Unknown"),
                student.get("email", "Unknown"),
                score_data.get("score", "")
            ))

    def generate():
        for row in rows:
            yield ','.join([str(item) for item in row]) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=results.csv"})

@lecturer_bp.route("/test_assignment", methods=["GET", "POST"])
def test_assignment():
    db = current_app.db
    lecturer_id = session.get("uid")

    # Fetch courses assigned to this lecturer for the dropdown
    assigned_courses = []
    if lecturer_id:
        assignments = db.collection("course_lecturers").where("lecturer_id", "==", lecturer_id).stream()
        for doc in assignments:
            course_id = doc.to_dict().get("course_id")
            if course_id:
                course_doc = db.collection("courses").document(course_id).get()
                if course_doc.exists:
                    course = course_doc.to_dict()
                    course["id"] = course_id
                    assigned_courses.append(course)

    # Handle assignment/test creation
    if request.method == "POST":
        course_id = request.form.get("course")
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        form_link = request.form.get("form_link")
        # Get course name for display
        course_name = ""
        for c in assigned_courses:
            if c["id"] == course_id:
                course_name = c["name"]
                break
        if course_id and title and description and due_date and form_link:
            db.collection("assignments").add({
                "lecturer_id": lecturer_id,
                "course_id": course_id,
                "course_name": course_name,
                "title": title,
                "description": description,
                "due_date": due_date,
                "form_link": form_link
            })
            flash("Assignment/Test created successfully.", "success")
            return redirect(url_for("lecturer.test_assignment"))
        else:
            flash("All fields are required.", "danger")

    # List assignments/tests created by this lecturer
    assignments_ref = db.collection("assignments").where("lecturer_id", "==", lecturer_id).stream()
    assignments = []
    for doc in assignments_ref:
        assignment = doc.to_dict()
        assignments.append(assignment)

    return render_template(
        "lecturer/lecturer_test_assingment.html",
        courses=assigned_courses,
        assignments=assignments
    )
