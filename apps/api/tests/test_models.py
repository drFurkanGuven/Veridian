from veridian_api.domain.enums import FpgaTarget, Toolchain, UserRole
from veridian_api.infrastructure.database.base import Base, str_enum
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


def test_str_enum_uses_lowercase_values() -> None:
    column_type = str_enum(UserRole, "user_role")
    assert column_type.process_bind_param(UserRole.ADMIN, None) == "admin"
    assert column_type.process_result_value("user", None) is UserRole.USER
    assert column_type.process_result_value("admin", None) is UserRole.ADMIN
    assert column_type.process_result_value("ADMIN", None) is UserRole.ADMIN
    assert column_type.process_result_value("USER", None) is UserRole.USER


def test_str_enum_accepts_legacy_project_enums() -> None:
    target_type = str_enum(FpgaTarget, "fpga_target")
    toolchain_type = str_enum(Toolchain, "toolchain")
    assert target_type.process_result_value("GENERIC", None) is FpgaTarget.GENERIC
    assert (
        toolchain_type.process_result_value("YOSYS_NEXTPNR", None)
        is Toolchain.YOSYS_NEXTPNR
    )


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
