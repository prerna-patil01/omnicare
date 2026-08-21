"""add page-aware report extraction tables

Revision ID: 46d7e8f9a012
Revises: 4d0d6c7c7e01
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "46d7e8f9a012"
down_revision = "4d0d6c7c7e01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "report_extractions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("parser", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id"),
    )
    with op.batch_alter_table("report_extractions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_report_extractions_report_id"), ["report_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_report_extractions_status"), ["status"], unique=False)

    op.create_table(
        "report_pages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "page_number", name="uq_report_pages_report_page"),
    )
    with op.batch_alter_table("report_pages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_report_pages_report_id"), ["report_id"], unique=False)


def downgrade():
    with op.batch_alter_table("report_pages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_report_pages_report_id"))
    op.drop_table("report_pages")
    with op.batch_alter_table("report_extractions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_report_extractions_status"))
        batch_op.drop_index(batch_op.f("ix_report_extractions_report_id"))
    op.drop_table("report_extractions")
