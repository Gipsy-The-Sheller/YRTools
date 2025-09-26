import sys
import logging
from PyQt5.QtCore import QCoreApplication

logger = logging.getLogger(__name__)

def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常捕获"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical("未捕获的异常", 
        exc_info=(exc_type, exc_value, exc_traceback))
    
    # 尝试安全退出
    if QCoreApplication.instance():
        QCoreApplication.instance().exit(1)

sys.excepthook = handle_exception 