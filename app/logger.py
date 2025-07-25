from dataclasses import dataclass
from loguru import logger as builtin_logger


@dataclass
class Logger:
    """
    Custom logger class for logging [debug, info, warning, error]

    Args
    filepath(str) :  File path of log file. If file exist app will continue logging if not exists create a new one.
    rotation(str) :  Log file size limit. When log file reach given size create new log file and old log file saved current timestamp.
    """

    filepath:str
    rotation:int

    def __post_init__(self,)->None:
        self.logger = builtin_logger
        self.logger.remove(0)
        msg_format = "[{time:YYYY-MM-DD HH:mm:ss}] | {level} | [{module}:{function}:{line}] | [{message}]"
        self.logger.add(sink=self.filepath, rotation=self.rotation, encoding="utf-8", format=msg_format)


    def debug(self,message)->None:
        self.logger.opt(depth=1).debug(message)


    def info(self,message)->None:
        self.logger.opt(depth=1).info(message)


    def warning(self, message)->None:
        self.logger.opt(depth=1).warning(message)


    def error(self,message)->None:
        self.logger.opt(depth=1).error(message)


if __name__ == "__main__":
    pass
