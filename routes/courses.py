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
    if request.method == "POST":
        db = current_app.db
        
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
        except Exception as e:
            flash(f"Error creating course: {str(e)}", "error")
    
    return render_template("courses/admin_create_course.html")


@courses_bp.route("/admin/list")
@role_required("admin")
def admin_courses():
    db = current_app.db
    
    courses_ref = db.collection("courses").stream()
    courses = []
    
    for doc in courses_ref:
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
        except Exception as e:
            flash(f"Error updating course: {str(e)}", "error")
    
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
    except Exception as e:
        flash(f"Error deleting course: {str(e)}", "error")
    
    return redirect(url_for("courses.admin_courses"))


# ============ LECTURER - SELECT & MANAGE COURSES ============

@courses_bp.route("/lecturer/available")
@role_required("lecturer")
def lecturer_available_courses():
    db = current_app.db
    user_id = session.get("uid")  # Use session to get current lecturer's ID

    # Get all courses
    courses_ref = db.collection("courses").stream()
    courses = []
    for doc in courses_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        courses.append(data)

    return render_template("courses/lecturer_available_courses.html", courses=courses, user_id=user_id)


@courses_bp.route("/lecturer/assign/<course_id>", methods=["POST"])
@role_required("lecturer")
def lecturer_assign_course(course_id):
    db = current_app.db
    user_id = request.form.get("user_id")
    
    try:
        # Add lecturer to course
        db.collection("course_lecturers").add({
            "lecturer_id": user_id,
            "course_id": course_id
        })
        flash("Course assigned successfully", "success")
    except Exception as e:
        flash(f"Error assigning course: {str(e)}", "error")
    
    return redirect(url_for("courses.lecturer_my_courses", user_id=user_id))


@courses_bp.route("/lecturer/my-courses")
@role_required("lecturer")
def lecturer_my_courses():
    db = current_app.db
    user_id = request.args.get("user_id") or "current_user"
    
    # Get courses assigned to this lecturer
    lecturers_ref = db.collection("course_lecturers").where("lecturer_id", "==", user_id).stream()
    my_courses = []
    
    for doc in lecturers_ref:
        data = doc.to_dict()
        course_id = data["course_id"]
        course_doc = db.collection("courses").document(course_id).get()
        
        if course_doc.exists:
            course_data = course_doc.to_dict()
            course_data["id"] = course_id
            course_data["assignment_id"] = doc.id
            my_courses.append(course_data)
    
    return render_template("courses/lecturer_my_courses.html", courses=my_courses)


@courses_bp.route("/lecturer/<assignment_id>/remove", methods=["POST"])
@role_required("lecturer")
def lecturer_remove_course(assignment_id):
    db = current_app.db
    
    try:
        db.collection("course_lecturers").document(assignment_id).delete()
        flash("Course removed successfully", "success")
    except Exception as e:
        flash(f"Error removing course: {str(e)}", "error")
    
    return redirect(url_for("courses.lecturer_my_courses"))


# ============ STUDENT - VIEW & ENROLL IN COURSES ============

@courses_bp.route("/student/available")
@role_required("student")
def student_available_courses():
    db = current_app.db
    
    # Get all courses
    courses_ref = db.collection("courses").stream()
    courses = []
    
    for doc in courses_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        courses.append(data)
    
    return render_template("courses/student_available_courses.html", courses=courses)


@courses_bp.route("/student/enroll/<course_id>", methods=["POST"])
@role_required("student")
def student_enroll_course(course_id):
    db = current_app.db
    user_id = request.form.get("user_id")
    
    try:
        # Check if already enrolled
        existing = db.collection("student_enrollments").where("student_id", "==", user_id).where("course_id", "==", course_id).stream()
        if list(existing):
            flash("Already enrolled in this course", "warning")
        else:
            db.collection("student_enrollments").add({
                "student_id": user_id,
                "course_id": course_id
            })
            flash("Enrolled successfully", "success")
    except Exception as e:
        flash(f"Error enrolling: {str(e)}", "error")
    
    return redirect(url_for("courses.student_my_courses", user_id=user_id))


@courses_bp.route("/student/my-courses")
@role_required("student")
def student_my_courses():
    db = current_app.db
    user_id = request.args.get("user_id") or "current_user"
    
    # Get courses enrolled by this student
    enrollments_ref = db.collection("student_enrollments").where("student_id", "==", user_id).stream()
    my_courses = []
    
    for doc in enrollments_ref:
        data = doc.to_dict()
        course_id = data["course_id"]
        course_doc = db.collection("courses").document(course_id).get()
        
        if course_doc.exists:
            course_data = course_doc.to_dict()
            course_data["id"] = course_id
            course_data["enrollment_id"] = doc.id
            my_courses.append(course_data)
    
    return render_template("courses/student_my_courses.html", courses=my_courses)


@courses_bp.route("/student/<enrollment_id>/drop", methods=["POST"])
@role_required("student")
def student_drop_course(enrollment_id):
    db = current_app.db
    
    try:
        db.collection("student_enrollments").document(enrollment_id).delete()
        flash("Course dropped successfully", "success")
    except Exception as e:
        flash(f"Error dropping course: {str(e)}", "error")
    
    return redirect(url_for("courses.student_my_courses"))
