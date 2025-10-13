import enum, os, sys
from typing import NoReturn

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


class Logger:
    def __init__(
        self,
        prefix: str,
        log_output_dir: str,
        print_to_screen: bool,
        enable_color_logs: bool = True,
        min_log_level: LogLevel = LogLevel.DEBUG
    ) -> None:
        self.prefix: str = prefix
        self.enable_color_logs: bool = enable_color_logs
        self.print_to_screen: bool = print_to_screen
        self.log_output_path: str = ""
        self.log_str: str = ""
        self.update_out_dir(log_output_dir)
        self.set_min_level(min_log_level)

    def update_out_dir(self, log_output_dir: str) -> None:
        if not os.path.exists(log_output_dir):
            os.mkdir(log_output_dir)

        self.log_output_path = f"{log_output_dir}/{self.prefix}-logs.txt"

    def set_min_level(self, level: LogLevel) -> None:
        self.min_log_level = level

    def log(self, level: LogLevel, msg: str) -> None:
        if level.value < self.min_log_level.value:
            return

        output: str = f"[{self.prefix:4}] {str(level)}: {msg}"
        if self.print_to_screen:
            if self.enable_color_logs:
                colored_output = level.color_codes() + output + Style.RESET_ALL
                print(colored_output)
            else:
                print(output)

    def dump_logs(self, log_output_path: str | None = None) -> None:
        if log_output_path is None:
            log_output_path = self.log_output_path

        with open(log_output_path, "w+") as f:
            f.write(self.log_str)

    def debug(self, msg: str) -> None:
        self.log(LogLevel.DEBUG, msg)

    def info(self, msg: str) -> None:
        self.log(LogLevel.INFO, msg)

    def warn(self, msg: str) -> None:
        self.log(LogLevel.WARN, msg)

    def error(self, msg: str) -> None:
        self.log(LogLevel.ERROR, msg)

    def fatal(self, msg: str) -> NoReturn:
        self.log(LogLevel.FATAL, msg)
        sys.exit(1)

repl_log: Logger = Logger(
    prefix="REPL",
    log_output_dir="trout/logs",
    print_to_screen=True,
    enable_color_logs=True,
    # min_log_level=LogLevel.INFO
    min_log_level=LogLevel.DEBUG
)

bot_log: Logger = Logger(
    prefix="BOT",
    log_output_dir="trout/logs",
    print_to_screen=False,
    enable_color_logs=False,
)

