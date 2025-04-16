import atexit
import json
import logging
import logging.config
import traceback
import os

CURRENT_FILE_PATH = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR_PATH = os.path.dirname(CURRENT_FILE_PATH)

LOG_FILE_PATH = os.path.join(PARENT_DIR_PATH, 'logs', 'pygriffin.log.json')
LOG_ROTATE_FILE_PATH = os.path.join(PARENT_DIR_PATH, 'logs', 'pygriffin.rotate.log.json')
DAMENG_LOG_FILE_PATH = os.path.join(PARENT_DIR_PATH, 'logs', 'pygriffin.dameng.log.json')

class JsonFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)

    def _open(self):
        # Open the file and write '[' if it's a new file
        file = super()._open()
        if os.path.getsize(self.baseFilename) == 0:  # Check if file is empty
            file.write('[')
        return file

    def close(self):
        # Move the file pointer back to overwrite the last comma, if any
        if self.stream is not None:
            self.stream.seek(max(self.stream.tell() - 2, 0))
            self.stream.write(']')
        super().close()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:

        record_native_keys = {'args', 'created', 'exc_info', 'exc_text', 'filename', 'funcName', 'levelname', 'levelno',
                              'lineno', 'module', 'msecs', 'msg', 'name', 'pathname', 'process', 'processName',
                              'relativeCreated', 'stack_info', 'thread', 'threadName'}

        basic_info = {
            "time": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
        }

        user_info = {
            "message": record.getMessage(),
        }

        # 将额外的字段加入日志记录，排除内置字段
        for key, value in record.__dict__.items():
            if key not in record_native_keys and key != 'exc_info':
                user_info[key] = value

        addition_info = {
            "pathname": record.pathname,
            "lineno": record.lineno,
        }

        log_record = {
            **basic_info,
            **user_info,
            **addition_info
        }

        # 添加异常信息（如果有）
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            log_record['exception'] = {
                "exc_type": str(exc_type),
                "exc_value": str(exc_value),
                "exc_traceback": traceback.format_exception(exc_type, exc_value, exc_traceback)
            }

        return json.dumps(log_record, ensure_ascii=False)


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'json': {
            '()': JsonFormatter,
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'rotating_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'json',
            'filename': LOG_ROTATE_FILE_PATH,
            'mode': 'a',
            'maxBytes': 1048576,
            'backupCount': 5
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'json',
            'filename': LOG_FILE_PATH,
            'mode': 'a'
        },
        'dameng_file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'json',
            'filename': DAMENG_LOG_FILE_PATH,
            'mode': 'a'
        }
    },
    'loggers': {
        'pygriffin.generation.mutator': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'json': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'dameng_json': {
            'handlers': ['dameng_file'],
            'level': 'DEBUG',
            'propagate': False
        },
        '__main__': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False
        }
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    }
}


# 应用日志配置
def setup_logging():
    # pass
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)
