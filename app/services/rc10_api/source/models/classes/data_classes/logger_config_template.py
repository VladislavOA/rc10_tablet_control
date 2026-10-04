import logging
import os
import pathlib
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class LoggerTemplate:
    enable_logger: bool = True
    enable_logfile: bool = False
    logger: logging.Logger = None
    logfile_path: pathlib.Path = Path(
        f'logfiles_[{os.path.basename(sys.argv[0])}]'
    )
    logfile_name: pathlib.Path = Path(
        f"{datetime.now().strftime('__%d.%m.%Y__%H')}.00__.log"
    )
    logfile_level: int = logging.INFO
    log_std_level: int = logging.DEBUG
    show_std_traceback: bool = False
