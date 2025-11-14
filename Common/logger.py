import logging
import os
from logging.handlers import RotatingFileHandler
from Common.config import Config

class Logger:
    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        """初始化日志配置"""
        config = Config.get_instance()
        log_dir = config.get('PATH', 'logs')
        log_file = os.path.join(log_dir, 'gobang_ai.log')

        # 创建日志器
        self._logger = logging.getLogger('GobangAI')
        self._logger.setLevel(logging.DEBUG)

        # 避免重复添加处理器
        if self._logger.handlers:
            return

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # 文件处理器（轮转日志，最大10MB，保留5个备份）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # 添加处理器
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    def debug(self, message):
        """调试日志"""
        self._logger.debug(message)

    def info(self, message):
        """信息日志"""
        self._logger.info(message)

    def warning(self, message):
        """警告日志"""
        self._logger.warning(message)

    def error(self, message):
        """错误日志"""
        self._logger.error(message)

    def critical(self, message):
        """严重错误日志"""
        self._logger.critical(message)

    def exception(self, message):
        """异常日志（包含堆栈信息）"""
        self._logger.exception(message)

    @staticmethod
    def get_instance():
        """获取单例实例"""
        if Logger._instance is None:
            Logger._instance = Logger()
        return Logger._instance