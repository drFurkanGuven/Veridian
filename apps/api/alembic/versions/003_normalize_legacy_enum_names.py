"""normalize_legacy_enum_names

Revision ID: 003_normalize_enums
Revises: 002_account_security
Create Date: 2026-07-06 23:00:00.000000

"""

from alembic import op

revision = "003_normalize_enums"
down_revision = "002_account_security"
branch_labels = None
depends_on = None

_ENUM_FIXES: list[tuple[str, str, dict[str, str]]] = [
    ("users", "role", {"USER": "user", "ADMIN": "admin"}),
    (
        "projects",
        "target_fpga",
        {"ICE40": "ice40", "ECP5": "ecp5", "GENERIC": "generic"},
    ),
    (
        "projects",
        "toolchain",
        {
            "YOSYS_NEXTPNR": "yosys-nextpnr",
            "YOSYS": "yosys",
            "ICARUS": "icarus",
            "VERILATOR": "verilator",
            "GHDL": "ghdl",
        },
    ),
    ("oauth_accounts", "provider", {"GOOGLE": "google", "GITHUB": "github"}),
    (
        "files",
        "language",
        {
            "VERILOG": "verilog",
            "SYSTEMVERILOG": "systemverilog",
            "VHDL": "vhdl",
            "XDC": "xdc",
            "QSF": "qsf",
        },
    ),
    (
        "compilation_jobs",
        "status",
        {
            "WAITING": "waiting",
            "RUNNING": "running",
            "SUCCESS": "success",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
        },
    ),
    (
        "compilation_jobs",
        "toolchain",
        {
            "YOSYS_NEXTPNR": "yosys-nextpnr",
            "YOSYS": "yosys",
            "ICARUS": "icarus",
            "VERILATOR": "verilator",
            "GHDL": "ghdl",
        },
    ),
    (
        "simulation_jobs",
        "status",
        {
            "WAITING": "waiting",
            "RUNNING": "running",
            "SUCCESS": "success",
            "FAILED": "failed",
            "CANCELLED": "cancelled",
        },
    ),
    (
        "simulation_jobs",
        "simulator",
        {"ICARUS": "icarus", "VERILATOR": "verilator", "GHDL": "ghdl"},
    ),
    (
        "artifacts",
        "job_type",
        {"COMPILATION": "compilation", "SIMULATION": "simulation"},
    ),
    (
        "artifacts",
        "artifact_type",
        {
            "BITSTREAM": "bitstream",
            "LOG": "log",
            "VCD": "vcd",
            "JSON_REPORT": "json_report",
        },
    ),
    (
        "job_logs",
        "job_type",
        {"COMPILATION": "compilation", "SIMULATION": "simulation"},
    ),
    (
        "job_logs",
        "level",
        {"INFO": "info", "WARN": "warn", "ERROR": "error"},
    ),
    (
        "ai_messages",
        "role",
        {"USER": "user", "ASSISTANT": "assistant", "SYSTEM": "system"},
    ),
    (
        "audit_logs",
        "event_type",
        {
            "REGISTER": "register",
            "LOGIN_SUCCESS": "login_success",
            "LOGIN_FAILED": "login_failed",
            "OAUTH_LOGIN": "oauth_login",
            "LOGOUT": "logout",
            "PASSWORD_CHANGED": "password_changed",
            "SESSION_REVOKED": "session_revoked",
            "ACCOUNT_LOCKED": "account_locked",
            "ACCOUNT_DISABLED": "account_disabled",
            "ACCOUNT_ENABLED": "account_enabled",
            "ROLE_CHANGED": "role_changed",
            "PROFILE_UPDATED": "profile_updated",
        },
    ),
]


def upgrade() -> None:
    for table, column, mapping in _ENUM_FIXES:
        for legacy, normalized in mapping.items():
            op.execute(
                f"UPDATE {table} SET {column} = '{normalized}' "
                f"WHERE {column} = '{legacy}'"
            )


def downgrade() -> None:
    for table, column, mapping in _ENUM_FIXES:
        for legacy, normalized in mapping.items():
            op.execute(
                f"UPDATE {table} SET {column} = '{legacy}' "
                f"WHERE {column} = '{normalized}'"
            )
