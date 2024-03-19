from __future__ import annotations

import logging


class Formatter(logging.Formatter):
    ansi_1 = "\x1b[38;5;68m"
    ansi_2 = "\x1b[38;5;117m"
    asci_3 = "\x1b[38;5;147m"
    rst = "\x1b[0m"
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    bold_red_underline = "\x1b[31;1;4m"
    reset = "\x1b[0m"
    blue = "\x1b[34m"
    green = "\x1b[32m"
    cyan = "\x1b[36m"
    magenta = "\x1b[35m"

    __format = f"{ansi_1}%(asctime)s{rst} | {ansi_2}%(levelname)s{rst} | {asci_3}%(name)s{rst} | %(message)s"
    __issue_format = f"{ansi_1}%(asctime)s{rst} | {ansi_2}%(levelname)s{rst} | {asci_3}%(name)s{rst} | {bold_red_underline}%(message)s{rst}"
    __warning_format = f"{ansi_1}%(asctime)s{rst} | {ansi_2}%(levelname)s{rst} | {asci_3}%(name)s{rst} | {yellow}%(message)s{rst}"

    def __init__(self, *args, **kwargs):
        super().__init__(self.__format, *args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno == logging.INFO:
            self._style._fmt = self.__format
        elif record.levelno == logging.WARNING:
            self._style._fmt = self.__warning_format
        elif record.levelno == logging.ERROR:
            self._style._fmt = self.__issue_format
        elif record.levelno == logging.CRITICAL:
            self._style._fmt = self.__issue_format
        else:
            self._style._fmt = self.__format
        return super().format(record)
