"""Add optional monthly debt payment without changing existing applications."""

from alembic import op
import sqlalchemy as sa

revision = "stage3_debt_payment"
down_revision = "57c20c7a970c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("monthly_debt_payment", sa.Numeric(14, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_applications_debt_payment_nonneg",
        "applications",
        "monthly_debt_payment IS NULL OR monthly_debt_payment >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_applications_debt_payment_nonneg", "applications", type_="check")
    op.drop_column("applications", "monthly_debt_payment")
