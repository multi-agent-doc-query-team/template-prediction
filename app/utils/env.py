from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from app.utils.constants import ENV_FILE
import os

@dataclass(frozen=True)
class Env:
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

def load_environment(env_file: Path = ENV_FILE) -> Env:
    load_dotenv(env_file, override=False)
    debug = os.getenv("DEBUG", "false").strip().casefold()
    if debug not in ("true", "1", "yes", "on", "false", "0", "no", "off", ""):
        raise ValueError("DEBUG must be true or false.")
    enabled = debug in ("true", "1", "yes", "on")
    level = os.getenv("LOG_LEVEL", "").strip().upper()
    level = level or ("DEBUG" if enabled else "INFO")
    if level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.")
    return Env(DEBUG=enabled, LOG_LEVEL=level)
