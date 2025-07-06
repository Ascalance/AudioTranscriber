import os
import logging

# Always resolve log path to project root, not src/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
LOG_PATH = os.path.join(PROJECT_ROOT, "Logs", "log.txt")

import warnings

def configure_logging():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(LOG_PATH, encoding='utf-8')]
    )
    # Ensure root logger captures all warnings
    logging.getLogger().setLevel(logging.INFO)
    # Redirect Python warnings to logging
    def log_warning(message, category, filename, lineno, file=None, line=None):
        logging.warning(f'{category.__name__}: {message} ({filename}:{lineno})')
    warnings.showwarning = log_warning

def start_new_log_session():
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n--- New Session ---\n")

def end_log_session():
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("--- End Session ---\n\n\n")
