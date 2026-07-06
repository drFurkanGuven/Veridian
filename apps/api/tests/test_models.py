from veridian_api.infrastructure.database.base import Base
from veridian_api.infrastructure.database.models import (  # noqa: F401
    AiConversation,
    AiMessage,
    Artifact,
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


from veridian_api.domain.enums import UserRole
from veridian_api.infrastructure.database.base import str_enum


def test_str_enum_uses_lowercase_values() -> None:
    column_type = str_enum(UserRole, "user_role")
    assert column_type.enums == ["user", "admin"]
    assert column_type._object_value_for_elem("user") is UserRole.USER
    assert column_type._object_value_for_elem("admin") is UserRole.ADMIN


def test_metadata_contains_all_tables() -> None:
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users",
        "oauth_accounts",
        "sessions",
        "projects",
        "folders",
        "files",
        "compilation_jobs",
        "simulation_jobs",
        "artifacts",
        "job_logs",
        "ai_conversations",
        "ai_messages",
        "audit_logs",
    }
    assert expected == table_names


def test_users_table_columns() -> None:
    users = Base.metadata.tables["users"]
    column_names = {column.name for column in users.columns}
    assert "email" in column_names
    assert "password_hash" in column_names
    assert "deleted_at" not in column_names


def test_projects_soft_delete_column() -> None:
    projects = Base.metadata.tables["projects"]
    assert "deleted_at" in {column.name for column in projects.columns}


def test_artifacts_polymorphic_columns() -> None:
    artifacts = Base.metadata.tables["artifacts"]
    column_names = {column.name for column in artifacts.columns}
    assert {"job_id", "job_type", "storage_key"}.issubset(column_names)
