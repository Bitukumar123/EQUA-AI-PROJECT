from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import query_one, execute
from utils.security import hash_password, verify_password

auth_bp = Blueprint("auth", __name__)


# ---------- Landing / role picker ----------
@auth_bp.route("/")
def index():
    return render_template("index.html")


# ---------- Registration ----------
@auth_bp.route("/register/institution", methods=["GET", "POST"])
def register_institution():
    if request.method == "POST":
        name = request.form["institution_name"].strip()
        code = request.form["institution_code"].strip()
        password = request.form["password"]
        address = request.form.get("address", "").strip()

        if query_one("SELECT id FROM institutions WHERE institution_code=%s", (code,)):
            flash("That institution ID is already registered.", "error")
            return redirect(url_for("auth.register_institution"))

        execute(
            "INSERT INTO institutions (institution_name, institution_code, password_hash, address) "
            "VALUES (%s,%s,%s,%s)",
            (name, code, hash_password(password), address),
        )
        flash("Institution registered. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_institution.html")


@auth_bp.route("/register/principal", methods=["GET", "POST"])
def register_principal():
    if request.method == "POST":
        inst_code = request.form["institution_code"].strip()
        institution = query_one("SELECT id FROM institutions WHERE institution_code=%s", (inst_code,))
        if not institution:
            flash("Institution ID not found. Ask your school/college to register first.", "error")
            return redirect(url_for("auth.register_principal"))

        principal_id = request.form["principal_id"].strip()
        full_name = request.form["full_name"].strip()
        password = request.form["password"]

        if query_one("SELECT id FROM principals WHERE principal_id=%s", (principal_id,)):
            flash("That principal ID is already registered.", "error")
            return redirect(url_for("auth.register_principal"))

        execute(
            "INSERT INTO principals (institution_id, principal_id, full_name, password_hash) "
            "VALUES (%s,%s,%s,%s)",
            (institution["id"], principal_id, full_name, hash_password(password)),
        )
        flash("Principal account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_principal.html")


@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    if request.method == "POST":
        inst_code = request.form["institution_code"].strip()
        institution = query_one("SELECT id FROM institutions WHERE institution_code=%s", (inst_code,))
        if not institution:
            flash("Institution ID not found.", "error")
            return redirect(url_for("auth.register_student"))

        student_id = request.form["student_id"].strip()
        full_name = request.form["full_name"].strip()
        class_name = request.form.get("class_name", "").strip()
        password = request.form["password"]

        if query_one("SELECT id FROM students WHERE student_id=%s", (student_id,)):
            flash("That student ID is already registered.", "error")
            return redirect(url_for("auth.register_student"))

        execute(
            "INSERT INTO students (institution_id, student_id, full_name, class_name, password_hash) "
            "VALUES (%s,%s,%s,%s,%s)",
            (institution["id"], student_id, full_name, class_name, hash_password(password)),
        )
        flash("Student account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_student.html")


@auth_bp.route("/register/parent", methods=["GET", "POST"])
def register_parent():
    if request.method == "POST":
        child_student_id = request.form["child_student_id"].strip()
        student = query_one("SELECT id FROM students WHERE student_id=%s", (child_student_id,))
        if not student:
            flash("No student found with that Student ID.", "error")
            return redirect(url_for("auth.register_parent"))

        parent_login_id = request.form["parent_login_id"].strip()
        full_name = request.form["full_name"].strip()
        password = request.form["password"]

        if query_one("SELECT id FROM parents WHERE parent_login_id=%s", (parent_login_id,)):
            flash("That parent ID is already registered.", "error")
            return redirect(url_for("auth.register_parent"))

        execute(
            "INSERT INTO parents (student_id, parent_login_id, full_name, password_hash) "
            "VALUES (%s,%s,%s,%s)",
            (student["id"], parent_login_id, full_name, hash_password(password)),
        )
        flash("Parent account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register_parent.html")


# ---------- Login (single form, role selector) ----------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        login_id = request.form["login_id"].strip()
        password = request.form["password"]

        table_map = {
            "institution": ("institutions", "institution_code", "id"),
            "principal": ("principals", "principal_id", "id"),
            "student": ("students", "student_id", "id"),
            "parent": ("parents", "parent_login_id", "id"),
        }
        if role not in table_map:
            flash("Invalid role selected.", "error")
            return redirect(url_for("auth.login"))

        table, id_column, pk = table_map[role]
        user = query_one(f"SELECT * FROM {table} WHERE {id_column}=%s", (login_id,))

        if not user or not verify_password(user["password_hash"], password):
            flash("Incorrect ID or password.", "error")
            return redirect(url_for("auth.login"))

        session.clear()
        session["role"] = role
        session["user_pk"] = user[pk]
        session["display_name"] = user.get("full_name") or user.get("institution_name")

        return redirect(url_for(f"{role}.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
