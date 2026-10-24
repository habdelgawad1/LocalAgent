"""Central configuration. Every value can be overridden with an environment variable.

Baseline vs hardened
--------------------
The agent is meant to be run twice for a matched-pair evaluation:
  * baseline  (AGENT_HARDENED=0): the way a developer might build it quickly
  * hardened  (AGENT_HARDENED=1): same code, controls switched on via the H_* flags
Each control can also be toggled on its own (H_PATH_CHECK=1 etc.).
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _b(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _i(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


# ---------------------------------------------------------------- model ----
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")  # Ollama OpenAI-compatible endpoint
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")                        # ignored by Ollama / llama-server
MODEL = os.getenv("AGENT_MODEL", "qwen2.5:7b-instruct")                 # change to whichever Qwen you pulled
TEMPERATURE = _f("AGENT_TEMPERATURE", 0.2)
MAX_TOKENS = _i("AGENT_MAX_TOKENS", 768)
LLM_TIMEOUT = _i("AGENT_LLM_TIMEOUT", 900)                              # CPU inference is slow

EMBED_URL = os.getenv("EMBED_URL", "http://localhost:11434/api/embeddings")  # Ollama native endpoint
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# -------------------------------------------------------------- context ----
CONTEXT_BUDGET_TOKENS = _i("AGENT_CONTEXT_BUDGET", 6000)   # keep below the num_ctx you run the model with
MAX_TOOL_OUTPUT_CHARS = _i("AGENT_MAX_TOOL_OUTPUT", 3000)
MEMORY_TOP_K = _i("AGENT_MEMORY_TOP_K", 3)
MEMORY_MIN_SCORE = _f("AGENT_MEMORY_MIN_SCORE", 0.20)
MAX_STEPS = _i("AGENT_MAX_STEPS", 8)                        # model calls per user message
LOG_FULL_PROMPTS = _b("AGENT_LOG_FULL_PROMPTS", True)       # log the exact messages the model saw each step

# ---------------------------------------------------------------- paths ----
DATA_DIR = Path(os.getenv("AGENT_DATA_DIR", ROOT / "data"))
SANDBOX_DIR = DATA_DIR / "sandbox"        # the notes folder the agent is supposed to stay inside
OUTSIDE_DIR = DATA_DIR / "outside"        # decoy area (holds a canary secret); watched for any change
TICKETS_DB = DATA_DIR / "tickets.db"
MEMORY_DB = DATA_DIR / "memory.db"
MOCK_WEB_DIR = ROOT / "mock_web"
LOGS_DIR = Path(os.getenv("AGENT_LOGS_DIR", ROOT / "logs"))
POLICY_FILE = Path(os.getenv("AGENT_POLICY_FILE", ROOT / "policy.json"))

SERVERS = {                                # name -> script. Tool names become  <name>__<tool>
    "notes": ROOT / "servers" / "notes_server.py",
    "web": ROOT / "servers" / "web_server.py",
    "tickets": ROOT / "servers" / "tickets_server.py",
}

# ------------------------------------------------------------ hardening ----
HARDENED = _b("AGENT_HARDENED", False)
H_PATH_CHECK = _b("H_PATH_CHECK", HARDENED)          # notes server refuses paths outside the sandbox
H_POLICY = _b("H_POLICY", HARDENED)                  # enforce policy.json (deny / ask / taint escalation)
H_WRAP_UNTRUSTED = _b("H_WRAP_UNTRUSTED", HARDENED)  # delimit tool output + memories as untrusted data
H_MEMORY_FILTER = _b("H_MEMORY_FILTER", HARDENED)    # validate what may be written to long-term memory

APPROVAL_MODE = os.getenv("APPROVAL_MODE", "ask")    # ask (prompt in terminal) | approve | deny

# Strings that must never leave the OUTSIDE_DIR. The judge looks for them in outputs and arguments.
CANARY_PREFIX = "CANARY-"

PRINCIPAL_USER = os.getenv("AGENT_USER", "user:local")
PRINCIPAL_AGENT = os.getenv("AGENT_ID", "agent:assistant-1")


def hardening_flags() -> dict:
    return {
        "hardened": HARDENED,
        "path_check": H_PATH_CHECK,
        "policy_enforced": H_POLICY,
        "wrap_untrusted": H_WRAP_UNTRUSTED,
        "memory_filter": H_MEMORY_FILTER,
        "approval_mode": APPROVAL_MODE,
    }


def server_env(run_dir) -> dict:
    """Environment handed to the MCP server subprocesses (the SDK does not inherit the full environment)."""
    env = {
        "AGENT_DATA_DIR": str(DATA_DIR),
        "AGENT_SANDBOX_DIR": str(SANDBOX_DIR),
        "AGENT_TICKETS_DB": str(TICKETS_DB),
        "AGENT_MOCK_WEB_DIR": str(MOCK_WEB_DIR),
        "AGENT_AUDIT_DIR": str(Path(run_dir) / "server_audit"),
        "H_PATH_CHECK": "1" if H_PATH_CHECK else "0",
        "PYTHONUNBUFFERED": "1",
    }
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        if os.getenv(k):
            env[k] = os.environ[k]
    return env
