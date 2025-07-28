"""create_customer_monthly_performance_mv_view

Revision ID: bec676522ec0
Revises: 
Create Date: 2025-07-15 15:38:53.543726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bec676522ec0'
down_revision: Union[str, Sequence[str], None] = '20250728_01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
    CREATE MATERIALIZED VIEW customer_monthly_performance_mv AS
    SELECT
        ROW_NUMBER() OVER () AS performance_id,
        c.customer_id,
        to_char(sr.sale_date, 'YYYY-MM') AS year_month,
        SUM(sr.sale_amount) AS monthly_sales,
        SUM(sr.sale_amount) FILTER (WHERE sr.sale_amount IS NOT NULL) AS budget_used,
        COUNT(il.log_id) AS visit_count
    FROM
        customers c
    LEFT JOIN sales_records sr ON c.customer_id = sr.customer_id
    LEFT JOIN interaction_logs il ON c.customer_id = il.customer_id
    GROUP BY
        c.customer_id, to_char(sr.sale_date, 'YYYY-MM');
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP MATERIALIZED VIEW IF EXISTS customer_monthly_performance_mv;")
