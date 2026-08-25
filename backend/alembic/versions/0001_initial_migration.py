"""Initial migration for all models

Revision ID: 0001_initial
Revises: 
Create Date: 2026-08-22 19:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Customer
    op.create_table(
        'customer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customer_email'), 'customer', ['email'], unique=False)
    op.create_index(op.f('ix_customer_external_id'), 'customer', ['external_id'], unique=True)

    # Payment
    op.create_table(
        'payment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('failure_reason', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('payment_method', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_customer_id'), 'payment', ['customer_id'], unique=False)
    op.create_index(op.f('ix_payment_external_id'), 'payment', ['external_id'], unique=False)
    op.create_index(op.f('ix_payment_status'), 'payment', ['status'], unique=False)

    # Checkout
    op.create_table(
        'checkout',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('cart_value', sa.Float(), nullable=False),
        sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('abandoned_step', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_checkout_customer_id'), 'checkout', ['customer_id'], unique=False)
    op.create_index(op.f('ix_checkout_external_id'), 'checkout', ['external_id'], unique=False)
    op.create_index(op.f('ix_checkout_status'), 'checkout', ['status'], unique=False)

    # Subscription
    op.create_table(
        'subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('plan_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('next_billing_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscription_customer_id'), 'subscription', ['customer_id'], unique=False)
    op.create_index(op.f('ix_subscription_external_id'), 'subscription', ['external_id'], unique=False)
    op.create_index(op.f('ix_subscription_status'), 'subscription', ['status'], unique=False)

    # Invoice
    op.create_table(
        'invoice',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('amount_due', sa.Float(), nullable=False),
        sa.Column('currency', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_customer_id'), 'invoice', ['customer_id'], unique=False)
    op.create_index(op.f('ix_invoice_external_id'), 'invoice', ['external_id'], unique=False)
    op.create_index(op.f('ix_invoice_status'), 'invoice', ['status'], unique=False)

    # RecoveryCase
    op.create_table(
        'recoverycase',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_type', sa.Enum('FAILED_PAYMENT', 'ABANDONED_CHECKOUT', 'FAILED_SUBSCRIPTION', 'OVERDUE_INVOICE', name='casetype'), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('amount_at_risk', sa.Float(), nullable=False),
        sa.Column('status', sa.Enum('DETECTED', 'PROCESSING', 'RECOVERED', 'ESCALATED', 'UNRECOVERABLE', name='casestatus'), nullable=False),
        sa.Column('root_cause', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('recommended_action', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recoverycase_case_type'), 'recoverycase', ['case_type'], unique=False)
    op.create_index(op.f('ix_recoverycase_source_id'), 'recoverycase', ['source_id'], unique=False)
    op.create_index(op.f('ix_recoverycase_customer_id'), 'recoverycase', ['customer_id'], unique=False)
    op.create_index(op.f('ix_recoverycase_status'), 'recoverycase', ['status'], unique=False)


    # RecoveryAction
    
    op.create_table(
        'recoveryaction',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('channel', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('payload', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recoverycase.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recoveryaction_action_type'), 'recoveryaction', ['action_type'], unique=False)
    op.create_index(op.f('ix_recoveryaction_case_id'), 'recoveryaction', ['case_id'], unique=False)
    op.create_index(op.f('ix_recoveryaction_status'), 'recoveryaction', ['status'], unique=False)

    # GuardrailEvent
    op.create_table(
        'guardrailevent',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.Integer(), nullable=False),
        sa.Column('rule_triggered', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('decision', sa.Enum('APPROVED', 'BLOCKED', name='guardraildecision'), nullable=False),
        sa.Column('reason', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recoverycase.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guardrailevent_case_id'), 'guardrailevent', ['case_id'], unique=False)
    op.create_index(op.f('ix_guardrailevent_decision'), 'guardrailevent', ['decision'], unique=False)

    # AuditLog
    op.create_table(
        'auditlog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('actor', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('details', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auditlog_entity_id'), 'auditlog', ['entity_id'], unique=False)
    op.create_index(op.f('ix_auditlog_entity_type'), 'auditlog', ['entity_type'], unique=False)


def downgrade() -> None:
    op.drop_table('auditlog')
    op.drop_table('guardrailevent')
    op.drop_table('recoveryaction')
    op.drop_table('recoverycase')
    op.drop_table('invoice')
    op.drop_table('subscription')
    op.drop_table('checkout')
    op.drop_table('payment')
    op.drop_table('customer')
