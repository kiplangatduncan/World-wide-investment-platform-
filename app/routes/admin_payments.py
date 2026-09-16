from functools import wraps

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request
)

from flask_login import (
    login_required,
    current_user
)

from app import db

from app.models import PaymentAccount


admin_payments_bp = Blueprint(
    "admin_payments",
    __name__,
    url_prefix="/admin/payment-accounts"
)


def admin_required(function):

    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):

        if not current_user.is_admin:

            flash(
                "Administrator access required.",
                "danger"
            )

            return redirect(
                url_for("dashboard")
            )

        return function(*args, **kwargs)

    return wrapper


@admin_payments_bp.route("/")
@admin_required
def payment_accounts():

    accounts = PaymentAccount.query.order_by(
        PaymentAccount.country.asc()
    ).all()

    return render_template(
        "admin_payment_accounts.html",
        accounts=accounts
    )


@admin_payments_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_payment_account():

    if request.method == "POST":

        account = PaymentAccount(
            country=request.form.get(
                "country",
                ""
            ).strip(),

            currency=request.form.get(
                "currency",
                ""
            ).strip(),

            payment_method=request.form.get(
                "payment_method",
                ""
            ).strip(),

            provider=request.form.get(
                "provider",
                ""
            ).strip(),

            account_name=request.form.get(
                "account_name",
                ""
            ).strip(),

            account_number=request.form.get(
                "account_number",
                ""
            ).strip(),

            phone_number=request.form.get(
                "phone_number",
                ""
            ).strip(),

            branch=request.form.get(
                "branch",
                ""
            ).strip(),

            additional_details=request.form.get(
                "additional_details",
                ""
            ).strip()
        )

        db.session.add(account)
        db.session.commit()

        flash(
            "Payment account added successfully.",
            "success"
        )

        return redirect(
            url_for(
                "admin_payments.payment_accounts"
            )
        )

    return render_template(
        "admin_payment_accounts.html",
        accounts=PaymentAccount.query.all(),
        adding=True
    )
