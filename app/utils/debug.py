from logging.config import dictConfig
from app.utils.env import Env
import logging

def get_logger(name: str = "app") -> logging.Logger:
    return logging.getLogger(name)

def configure_logging(settings: Env) -> None:
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "standard",
            },
        },
        "root": {"level": "WARNING", "handlers": ["console"]},
        "loggers": {
            name: {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            }
            for name in ("app", "uvicorn", "uvicorn.error", "uvicorn.access")
        },
    })
