"""preserve missing vital measurements as null

Revision ID: 4d0d6c7c7e01
Revises: dbdde4104cc7
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "4d0d6c7c7e01"
down_revision = "dbdde4104cc7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("vital_readings", schema=None) as batch_op:
        batch_op.alter_column("heart_rate", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("hrv_ms", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("spo2", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("sleep_hours", existing_type=sa.Float(), nullable=True)
        batch_op.alter_column("stress_score", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("hydration_ml", existing_type=sa.Integer(), nullable=True)


def downgrade():
    # Existing nulls cannot truthfully be converted to a clinical value. A
    # downgrade therefore requires an explicit data-migration decision.
    raise RuntimeError("Cannot downgrade without choosing values for missing vital measurements.")
