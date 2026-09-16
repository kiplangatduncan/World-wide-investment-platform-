from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request
)

from flask_login import login_required, current_user

from app import db

from app.models import Deposit, Transaction

from app.payments.service import (
    get_country_payment_methods,
    start_mpesa_payment,
    start_card_payment
)


payments_bp = Blueprint(
    "payments",
    __name__,
    url_prefix="/payments"
)


@payments_bp.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    payment_options = get_country_payment_methods(
        current_user.country
    )

    if request.method == "POST":

        try:
            amount = float(
                request.form.get("amount", 0)
            )
        except (ValueError, TypeError):
            amount = 0

        method = request.form.get(
            "payment_method",
            ""
        )

        if amount <= 0:
            flash(
                "Enter a valid deposit amount.",
                "danger"
            )
            return redirect(
                url_for("payments.deposit")
            )

        if method not in payment_options["methods"]:
            flash(
                "Invalid payment method.",
                "danger"
            )
            return redirect(
                url_for("payments.deposit")
            )

        reference = (
            f"DEP-{current_user.id}-"
            f"{int(datetime.utcnow().timestamp())}"
        )

        deposit_record = Deposit(
            user_id=current_user.id,
            amount=amount,
            currency=payment_options["currency"],
            payment_method=method,
            provider=method,
            reference=reference,
            status="pending"
        )

        db.session.add(deposit_record)
        db.session.commit()

        if method == "M-Pesa":

            phone = request.form.get(
                "phone",
                current_user.phone
            )

            try:

                result = start_mpesa_payment(
                    phone_number=phone,
                    amount=amount,
                    reference=reference
                )

                flash(
                    "M-Pesa payment request sent. "
                    "Complete the payment on your phone.",
                    "success"
                )

                return redirect(
                    url_for("dashboard")
                )

            except Exception:

                deposit_record.status = "failed"

                db.session.commit()

                flash(
                    "Unable to start M-Pesa payment. "
                    "Check your M-Pesa configuration.",
                    "danger"
                )

                return redirect(
                    url_for("payments.deposit")
                )

        if method == "Card":

            try:

                result = start_card_payment(
                    amount=amount,
                    currency=payment_options["currency"],
                    email=current_user.email,
                    reference=reference
                )

                payment_link = (
                    result.get("data", {})
                    .get("link")
                )

                if payment_link:
                    return redirect(
                        payment_link
                    )

            except Exception:
                pass

            flash(
                "Unable to start card payment.",
                "danger"
            )

        return redirect(
            url_for("payments.deposit")
        )

    return render_template(
        "deposit.html",
        payment_options=payment_options
          )
