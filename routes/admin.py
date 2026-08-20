from flask import Blueprint, render_template, session, request, jsonify
from datetime import date
from db import query_all, query_one, execute
from utils.security import login_required
from utils.ai import dashboard_chatbot_reply

admin_bp = Blueprint("institution", __name__, url_prefix="/institution")


@admin_bp.route("/dashboard")
@login_required("institution")
def dashboard():
    inst_id = session["user_pk"]
    institution = query_one("SELECT * FROM institutions WHERE id=%s", (inst_id,))
    principals = query_all("SELECT * FROM principals WHERE institution_id=%s", (inst_id,))
    students = query_all("SELECT * FROM students WHERE institution_id=%s", (inst_id,))

    total_students = len(students)
    total_principals = len(principals)

    return render_template(
        "dashboard_admin.html",
        institution=institution,
        principals=principals,
        students=students,
        total_students=total_students,
        total_principals=total_principals,
    )


@admin_bp.route("/chatbot", methods=["POST"])
@login_required("institution")
def chatbot():
    institution = query_one("SELECT * FROM institutions WHERE id=%s", (session["user_pk"],))
    message = request.json.get("message", "")
    context = f"Institution admin for {institution['institution_name']}"
    reply = dashboard_chatbot_reply(context, [], message)
    return jsonify({"reply": reply})


@admin_bp.route("/attendance", methods=["GET"])
@login_required("institution")
def attendance():
    inst_id = session["user_pk"]

    # Which date are we viewing/marking? Defaults to today.
    selected_date = request.args.get("date", date.today().isoformat())

    students = query_all(
        "SELECT * FROM students WHERE institution_id=%s ORDER BY class_name, full_name",
        (inst_id,),
    )

    # Pull any attendance already marked for this date, keyed by student_id
    existing_rows = query_all(
        """
        SELECT a.student_id, a.status
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE s.institution_id=%s AND a.attendance_date=%s
        """,
        (inst_id, selected_date),
    )
    existing_map = {row["student_id"]: row["status"] for row in existing_rows}

    return render_template(
        "attendance.html",
        students=students,
        selected_date=selected_date,
        existing_map=existing_map,
    )


@admin_bp.route("/attendance", methods=["POST"])
@login_required("institution")
def save_attendance():
    inst_id = session["user_pk"]
    attendance_date = request.form.get("attendance_date", date.today().isoformat())

    students = query_all(
        "SELECT id FROM students WHERE institution_id=%s", (inst_id,)
    )
    valid_student_ids = {s["id"] for s in students}

    for key, status in request.form.items():
        if not key.startswith("status_"):
            continue
        try:
            student_id = int(key.replace("status_", ""))
        except ValueError:
            continue

        # Only allow marking attendance for students that belong to this institution
        if student_id not in valid_student_ids:
            continue
        if status not in ("present", "absent", "late"):
            continue

        execute(
            """
            INSERT INTO attendance (student_id, attendance_date, status, marked_by)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE status=VALUES(status), marked_by=VALUES(marked_by)
            """,
            (student_id, attendance_date, status, inst_id),
        )

    return render_template(
        "attendance.html",
        students=query_all(
            "SELECT * FROM students WHERE institution_id=%s ORDER BY class_name, full_name",
            (inst_id,),
        ),
        selected_date=attendance_date,
        existing_map={
            row["student_id"]: row["status"]
            for row in query_all(
                """
                SELECT a.student_id, a.status
                FROM attendance a
                JOIN students s ON s.id = a.student_id
                WHERE s.institution_id=%s AND a.attendance_date=%s
                """,
                (inst_id, attendance_date),
            )
        },
        saved=True,
    )
