import json
from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash
from db import query_all, query_one, execute
from utils.security import login_required
from utils.ai import ai_teacher_reply, generate_exam_questions, grade_exam, dashboard_chatbot_reply

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required("student")
def dashboard():
    student = query_one("SELECT * FROM students WHERE id=%s", (session["user_pk"],))

    attendance_rows = query_all(
        "SELECT attendance_date, status FROM attendance WHERE student_id=%s ORDER BY attendance_date DESC LIMIT 30",
        (student["id"],),
    )
    total_marked = len(attendance_rows)
    present_count = sum(1 for r in attendance_rows if r["status"] == "present")
    attendance_pct = round((present_count / total_marked) * 100, 1) if total_marked else 0

    results = query_all(
        "SELECT er.*, e.subject, e.topic FROM exam_results er "
        "JOIN exams e ON e.id = er.exam_id WHERE er.student_id=%s ORDER BY er.taken_at DESC",
        (student["id"],),
    )

    exams_available = query_all(
        "SELECT * FROM exams WHERE institution_id=%s ORDER BY created_at DESC",
        (student["institution_id"],),
    )

    return render_template(
        "dashboard_student.html",
        student=student,
        attendance_rows=attendance_rows,
        attendance_pct=attendance_pct,
        results=results,
        exams_available=exams_available,
    )


# ---------- AI Teacher (chat + whiteboard) ----------
@student_bp.route("/ai-teacher")
@login_required("student")
def ai_teacher():
    student = query_one("SELECT * FROM students WHERE id=%s", (session["user_pk"],))
    history = query_all(
        "SELECT role, message FROM chat_history WHERE student_id=%s ORDER BY created_at ASC",
        (student["id"],),
    )
    return render_template("ai_teacher.html", student=student, history=history)


@student_bp.route("/ai-teacher/send", methods=["POST"])
@login_required("student")
def ai_teacher_send():
    student = query_one("SELECT * FROM students WHERE id=%s", (session["user_pk"],))
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "empty message"}), 400

    execute(
        "INSERT INTO chat_history (student_id, role, message) VALUES (%s,'user',%s)",
        (student["id"], user_message),
    )
    history = query_all(
        "SELECT role, message FROM chat_history WHERE student_id=%s ORDER BY created_at ASC",
        (student["id"],),
    )
    reply = ai_teacher_reply(student["full_name"], student.get("class_name"), history)

    execute(
        "INSERT INTO chat_history (student_id, role, message) VALUES (%s,'assistant',%s)",
        (student["id"], reply),
    )
    return jsonify({"reply": reply})


# ---------- AI Exam ----------
@student_bp.route("/exam/<int:exam_id>")
@login_required("student")
def take_exam(exam_id):
    exam = query_one("SELECT * FROM exams WHERE id=%s", (exam_id,))
    if not exam:
        flash("Exam not found.", "error")
        return redirect(url_for("student.dashboard"))
    questions = json.loads(exam["questions_json"])
    # strip correct answers before sending to the browser
    safe_questions = [{"question": q["question"], "options": q["options"]} for q in questions]
    return render_template("ai_exam.html", exam=exam, questions=safe_questions)


@student_bp.route("/exam/<int:exam_id>/submit", methods=["POST"])
@login_required("student")
def submit_exam(exam_id):
    exam = query_one("SELECT * FROM exams WHERE id=%s", (exam_id,))
    questions = json.loads(exam["questions_json"])

    answers = {}
    for i in range(len(questions)):
        val = request.form.get(f"q{i}")
        if val is not None:
            answers[str(i)] = val

    score, max_score, feedback = grade_exam(questions, answers)

    execute(
        "INSERT INTO exam_results (exam_id, student_id, answers_json, score, max_score, ai_feedback) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (exam_id, session["user_pk"], json.dumps(answers), score, max_score, feedback),
    )
    flash("Exam submitted and AI-graded.", "success")
    return redirect(url_for("student.dashboard"))


# ---------- Dashboard chatbot (shared pattern reused by all roles) ----------
@student_bp.route("/chatbot", methods=["POST"])
@login_required("student")
def chatbot():
    student = query_one("SELECT * FROM students WHERE id=%s", (session["user_pk"],))
    message = request.json.get("message", "")
    context = f"Student {student['full_name']}, class {student.get('class_name')}"
    reply = dashboard_chatbot_reply(context, [], message)
    return jsonify({"reply": reply})
