"""create_all_core_tables

Revision ID: 20240715_02
Revises: 
Create Date: 2025-07-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20240715_02'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # employees (계정 정보만)
    op.create_table(
        'employees',
        sa.Column('employee_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String, unique=True, nullable=False),
        sa.Column('username', sa.String, unique=True, nullable=False),
        sa.Column('password', sa.String, nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('role', sa.String, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime),
    )
    
    # employee_info (인사 정보)
    op.create_table(
        'employee_info',
        sa.Column('employee_info_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('employee_id', sa.Integer, sa.ForeignKey('employees.employee_id'), nullable=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('team', sa.String),
        sa.Column('position', sa.String),
        sa.Column('business_unit', sa.String),
        sa.Column('branch', sa.String),
        sa.Column('contact_number', sa.String),
        sa.Column('responsibilities', sa.String),
        sa.Column('base_salary', sa.Integer),
        sa.Column('incentive_pay', sa.Integer),
        sa.Column('avg_monthly_budget', sa.Integer),
        sa.Column('latest_evaluation', sa.String),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime),
    )
    # customers
    op.create_table(
        'customers',
        sa.Column('customer_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('customer_name', sa.String, nullable=False),
        sa.Column('customer_type', sa.String),
        sa.Column('address', sa.String),
        sa.Column('doctor_name', sa.String),
        sa.Column('total_patients', sa.Integer),
        sa.Column('customer_grade', sa.String),
        sa.Column('notes', sa.String),
        sa.Column('created_at', sa.DateTime),
    )
    # products
    op.create_table(
        'products',
        sa.Column('product_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('product_name', sa.String, nullable=False),
        sa.Column('description', sa.String),
        sa.Column('category', sa.String),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    # interaction_logs
    op.create_table(
        'interaction_logs',
        sa.Column('log_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('employee_id', sa.Integer, sa.ForeignKey('employees.employee_id'), nullable=False),
        sa.Column('customer_id', sa.Integer, sa.ForeignKey('customers.customer_id'), nullable=False),
        sa.Column('interaction_type', sa.String, nullable=False),
        sa.Column('summary', sa.String),
        sa.Column('sentiment', sa.String),
        sa.Column('compliance_risk', sa.String),
        sa.Column('interacted_at', sa.DateTime, nullable=False),
    )
    # sales_records
    op.create_table(
        'sales_records',
        sa.Column('record_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('employee_id', sa.Integer, sa.ForeignKey('employees.employee_id'), nullable=False),
        sa.Column('customer_id', sa.Integer, sa.ForeignKey('customers.customer_id'), nullable=False),
        sa.Column('product_id', sa.Integer, sa.ForeignKey('products.product_id'), nullable=False),
        sa.Column('sale_amount', sa.Integer, nullable=False),
        sa.Column('sale_date', sa.Date, nullable=False),
    )
    # documents
    op.create_table(
        'documents',
        sa.Column('doc_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('uploader_id', sa.Integer, sa.ForeignKey('employees.employee_id'), nullable=False),
        sa.Column('doc_title', sa.String, nullable=False),
        sa.Column('doc_type', sa.String),
        sa.Column('file_path', sa.String, nullable=False),
        sa.Column('version', sa.String),
        sa.Column('created_at', sa.DateTime),
    )
    # chat_history
    op.create_table(
        'chat_history',
        sa.Column('message_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String, nullable=False),
        sa.Column('employee_id', sa.Integer, sa.ForeignKey('employees.employee_id'), nullable=False),
        sa.Column('user_query', sa.String, nullable=False),
        sa.Column('system_response', sa.String, nullable=False),
        sa.Column('created_at', sa.DateTime),
    )
    # system_trace_logs
    op.create_table(
        'system_trace_logs',
        sa.Column('trace_id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('message_id', sa.Integer, sa.ForeignKey('chat_history.message_id'), nullable=False),
        sa.Column('event_type', sa.String, nullable=False),
        sa.Column('log_data', sa.dialects.postgresql.JSONB),
        sa.Column('latency_ms', sa.Integer),
        sa.Column('created_at', sa.DateTime),
    )
    # assignment_map
    op.create_table(
        'assignment_map',
        sa.Column('employee_id', sa.Integer, sa.ForeignKey('employees.employee_id'), nullable=False),
        sa.Column('customer_id', sa.Integer, sa.ForeignKey('customers.customer_id'), nullable=False),
        sa.PrimaryKeyConstraint('employee_id', 'customer_id'),
    )
    # document_relations
    op.create_table(
        'document_relations',
        sa.Column('doc_id', sa.Integer, sa.ForeignKey('documents.doc_id'), nullable=False),
        sa.Column('related_doc_id', sa.Integer, sa.ForeignKey('documents.doc_id'), nullable=False),
        sa.Column('relation_type', sa.String, nullable=False),
        sa.PrimaryKeyConstraint('doc_id', 'related_doc_id', 'relation_type'),
    )
    # document_interaction_map
    op.create_table(
        'document_interaction_map',
        sa.Column('doc_id', sa.Integer, sa.ForeignKey('documents.doc_id'), nullable=False),
        sa.Column('log_id', sa.Integer, sa.ForeignKey('interaction_logs.log_id'), nullable=False),
        sa.PrimaryKeyConstraint('doc_id', 'log_id'),
    )
    # document_sales_map
    op.create_table(
        'document_sales_map',
        sa.Column('doc_id', sa.Integer, sa.ForeignKey('documents.doc_id'), nullable=False),
        sa.Column('record_id', sa.Integer, sa.ForeignKey('sales_records.record_id'), nullable=False),
        sa.PrimaryKeyConstraint('doc_id', 'record_id'),
    )

def downgrade() -> None:
    op.drop_table('document_sales_map')
    op.drop_table('document_interaction_map')
    op.drop_table('document_relations')
    op.drop_table('assignment_map')
    op.drop_table('system_trace_logs')
    op.drop_table('chat_history')
    op.drop_table('documents')
    op.drop_table('sales_records')
    op.drop_table('interaction_logs')
    op.drop_table('products')
    op.drop_table('customers')
    op.drop_table('employee_info')
    op.drop_table('employees') 