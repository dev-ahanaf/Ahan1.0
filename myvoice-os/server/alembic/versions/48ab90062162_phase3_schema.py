"""phase3_schema

Revision ID: 48ab90062162
Revises: ceb0f39334f2
Create Date: 2026-10-19 22:37:31.471521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48ab90062162'
down_revision: Union[str, Sequence[str], None] = 'ceb0f39334f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    device_cols = [c['name'] for c in inspector.get_columns('devices')]

    if 'tools_enabled' not in device_cols:
        with op.batch_alter_table('devices') as batch_op:
            batch_op.add_column(sa.Column('tools_enabled', sa.String(length=255), nullable=False, server_default='clock,weather,search,timer,alarm,device_settings'))

    # Check and create timers
    if 'timers' not in existing_tables:
        op.create_table(
            'timers',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('device_id', sa.String(length=32), nullable=False, index=True),
            sa.Column('label', sa.String(length=100), nullable=False, server_default='Timer'),
            sa.Column('duration_seconds', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.String(length=64), nullable=False),
            sa.Column('expires_at', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
            sa.Column('alert_acknowledged', sa.Integer(), nullable=False, server_default='0'),
        )

    # Check and create alarms
    if 'alarms' not in existing_tables:
        op.create_table(
            'alarms',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('device_id', sa.String(length=32), nullable=False, index=True),
            sa.Column('time_str', sa.String(length=10), nullable=False),
            sa.Column('label', sa.String(length=100), nullable=False, server_default='Alarm'),
            sa.Column('timezone', sa.String(length=64), nullable=False, server_default='Asia/Dhaka'),
            sa.Column('repeat_days', sa.String(length=64), nullable=False, server_default=''),
            sa.Column('created_at', sa.String(length=64), nullable=False),
            sa.Column('next_trigger_at', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        )

    # Check and create firmware_releases
    if 'firmware_releases' not in existing_tables:
        op.create_table(
            'firmware_releases',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('version', sa.String(length=32), unique=True, nullable=False, index=True),
            sa.Column('target_hardware', sa.String(length=32), nullable=False, server_default='esp32dev'),
            sa.Column('file_path', sa.String(length=255), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('sha256', sa.String(length=64), nullable=False),
            sa.Column('release_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.String(length=64), nullable=False),
            sa.Column('is_active', sa.Integer(), nullable=False, server_default='1'),
        )

    # Check and create device_telemetry
    if 'device_telemetry' not in existing_tables:
        op.create_table(
            'device_telemetry',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('device_id', sa.String(length=32), nullable=False, index=True),
            sa.Column('rssi', sa.Integer(), nullable=True),
            sa.Column('free_heap', sa.Integer(), nullable=True),
            sa.Column('min_free_heap', sa.Integer(), nullable=True),
            sa.Column('uptime_s', sa.Integer(), nullable=True),
            sa.Column('dropped_frames', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.String(length=64), nullable=False),
        )

    # Check and create audit_logs
    if 'audit_logs' not in existing_tables:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('user', sa.String(length=64), nullable=False, server_default='admin'),
            sa.Column('action', sa.String(length=64), nullable=False),
            sa.Column('target', sa.String(length=64), nullable=True),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('ip_address', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.String(length=64), nullable=False),
        )



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('audit_logs')
    op.drop_table('device_telemetry')
    op.drop_table('firmware_releases')
    op.drop_table('alarms')
    op.drop_table('timers')
    with op.batch_alter_table('devices') as batch_op:
        batch_op.drop_column('tools_enabled')

