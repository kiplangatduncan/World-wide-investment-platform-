from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from app.extensions import db
from app.models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash(
                "Please enter your email and password.",
                "danger"
            )
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            session["user_id"] = user.id
            session["user_email"] = user.email
            session["is_admin"] = user.is_admin

            flash(
                "Login successful.",
                "success"
            )

            return redirect(
                url_for("main.dashboard")
            )

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not email or not password:
            flash(
                "Please complete all required fields.",
                "danger"
            )
            return render_template("register.html")

        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "danger"
            )
            return render_template("register.html")

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash(
                "An account with this email already exists.",
                "danger"
            )
            return render_template("register.html")

        user = User(
            email=email,
            password=""
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("auth.login")
    )
