import logging
from logging.handlers import RotatingFileHandler
import os

from app.config import settings


def setup_logging():
   
    logger = logging.getLogger("app")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return
    
    os.makedirs("logs", exist_ok=True)

    console_handler = logging.StreamHandler()
    if settings.debug:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    file_handler = RotatingFileHandler("logs/app.log", maxBytes=10_000_000, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

