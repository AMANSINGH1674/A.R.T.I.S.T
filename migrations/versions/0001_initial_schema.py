"""Create initial tables

Revision ID: 0001
Revises: 
Create Date: 2024-01-30 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('roles', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Workflow definitions table
    op.create_table('workflow_definitions',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_definitions_id'), 'workflow_definitions', ['id'], unique=False)
    
    # Workflow executions table
    op.create_table('workflow_executions',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('task_id', sa.String(length=100), nullable=True),
        sa.Column('workflow_id', sa.String(length=100), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('user_request', sa.Text(), nullable=False),
        sa.Column('request_metadata', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('completed_steps', sa.JSON(), nullable=True),
        sa.Column('intermediate_results', sa.JSON(), nullable=True),
        sa.Column('final_result', sa.JSON(), nullable=True),
        sa.Column('error_info', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_time', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow_definitions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_executions_id'), 'workflow_executions', ['id'], unique=False)
    op.create_index(op.f('ix_workflow_executions_task_id'), 'workflow_executions', ['task_id'], unique=True)
    # Indexes on FK columns for fast joins and lookups
    op.create_index('ix_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'], unique=False)
    op.create_index('ix_workflow_executions_user_id', 'workflow_executions', ['user_id'], unique=False)
    
    # Agent registry table
    op.create_table('agent_registry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('class_path', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_registry_id'), 'agent_registry', ['id'], unique=False)
    op.create_index(op.f('ix_agent_registry_name'), 'agent_registry', ['name'], unique=True)
    
    # Tool registry table
    op.create_table('tool_registry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('class_path', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tool_registry_id'), 'tool_registry', ['id'], unique=False)
    op.create_index(op.f('ix_tool_registry_name'), 'tool_registry', ['name'], unique=True)
    
    # System metrics table
    op.create_table('system_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.String(length=255), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=True),
        sa.Column('labels', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_metrics_id'), 'system_metrics', ['id'], unique=False)
    
    # Audit logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)

def downgrade():
    # Drop all tables in reverse order
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index(op.f('ix_system_metrics_id'), table_name='system_metrics')
    op.drop_table('system_metrics')
    
    op.drop_index(op.f('ix_tool_registry_name'), table_name='tool_registry')
    op.drop_index(op.f('ix_tool_registry_id'), table_name='tool_registry')
    op.drop_table('tool_registry')
    
    op.drop_index(op.f('ix_agent_registry_name'), table_name='agent_registry')
    op.drop_index(op.f('ix_agent_registry_id'), table_name='agent_registry')
    op.drop_table('agent_registry')
    
    op.drop_index('ix_workflow_executions_user_id', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_workflow_id', table_name='workflow_executions')
    op.drop_index(op.f('ix_workflow_executions_task_id'), table_name='workflow_executions')
    op.drop_index(op.f('ix_workflow_executions_id'), table_name='workflow_executions')
    op.drop_table('workflow_executions')
    
    op.drop_index(op.f('ix_workflow_definitions_id'), table_name='workflow_definitions')
    op.drop_table('workflow_definitions')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
