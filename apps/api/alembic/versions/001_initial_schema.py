"""initial_schema

Revision ID: 001_initial
Revises:
Create Date: 2026-07-06 20:00:00.000000

"""

from alembic import op

from veridian_api.infrastructure.database.base import Base
from veridian_api.infrastructure.database.models import (  # noqa: F401
    AiConversation,
    AiMessage,
    Artifact,
    AuditLog,
    CompilationJob,
    File,
    Folder,
    JobLog,
    OAuthAccount,
    Project,
    SimulationJob,
    User,
    UserSession,
)

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
