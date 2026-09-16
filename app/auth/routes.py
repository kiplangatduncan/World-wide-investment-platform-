from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        country = request.form.get("country", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not username or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
            return render_template("register.html")

        existing_username = User.query.filter_by(
            username=username
        ).first()

        if existing_username:
            flash("Username already exists.", "danger")
            return render_template("register.html")

        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_email:
            flash("Email already exists.", "danger")
            return render_template("register.html")

        if phone:
            existing_phone = User.query.filter_by(
                phone=phone
            ).first()

            if existing_phone:
                flash("Phone number already exists.", "danger")
                return render_template("register.html")

        user = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=phone or None,
            country=country or None
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(
            "Registration successful. You can now log in.",
            "success"
        )

        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        login_value = request.form.get(
            "login",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter(
            db.or_(
                User.email == login_value,
                User.username == login_value
            )
        ).first()

        if user and user.check_password(password):

            if not user.is_active_user:
                flash(
                    "Your account has been disabled.",
                    "danger"
                )
                return render_template("login.html")

            login_user(user)

            next_page = request.args.get("next")

            if next_page:
                return redirect(next_page)

            return redirect(url_for("dashboard"))

        flash(
            "Invalid username/email or password.",
            "danger"
        )

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("index"))
