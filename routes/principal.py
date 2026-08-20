import json
from datetime import date
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from db import query_all, query_one, execute
from utils.security import login_required
from utils.ai import generate_exam_questions, dashboard_chatbot_reply

principal_bp = Blueprint("principal", __name__, url_prefix="/principal")


@principal_bp.route("/dashboard")
@login_required("principal")
def dashboard():
    principal = query_one("SELECT * FROM principals WHERE id=%s", (session["user_pk"],))
    students = query_all(
        "SELECT * FROM students WHERE institution_id=%s ORDER BY class_name, full_name",
        (principal["institution_id"],),
    )
    exams = query_all(
        "SELECT * FROM exams WHERE institution_id=%s ORDER BY created_at DESC",
        (principal["institution_id"],),
    )
    today = date.today().isoformat()
    return render_template(
        "dashboard_principal.html", principal=principal, students=students, exams=exams, today=today
    )


@principal_bp.route("/attendance/mark", methods=["POST"])
@login_required("principal")
def mark_attendance():
    principal_pk = session["user_pk"]
    attendance_date = request.form["attendance_date"]
    student_ids = request.form.getlist("present_student_ids")  # checked = present
    all_student_ids = request.form.getlist("all_student_ids")

    for sid in all_student_ids:
        status = "present" if sid in student_ids else "absent"
        execute(
            "INSERT INTO attendance (student_id, attendance_date, status, marked_by) "
            "VALUES (%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE status=VALUES(status), marked_by=VALUES(marked_by)",
            (sid, attendance_date, status, principal_pk),
        )
    flash("Attendance saved.", "success")
    return redirect(url_for("principal.dashboard"))


@principal_bp.route("/exam/create", methods=["POST"])
@login_required("principal")
def create_exam():
    principal = query_one("SELECT * FROM principals WHERE id=%s", (session["user_pk"],))
    subject = request.form["subject"].strip()
    topic = request.form["topic"].strip()
    difficulty = request.form.get("difficulty", "medium")
    num_questions = int(request.form.get("num_questions", 5))

    questions = generate_exam_questions(subject, topic, difficulty, num_questions)

    execute(
        "INSERT INTO exams (institution_id, subject, topic, difficulty, questions_json) "
        "VALUES (%s,%s,%s,%s,%s)",
        (principal["institution_id"], subject, topic, difficulty, json.dumps(questions)),
    )
    flash(f"AI exam '{subject}: {topic}' created with {len(questions)} questions.", "success")
    return redirect(url_for("principal.dashboard"))


@principal_bp.route("/chatbot", methods=["POST"])
@login_required("principal")
def chatbot():
    principal = query_one("SELECT * FROM principals WHERE id=%s", (session["user_pk"],))
    message = request.json.get("message", "")
    context = f"Principal {principal['full_name']}"
    reply = dashboard_chatbot_reply(context, [], message)
    return jsonify({"reply": reply})
