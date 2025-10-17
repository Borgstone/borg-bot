import logging, sys, os
from logging.handlers import RotatingFileHandler
import structlog
LOG_PATH = os.environ.get("LOG_PATH", "/app/logs/borg.jsonl")
def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    fh = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
    fh.setLevel(logging.INFO); fh.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger(); root.addHandler(fh)
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    return structlog.get_logger("borg")
