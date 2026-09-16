from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.models import (
    InvestmentPlan,
    Investment,
    Transaction
)


investments_bp = Blueprint(
    "investments",
    __name__,
    url_prefix="/investments"
)


@investments_bp.route("/")
@login_required
def investments():

    user_investments = Investment.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Investment.created_at.desc()
    ).all()

    plans = InvestmentPlan.query.filter_by(
        is_active=True
    ).order_by(
        InvestmentPlan.minimum_amount.asc()
    ).all()

    return render_template(
        "investments.html",
        investments=user_investments,
        plans=plans
    )


@investments_bp.route("/invest/<int:plan_id>", methods=["POST"])
@login_required
def invest(plan_id):

    plan = InvestmentPlan.query.get_or_404(plan_id)

    try:
        amount = float(
            request.form.get("amount", 0)
        )
    except (ValueError, TypeError):
        amount = 0

    if amount <= 0:
        flash(
            "Enter a valid investment amount.",
            "danger"
        )
        return redirect(url_for("investments.investments"))

    if amount < plan.minimum_amount:
        flash(
            f"Minimum investment is {plan.minimum_amount:,.2f}.",
            "danger"
        )
        return redirect(url_for("investments.investments"))

    if plan.maximum_amount is not None:
        if amount > plan.maximum_amount:
            flash(
                f"Maximum investment is {plan.maximum_amount:,.2f}.",
                "danger"
            )
            return redirect(url_for("investments.investments"))

    if current_user.balance < amount:
        flash(
            "Insufficient available balance. Please deposit funds first.",
            "danger"
        )
        return redirect(url_for("investments.investments"))

    expected_return = amount * (
        plan.return_rate / 100
    )

    start_date = datetime.utcnow()

    maturity_date = start_date + timedelta(
        days=plan.duration_days
    )

    investment = Investment(
        user_id=current_user.id,
        plan_id=plan.id,
        amount=amount,
        expected_return=expected_return,
        status="active",
        start_date=start_date,
        maturity_date=maturity_date
    )

    current_user.balance -= amount
    current_user.total_invested += amount

    transaction = Transaction(
        user_id=current_user.id,
        transaction_type="investment",
        amount=amount,
        currency=current_user.currency or "KES",
        reference=f"INV-{int(datetime.utcnow().timestamp())}",
        description=f"Investment in {plan.name}",
        status="completed"
    )

    db.session.add(investment)
    db.session.add(transaction)

    db.session.commit()

    flash(
        "Investment created successfully.",
        "success"
    )

    return redirect(url_for("investments.investments"))
