import enum


class OAuthProvider(str, enum.Enum):
    GOOGLE = "google"
    GITHUB = "github"


class JobStatus(str, enum.Enum):
    WAITING = "waiting"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Simulator(str, enum.Enum):
    ICARUS = "icarus"
    VERILATOR = "verilator"
    GHDL = "ghdl"


class ArtifactType(str, enum.Enum):
    BITSTREAM = "bitstream"
    LOG = "log"
    VCD = "vcd"
    JSON_REPORT = "json_report"


class JobType(str, enum.Enum):
    COMPILATION = "compilation"
    SIMULATION = "simulation"


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class HdlLanguage(str, enum.Enum):
    VERILOG = "verilog"
    SYSTEMVERILOG = "systemverilog"
    VHDL = "vhdl"
    XDC = "xdc"
    QSF = "qsf"


class AiMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FpgaTarget(str, enum.Enum):
    ICE40 = "ice40"
    ECP5 = "ecp5"
    GENERIC = "generic"


class Toolchain(str, enum.Enum):
    YOSYS_NEXTPNR = "yosys-nextpnr"
    YOSYS = "yosys"
    ICARUS = "icarus"
    VERILATOR = "verilator"
    GHDL = "ghdl"


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class AuditEventType(str, enum.Enum):
    REGISTER = "register"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    OAUTH_LOGIN = "oauth_login"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    SESSION_REVOKED = "session_revoked"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_ENABLED = "account_enabled"
    ROLE_CHANGED = "role_changed"
    PROFILE_UPDATED = "profile_updated"
