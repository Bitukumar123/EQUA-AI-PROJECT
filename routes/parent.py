from flask import Blueprint, render_template, session, request, jsonify
from db import query_all, query_one
from utils.security import login_required
from utils.ai import dashboard_chatbot_reply

parent_bp = Blueprint("parent", __name__, url_prefix="/parent")


@parent_bp.route("/dashboard")
@login_required("parent")
def dashboard():
    parent = query_one("SELECT * FROM parents WHERE id=%s", (session["user_pk"],))
    child = query_one("SELECT * FROM students WHERE id=%s", (parent["student_id"],))

    attendance_rows = query_all(
        "SELECT attendance_date, status FROM attendance WHERE student_id=%s ORDER BY attendance_date DESC LIMIT 30",
        (child["id"],),
    )
    total_marked = len(attendance_rows)
    present_count = sum(1 for r in attendance_rows if r["status"] == "present")
    attendance_pct = round((present_count / total_marked) * 100, 1) if total_marked else 0

    results = query_all(
        "SELECT er.*, e.subject, e.topic FROM exam_results er "
        "JOIN exams e ON e.id = er.exam_id WHERE er.student_id=%s ORDER BY er.taken_at DESC",
        (child["id"],),
    )

    return render_template(
        "dashboard_parent.html",
        parent=parent,
        child=child,
        attendance_rows=attendance_rows,
        attendance_pct=attendance_pct,
        results=results,
    )


@parent_bp.route("/chatbot", methods=["POST"])
@login_required("parent")
def chatbot():
    parent = query_one("SELECT * FROM parents WHERE id=%s", (session["user_pk"],))
    child = query_one("SELECT * FROM students WHERE id=%s", (parent["student_id"],))
    message = request.json.get("message", "")
    context = f"Parent {parent['full_name']}, asking about their child {child['full_name']} (class {child.get('class_name')})"
    reply = dashboard_chatbot_reply(context, [], message)
    return jsonify({"reply": reply})
