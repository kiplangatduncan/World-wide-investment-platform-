from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for
)


main_bp = Blueprint(
    "main",
    __name__
)


# -------------------------------------------------
# HOME
# -------------------------------------------------

@main_bp.route("/")
def index():

    return render_template(
        "index.html"
    )


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------

@main_bp.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "dashboard.html"
    )


# -------------------------------------------------
# TRANSACTIONS
# -------------------------------------------------

@main_bp.route("/transactions")
def transactions():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "transactions.html"
    )


# -------------------------------------------------
# WITHDRAWALS
# -------------------------------------------------

@main_bp.route("/withdrawals")
def withdrawals():

    if "user_id" not in session:

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "withdrawals.html"
    )
