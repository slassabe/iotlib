import logging
import inspect
import os

logger = logging.getLogger('test')

class Colors:
    """ ANSI color codes """
    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    LIGHT_GRAY = "\033[0;37m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    END = "\033[0m"

class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://alexandra-zaharia.github.io/posts/make-your-own-custom-color-formatter-with-python-logging/"""

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.fmt,
            logging.INFO: Colors.GREEN + self.fmt + Colors.END,
            logging.WARNING: Colors.BLUE + self.fmt + Colors.END,
            logging.ERROR: Colors.RED + Colors.BOLD + self.fmt + Colors.END,
            logging.CRITICAL: Colors.BROWN + self.fmt + Colors.END
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def init_logger(_logger, debug=False):
    _logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Define format for logs
    FORMAT = '%(levelname)8s | %(name)s | %(filename)s:%(lineno)s |  %(funcName)s(): %(message)s'

    # Create stdout handler for logging to the console (logs all five levels)
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(CustomFormatter(FORMAT))

    # Add both handlers to the logger
    _logger.addHandler(stdout_handler)


def log_it(summary):
    # https://stackoverflow.com/questions/10973362/python-logging-function-name-file-name-line-number-using-a-single-file
    _func = inspect.currentframe().f_back.f_code
    _location = "[" +os.path.basename(_func.co_filename)
    _location += ":" + str(_func.co_firstlineno)
    _location += "] " + "=" * (30 - len(_location)) + " "
    _calling = _func.co_name.replace('test_', '')
    _calling += ":" + " " * (20 - len(_calling))
    _trailer = " " + "=" * (60 - len(summary))
    print(Colors.DARK_GRAY + _location + _calling + summary + _trailer + '\x1b[0m')

def get_broker_name():
    return 'localhost'
    #return 'test.mosquitto.org'
    #return 'groseille.back.internal'

init_logger(logging.getLogger('test'), debug=False)
init_logger(logging.getLogger('iotlib'), debug=False)
init_logger(logging.getLogger('utilities'), debug=False)

