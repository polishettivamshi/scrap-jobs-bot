import os
import logging
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Define formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Rotating File Handler: max 10MB (10 * 1024 * 1024 bytes), max 2 files total (1 active + 1 backup)
file_handler = RotatingFileHandler("logs/app.log", maxBytes=10 * 1024 * 1024, backupCount=1)
file_handler.setFormatter(formatter)

# Console handler to output to terminal/Render stdout
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Configure the logger
logger = logging.getLogger("scraper")
logger.setLevel(logging.INFO)

# Avoid adding duplicate handlers if the module is re-imported
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def log_print(*args, **kwargs):
    # standard print support: join arguments by space
    msg = " ".join(str(arg) for arg in args)
    logger.info(msg)
