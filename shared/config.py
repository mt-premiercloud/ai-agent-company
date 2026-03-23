"""Configuration loader — reads .env and exposes settings."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# GCP
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "pcagentspace")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
VERTEX_AI_MODEL = os.getenv("VERTEX_AI_MODEL", "gemini-3.1-pro-preview")

# Jira
JIRA_URL = os.getenv("JIRA_URL", "https://mohamdti.atlassian.net")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "mohamdti@gmail.com")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")


def get_logger(name: str) -> logging.Logger:
    """Create a logger with consistent formatting and debug level."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)-30s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
    return logger
