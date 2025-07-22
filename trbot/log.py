import os
import enum, sys

from colorama import Fore, Style

class LogLevel(enum.Enum):
    DEBUG = enum.auto()
    WARN = enum.auto()
    INFO = enum.auto()
    ERROR = enum.auto()
    FATAL = enum.auto()

    def __str__(self) -> str:
        match self:
            case LogLevel.DEBUG:
                return "DEBUG"
            case LogLevel.WARN:
                return "WARN"
            case LogLevel.INFO:
                return "INFO"
            case LogLevel.ERROR:
                return "ERROR"
            case LogLevel.FATAL:
                return "FATAL"

    def color_codes(self) -> str:
        match self:
            case LogLevel.DEBUG:
                return Style.DIM
            case LogLevel.INFO:
                # INFO logs should just be the default color
                return ""
            case LogLevel.WARN:
                return Fore.YELLOW
            case LogLevel.ERROR:
                return Fore.RED
            case LogLevel.FATAL:
                return Fore.RED + Style.BRIGHT


_ENABLE_COLOR_LOGS: bool = True
_LOG_OUTPUT_PATH: str | None = None
_MIN_LOG_LEVEL: LogLevel = LogLevel.DEBUG

def init(
    log_output_dir: str,
    enable_color_logs: bool = True,
    min_log_level: LogLevel = LogLevel.DEBUG
) -> None:
    global _ENABLE_COLOR_LOGS, _LOG_OUTPUT_PATH

    _ENABLE_COLOR_LOGS = enable_color_logs
    if not os.path.exists(log_output_dir):
        os.mkdir(log_output_dir)

    _LOG_OUTPUT_PATH = f"{log_output_dir}/logs.txt"
    set_level(min_log_level)

def set_level(level: LogLevel) -> None:
    global _MIN_LOG_LEVEL
    _MIN_LOG_LEVEL = level

def log(level: LogLevel, msg: str) -> None:
    if level.value < _MIN_LOG_LEVEL.value:
        return

    output: str = f"{str(level)}: {msg}"
    if _ENABLE_COLOR_LOGS:
        colored_output = level.color_codes() + output + Style.RESET_ALL
        print(colored_output)
    else:
        print(output)

    if _LOG_OUTPUT_PATH is not None:
        with open(_LOG_OUTPUT_PATH, "a") as f:
            print(output, file=f)

def debug(msg: str) -> None:
    log(LogLevel.DEBUG, msg)

def info(msg: str) -> None:
    log(LogLevel.INFO, msg)

def warn(msg: str) -> None:
    log(LogLevel.WARN, msg)

def error(msg: str) -> None:
    log(LogLevel.ERROR, msg)

def fatal(msg: str) -> None:
    log(LogLevel.FATAL, msg)
    sys.exit(1)
