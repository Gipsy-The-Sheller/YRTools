# Copyright (C) 2025 Zhi-Jie Xu & Yi-Yang Jia
# 
# This file is part of YRTools.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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