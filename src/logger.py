from loguru import logger
import sys

def setup_logger(log_path: str):
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    logger.add(log_path, rotation="10 MB", retention="10 days", level="INFO")
    return logger 