from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import User


auth = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


# ============================================================
# REGISTER
# ============================================================

@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()

        country = request.form.get("country", "").strip()
        phone_code = request.form.get("phone_code", "").strip()
        phone = request.form.get("phone", "").strip()

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        currency = request.form.get(
            "currency",
            "KES"
        ).strip().upper()


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not full_name:
            flash("Please enter your full name.")
            return render_template("register.html")

        if len(username) < 3:
            flash("Username must be at least 3 characters.")
            return render_template("register.html")

        if not email:
            flash("Please enter your email address.")
            return render_template("register.html")

        if not country:
            flash("Please select your country.")
            return render_template("register.html")

        if not phone_code:
            flash("Please select your country phone code.")
            return render_template("register.html")

        if not phone:
            flash("Please enter your phone number.")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("register.html")


        # ----------------------------------------------------
        # CLEAN PHONE NUMBER
        # ----------------------------------------------------

        phone = (
            phone
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        if phone.startswith("+"):
            phone = phone[1:]

        if phone.startswith("0"):
            phone = phone[1:]


        # Create international number
        international_phone = phone_code + phone


        # ----------------------------------------------------
        # CHECK USERNAME
        # ----------------------------------------------------

        existing_username = User.query.filter_by(
            username=username
        ).first()

        if existing_username:
            flash("That username is already registered.")
            return render_template("register.html")


        # ----------------------------------------------------
        # CHECK EMAIL
        # ----------------------------------------------------

        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_email:
            flash("That email address is already registered.")
            return render_template("register.html")


        # ----------------------------------------------------
        # CHECK PHONE
        # ----------------------------------------------------

        existing_phone = User.query.filter_by(
            phone=international_phone
        ).first()

        if existing_phone:
            flash("That phone number is already registered.")
            return render_template("register.html")


        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

        user = User(
            full_name=full_name,
            username=username,
            email=email,
            phone=international_phone,
            country=country,
            currency=currency
        )

        user.set_password(password)


        # ----------------------------------------------------
        # SAVE USER
        # ----------------------------------------------------

        try:

            db.session.add(user)
            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print("REGISTRATION ERROR:", e)

            flash("Registration failed. Please try again.")

            return render_template("register.html")


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        flash("Account created successfully. Please log in.")

        return redirect(
            url_for("auth.login")
        )


    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================

@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        user = User.query.filter_by(
            username=username
        ).first()


        if user and user.check_password(password):

            session["user_id"] = user.id
            session["username"] = user.username

            return redirect(
                url_for("main.dashboard")
            )


        flash("Invalid username or password.")


    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@auth.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.")

    return redirect(
        url_for("auth.login")
    )
