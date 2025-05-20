import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger():
    """Configure application logging"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Try to make the directory writable if it's not
    try:
        if not os.access(logs_dir, os.W_OK):
            # Try to create a temp logs directory in /tmp if we can't write to the app logs dir
            logs_dir = "/tmp/app_logs"
            os.makedirs(logs_dir, exist_ok=True)
    except Exception:
        # Fallback to current directory
        logs_dir = "."

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Log format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # File handler with rotation
    log_file = os.path.join(logs_dir, "app.log")
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10,
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except (PermissionError, IOError) as e:
        logger.warning(f"Could not create log file: {e}. Logging to console only.")

    return logger
