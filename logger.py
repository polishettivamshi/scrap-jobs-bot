import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Define replacements for icons/emojis to avoid console encoding issues and clean up logs
REPLACEMENTS = {
    "✅": "[OK]",
    "❌": "[ERROR]",
    "⚠️": "[WARNING]",
    "📨": "[Sent]",
    "🕒": "[Time]",
    "📦": "[State]",
    "📡": "[Search]",
    "📂": "[Category]",
    "—": "-",

    "─": "-",
    "═": "=",
    "🚀": "[Job]",
    "💼": "[Role]",
    "🏢": "[Company]",
    "📍": "[Loc]",
    "⏱": "[Type]",
    "🎯": "[Exp]",
    "🕐": "[Posted]",
    "🏷": "[Tags]",
    "🌐": "[Source]",
    "🔗": "[Link]",
    "🔴": "[Red]",
    "🟢": "[Green]",
    "⚫": "[Black]",
    "🔵": "[Blue]",
    "🟠": "[Orange]",
    "🟣": "[Purple]",
}

def clean_icons(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    for icon, replacement in REPLACEMENTS.items():
        text = text.replace(icon, replacement)
    return text

# Safe formatter to prevent any UnicodeEncodeError in console output on Windows
class SafeConsoleFormatter(logging.Formatter):
    def format(self, record):
        s = super().format(record)
        encoding = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
        try:
            return s.encode(encoding, errors='replace').decode(encoding)
        except Exception:
            return s.encode('ascii', errors='replace').decode('ascii')

# Standard formatter for files (using UTF-8)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Rotating File Handler: max 10MB, max 2 files total (1 active + 1 backup), explicitly UTF-8 encoded
file_handler = RotatingFileHandler("logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=1, encoding="utf-8")
file_handler.setFormatter(file_formatter)

# Console handler to output to terminal/Render stdout
console_handler = logging.StreamHandler()
console_handler.setFormatter(SafeConsoleFormatter('%(asctime)s - %(levelname)s - %(message)s'))

# Configure the logger
logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)

# Avoid adding duplicate handlers if the module is re-imported
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_print(*args, **kwargs):
    # Join arguments with spaces, clean icons, and log
    msg = " ".join(str(arg) for arg in args)
    msg = clean_icons(msg)
    logger.info(msg)
