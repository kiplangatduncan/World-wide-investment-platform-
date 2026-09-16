from functools import wraps

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from app import db

from app.models import (
    User,
    Investment,
    InvestmentPlan,
    Deposit,
    Withdrawal,
    Transaction
)


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
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


@admin_bp.route("/")
@admin_required
def admin_dashboard():

    users_count = User.query.count()

    investments_count = Investment.query.count()

    deposits_count = Deposit.query.count()

    withdrawals_count = Withdrawal.query.count()

    transactions_count = Transaction.query.count()

    users = User.query.order_by(
        User.created_at.desc()
    ).limit(20).all()

    return render_template(
        "admin.html",
        users_count=users_count,
        investments_count=investments_count,
        deposits_count=deposits_count,
        withdrawals_count=withdrawals_count,
        transactions_count=transactions_count,
        users=users
    )


@admin_bp.route("/plans")
@admin_required
def plans():

    plans = InvestmentPlan.query.order_by(
        InvestmentPlan.created_at.desc()
    ).all()

    return render_template(
        "admin.html",
        plans=plans
    )


@admin_bp.route("/users")
@admin_required
def users():

    users = User.query.order_by(
        User.created_at.desc()
    ).all()

    return render_template(
        "admin.html",
        users=users
  )
