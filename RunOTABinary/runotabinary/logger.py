import logging
from pathlib import Path

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    reset = "\033[0m"
    bold = "\033[1m"
    underline = "\033[4m"
    red = "\033[91m"
    green = "\033[32m"
    yellow = "\033[93m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    white = "\033[37m"

    format = "%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"


    FORMATS = {
        logging.DEBUG: yellow + format + reset,
        logging.INFO: cyan + format + reset,
        logging.WARNING: yellow + bold + underline + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: red + bold + underline + format + reset,
    }

    def format(self, record):
        time_fmt = "%H:%M:%S"
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, time_fmt)
        return formatter.format(record)

raw_formatter = logging.Formatter('%(message)s')

def setup_logger(
    name=None, level=logging.INFO, stream=False, file=False, log_file=None, format='color', terminator=None
):
    """To setup as many loggers as you want"""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    formatter = None
    if format == 'raw':
        formatter = raw_formatter
    elif format == 'color':
        formatter = CustomFormatter()

    if file:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)
        if terminator is not None:
            handler.terminator = terminator
        logger.addHandler(handler)

    if stream:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        if terminator is not None:
            handler.terminator = terminator
        logger.addHandler(handler)

    return logger


# default logger
logger = setup_logger(name='default', level=logging.DEBUG, stream=True, format='color')

if __name__ == "__main__":
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")
