from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from app import db

from app.models import (
    Withdrawal,
    Transaction
)


main_bp = Blueprint(
    "main",
    __name__
)


@main_bp.route("/")
def index():

    return render_template(
        "index.html"
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():

    return render_template(
        "dashboard.html"
    )


@main_bp.route(
    "/withdrawals",
    methods=["GET", "POST"]
)
@login_required
def withdrawals():

    if request.method == "POST":

        try:
            amount = float(
                request.form.get(
                    "amount",
                    0
                )
            )
        except (ValueError, TypeError):

            amount = 0

        payment_method = request.form.get(
            "payment_method",
            ""
        ).strip()

        account_name = request.form.get(
            "account_name",
            ""
        ).strip()

        account_number = request.form.get(
            "account_number",
            ""
        ).strip()

        if amount <= 0:

            flash(
                "Enter a valid withdrawal amount.",
                "danger"
            )

            return redirect(
                url_for("withdrawals")
            )

        if amount > current_user.balance:

            flash(
                "Insufficient available balance.",
                "danger"
            )

            return redirect(
                url_for("withdrawals")
            )

        reference = (
            f"WDR-{current_user.id}-"
            f"{int(datetime.utcnow().timestamp())}"
        )

        withdrawal = Withdrawal(
            user_id=current_user.id,
            amount=amount,
            currency=current_user.currency or "KES",
            payment_method=payment_method,
            account_name=account_name,
            account_number=account_number,
            reference=reference,
            status="pending"
        )

        current_user.balance -= amount

        db.session.add(withdrawal)

        db.session.commit()

        flash(
            "Withdrawal request submitted.",
            "success"
        )

        return redirect(
            url_for("withdrawals")
        )

    return render_template(
        "withdrawals.html"
    )


@main_bp.route("/transactions")
@login_required
def transactions():

    user_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Transaction.created_at.desc()
    ).all()

    return render_template(
        "transactions.html",
        transactions=user_transactions
    )
