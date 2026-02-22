from flask import (
    Blueprint,
    render_template,
    current_app,
    redirect,
    url_for,
    flash,
    request,
    session
)
from decorators import role_required

courses_bp = Blueprint("courses", __name__, url_prefix="/courses")

# ============ ADMIN - CREATE & MANAGE COURSES ============

@courses_bp.route("/admin/create", methods=["GET", "POST"])
@role_required("admin")
def admin_create_course():
    db = current_app.db

    if request.method == "POST": 
        course_data = {
            "name": request.form.get("name"),
            "code": request.form.get("code"),
            "description": request.form.get("description"),
            "credits": int(request.form.get("credits")),
            "department": request.form.get("department"),
            "max_students": int(request.form.get("max_students"))
        }

        try:
            db.collection("courses").add(course_data)
            flash("Course created successfully", "success")
            return redirect(url_for("courses.admin_courses"))
        except Exception:
            flash("Unable to create course. Please try again.", "danger")

    return render_template("courses/admin_create_course.html")


@courses_bp.route("/admin/list")
@role_required("admin")
def admin_courses():
    db = current_app.db 
    courses = []

    for doc in db.collection("courses").stream():
        data = doc.to_dict()
        data["id"] = doc.id
        courses.append(data)

    return render_template("courses/admin_courses.html", courses=courses)


@courses_bp.route("/admin/<course_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def admin_edit_course(course_id):
    db = current_app.db

    if request.method == "POST":
        course_data = {
            "name": request.form.get("name"),
            "code": request.form.get("code"),
            "description": request.form.get("description"),
            "credits": int(request.form.get("credits")),
            "department": request.form.get("department"),
            "max_students": int(request.form.get("max_students"))
        }

        try:
            db.collection("courses").document(course_id).update(course_data)
            flash("Course updated successfully", "success")
            return redirect(url_for("courses.admin_courses"))
        except Exception:
            flash("Unable to update course.", "danger")

    course_doc = db.collection("courses").document(course_id).get()
    if not course_doc.exists:
        return "Course not found", 404

    course = course_doc.to_dict()
    course["id"] = course_id

    return render_template("courses/admin_edit_course.html", course=course)


@courses_bp.route("/admin/<course_id>/delete", methods=["POST"])
@role_required("admin")
def admin_delete_course(course_id):
    db = current_app.db

    try:
        db.collection("courses").document(course_id).delete()
        flash("Course deleted successfully", "success")
    except Exception:
        flash("Unable to delete course.", "danger")

    return redirect(url_for("courses.admin_courses"))


# ============ LECTURER - COURSE ASSIGNMENT ============

@courses_bp.route("/lecturer/available")
@role_required("lecturer")
def lecturer_available_courses():
    db = current_app.db 
    courses = []

    for doc in db.collection("courses").stream():
        data = doc.to_dict()
        data["id"] = doc.id
        courses.append(data)

    return render_template("courses/lecturer_available_courses.html", courses=courses)


@courses_bp.route("/lecturer/assign/<course_id>", methods=["POST"])
@role_required("lecturer")
def lecturer_assign_course(course_id):
    db = current_app.db
    lecturer_id = session.get("uid")

    try: 
        db.collection("course_lecturers").add({
            "lecturer_id": lecturer_id,
            "course_id": course_id
        })
        flash("Course assigned successfully", "success")
    except Exception:
        flash("Unable to assign course.", "danger")

    return redirect(url_for("courses.lecturer_my_courses"))


@courses_bp.route("/lecturer/my-courses")
@role_required("lecturer")
def lecturer_my_courses():
    db = current_app.db
    lecturer_id = session.get("uid")
    my_courses = []

    assignments = db.collection("course_lecturers").where(
        "lecturer_id", "==", lecturer_id
    ).stream()

    for doc in assignments:
        data = doc.to_dict()
        course_id = data.get("course_id")
        course_doc = db.collection("courses").document(course_id).get()

        if course_doc.exists:
            course = course_doc.to_dict()
            course["id"] = course_id
            course["assignment_id"] = doc.id
            my_courses.append(course)

    return render_template("courses/lecturer_my_courses.html", courses=my_courses)


@courses_bp.route("/lecturer/<assignment_id>/remove", methods=["POST"])
@role_required("lecturer")
def lecturer_remove_course(assignment_id):
    db = current_app.db

    try:
        db.collection("course_lecturers").document(assignment_id).delete()
        flash("Course removed successfully", "success")
    except Exception:
        flash("Unable to remove course.", "danger")

    return redirect(url_for("courses.lecturer_my_courses"))


# ============ STUDENT - ENROLLMENT ============

@courses_bp.route("/student/available")
@role_required("student")
def student_available_courses():
    db = current_app.db 
    courses = []

    for doc in db.collection("courses").stream():
        data = doc.to_dict()
        data["id"] = doc.id
        courses.append(data)

    return render_template("courses/student_available_courses.html", courses=courses)


@courses_bp.route("/student/enroll/<course_id>", methods=["POST"])
@role_required("student")
def student_enroll_course(course_id):
    db = current_app.db
    student_id = session.get("uid")

    try:
        existing = db.collection("student_enrollments") \
            .where("student_id", "==", student_id) \
            .where("course_id", "==", course_id) \
            .stream()

        if list(existing):
            flash("Already enrolled in this course.", "warning")
        else:
            db.collection("student_enrollments").add({
                "student_id": student_id,
                "course_id": course_id
            })
            flash("Enrolled successfully.", "success")
    except Exception:
        flash("Unable to enroll in course.", "danger")

    return redirect(url_for("courses.student_my_courses"))


@courses_bp.route("/student/my-courses")
@role_required("student")
def student_my_courses():
    db = current_app.db
    student_id = session.get("uid")
    my_courses = []

    enrollments = db.collection("student_enrollments").where(
        "student_id", "==", student_id
    ).stream()

    for doc in enrollments:
        data = doc.to_dict()
        course_id = data.get("course_id")
        course_doc = db.collection("courses").document(course_id).get()

        if course_doc.exists:
            course = course_doc.to_dict()
            course["id"] = course_id
            course["enrollment_id"] = doc.id
            my_courses.append(course)

    return render_template("courses/student_my_courses.html", courses=my_courses)


@courses_bp.route("/student/<enrollment_id>/drop", methods=["POST"])
@role_required("student")
def student_drop_course(enrollment_id):
    db = current_app.db

    try:
        db.collection("student_enrollments").document(enrollment_id).delete()
        flash("Course dropped successfully.", "success")
    except Exception:
        flash("Unable to drop course.", "danger")

    return redirect(url_for("courses.student_my_courses")) 