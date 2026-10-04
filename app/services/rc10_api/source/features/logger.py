import logging
import sys
from dataclasses import fields
from datetime import datetime
from pathlib import Path

from rc10_api.source.models.classes.data_classes.logger_config_template import (
    LoggerTemplate
)
from rc10_api.source.models.constants import LOGGER_NAME


def set_logger(**kwargs) -> None | logging.Logger:
    logger_template = LoggerTemplate()
    for key, value in kwargs.items():
        if key in [field.name for field in fields(logger_template)]:
            setattr(logger_template, key, value)
    if not isinstance(logger_template.logger, logging.Logger):
        logger_template.logger = logging.getLogger(LOGGER_NAME)
        logger_template.logger.propagate = False
    else:  # means logger has been overriden by user
        return logger_template.logger
    logger = logger_template.logger
    if not logger_template.enable_logger:
        logger.handlers.clear()
    else:
        logger.setLevel(logging.DEBUG)
        std_formatter = StdFormatter()
        std_formatter.set_exceptions_enabled(
            logger_template.show_std_traceback
        )
        std_handler = logging.StreamHandler(sys.stdout)
        std_handler.setLevel(logger_template.log_std_level)
        std_handler.setFormatter(std_formatter)
        logger.addHandler(std_handler)
        if not logger_template.enable_logfile:
            logger.debug('Logging without file')
        else:
            file_formatter = FileFormatter()
            Path.mkdir(
                Path(logger_template.logfile_path),
                parents=True,
                exist_ok=True
            )
            log_file_path = (
                Path(logger_template.logfile_path)
                / Path(str(logger_template.logfile_name))
            )
            file_handler = FirstRowFileHandler(log_file_path)
            file_handler.setLevel(logger_template.logfile_level)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            logger.debug(f'Logging to the file [{log_file_path}]')
    return logger


class FirstRowFileHandler(logging.FileHandler):
    def __init__(self, filename, *args):
        super().__init__(filename, *args)
        self.first_run = True
        self.filename = filename
        self.separator = (
            f"{'=' * 7} rc10_api Launch "
            f"{datetime.now().strftime('[%d.%m.%Y %H:%M:%S]')} {'=' * 70}"
        )

    def emit(self, record):
        if self.first_run:
            self.stream.write(f'\n\n\n{self.separator}\n\n\n')
        self.first_run = False
        super().emit(record)


class FileFormatter(logging.Formatter):
    def __init__(self):
        logging.Formatter.__init__(self)
        self.is_last_msg_exception = False

    def format(self, record):
        self._style._fmt = (
            '[%(asctime)s] %(levelname)-8s '
            '[%(filename)s/%(funcName)s:%(lineno)s]  %(message)s'
        )
        return super().format(record)

    def formatException(self, exc_info) -> str:
        self.is_last_msg_exception = True
        return '\n' + super().formatException(exc_info)

    def formatMessage(self, record) -> str:
        if self.is_last_msg_exception:
            self.is_last_msg_exception = False
            return '\n' + super().formatMessage(record)
        return super().formatMessage(record)


class StdFormatter(logging.Formatter):
    _enable_exceptions: bool = False

    def format(self, record):
        color = {
            logging.CRITICAL: (31, 31),
            logging.ERROR: (31, 31),
            logging.FATAL: (31, 31),
            logging.WARNING: (33, 33),
            logging.DEBUG: (36, 37),
            logging.INFO: (32, 32)
        }.get(record.levelno, 0)
        self._style._fmt = (
            f'\033[37m[%(asctime)s]\033[0m \033[{color[0]}m%(levelname)-8s'
            f'\033[0m \033[{color[1]}m%(message)s\033[0m'
        )
        return super().format(record)

    def set_exceptions_enabled(self, enable: bool):
        self._enable_exceptions = enable

    def formatException(self, exc_info) -> str:
        if self._enable_exceptions:
            return super().formatException(exc_info)
        return ''
