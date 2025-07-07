# BOTS/loggerbot.py


import logging
import os

class Logger:
    def __init__(self, name="ALL", tag = "[ALL]", logfile="LOGS/general.log", console=False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        formatter = logging.Formatter(f"%(asctime)s {tag} [%(levelname)s] %(message)s")

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        general_log = "LOGS/general.log"
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        os.makedirs(os.path.dirname(general_log), exist_ok=True)

        # 🔹 Handler для модуля
        module_handler = logging.FileHandler(logfile, mode="a", encoding="utf-8")
        module_handler.setFormatter(formatter)
        self.logger.addHandler(module_handler)

        # 🔹 Handler для общего лога
        general_handler = logging.FileHandler(general_log, mode="a", encoding="utf-8")
        general_handler.setFormatter(formatter)
        self.logger.addHandler(general_handler)

        # 🔹 Handler для консоли
        if console:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)

    def get_logger(self):
        return self.logger
