# BOTS/loggerbot.py


import logging
import os

class Logger:
    def __init__(self, name="ALL", logfile="logs/general.log", console=False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        # Удаляем старые обработчики, чтобы не дублировались логи
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Файловый лог
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Консольный лог
        if console:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def get_logger(self):
        return self.logger
