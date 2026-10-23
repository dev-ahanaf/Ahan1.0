"""phase2_schema

Revision ID: ceb0f39334f2
Revises: 822821a643e5
Create Date: 2026-10-19 22:08:26.895088

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ceb0f39334f2'
down_revision: Union[str, Sequence[str], None] = '822821a643e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('devices') as batch_op:
        batch_op.alter_column('assistant_name',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=64),
                   existing_nullable=False,
                   existing_server_default=sa.text("'MyVoice'"))
        batch_op.alter_column('personality',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=128),
                   nullable=True,
                   existing_server_default=sa.text("'helpful, concise voice assistant'"))
        batch_op.alter_column('asr_provider',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=32),
                   existing_nullable=True)
        batch_op.alter_column('llm_provider',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=32),
                   existing_nullable=True)
        batch_op.alter_column('llm_model',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=64),
                   existing_nullable=True)
        batch_op.alter_column('tts_provider',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=32),
                   existing_nullable=True)
        batch_op.alter_column('tts_voice',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=64),
                   existing_nullable=True)
        batch_op.alter_column('vad_mode',
                   existing_type=sa.TEXT(),
                   type_=sa.String(length=16),
                   existing_nullable=False,
                   existing_server_default=sa.text("'manual'"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('devices') as batch_op:
        batch_op.alter_column('vad_mode',
                   existing_type=sa.String(length=16),
                   type_=sa.TEXT(),
                   existing_nullable=False,
                   existing_server_default=sa.text("'manual'"))
        batch_op.alter_column('tts_voice',
                   existing_type=sa.String(length=64),
                   type_=sa.TEXT(),
                   existing_nullable=True)
        batch_op.alter_column('tts_provider',
                   existing_type=sa.String(length=32),
                   type_=sa.TEXT(),
                   existing_nullable=True)
        batch_op.alter_column('llm_model',
                   existing_type=sa.String(length=64),
                   type_=sa.TEXT(),
                   existing_nullable=True)
        batch_op.alter_column('llm_provider',
                   existing_type=sa.String(length=32),
                   type_=sa.TEXT(),
                   existing_nullable=True)
        batch_op.alter_column('asr_provider',
                   existing_type=sa.String(length=32),
                   type_=sa.TEXT(),
                   existing_nullable=True)
        batch_op.alter_column('personality',
                   existing_type=sa.String(length=128),
                   type_=sa.TEXT(),
                   nullable=False,
                   existing_server_default=sa.text("'helpful, concise voice assistant'"))
        batch_op.alter_column('assistant_name',
                   existing_type=sa.String(length=64),
                   type_=sa.TEXT(),
                   existing_nullable=False,
                   existing_server_default=sa.text("'MyVoice'"))
