# logger_manager.py
import logging

class LoggerManager:
    @staticmethod
    def setup_logger(name: str = __name__):
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            file_handler = logging.FileHandler('categorizer.log', encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger
