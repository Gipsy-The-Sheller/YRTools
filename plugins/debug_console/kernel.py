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
#

import sys
import os
import logging
import threading
import queue
import time
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, 
                             QPushButton, QCheckBox, QLabel, QComboBox, QSpinBox,
                             QGroupBox, QFormLayout, QSplitter, QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor, QTextCharFormat
import platform

class LogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到队列"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        
    def emit(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'funcName': record.funcName,
            'lineno': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        try:
            self.log_queue.put_nowait(log_entry)
        except queue.Full:
            pass  # 如果队列满了，丢弃日志

class LogMonitorThread(QThread):
    """日志监控线程"""
    log_received = pyqtSignal(dict)
    
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        self.running = True
        
    def run(self):
        while self.running:
            try:
                # 非阻塞获取日志
                log_entry = self.log_queue.get(timeout=0.1)
                self.log_received.emit(log_entry)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Log monitor error: {e}")
                
    def stop(self):
        self.running = False

class YRDebugConsole(QWidget):
    """YR Debug Console主窗口"""
    
    def __init__(self, plugin_path=None):
        super().__init__()
        self.plugin_path = plugin_path
        self.log_queue = queue.Queue(maxsize=1000)
        self.log_handler = None
        self.monitor_thread = None
        self.log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.current_level = 'DEBUG'
        self.auto_scroll = True
        self.max_lines = 1000
        
        self.setup_logging()
        self.init_ui()
        self.start_monitoring()
        
    def setup_logging(self):
        """设置日志系统"""
        # 获取根日志记录器
        root_logger = logging.getLogger()
        
        # 创建自定义处理器
        self.log_handler = LogHandler(self.log_queue)
        self.log_handler.setLevel(logging.DEBUG)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s [%(threadName)s] %(name)s.%(funcName)s:%(lineno)d - %(levelname)s - %(message)s'
        )
        self.log_handler.setFormatter(formatter)
        
        # 添加到根日志记录器
        root_logger.addHandler(self.log_handler)
        
        # 设置日志级别
        root_logger.setLevel(logging.DEBUG)
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("YR Debug Console")
        self.setGeometry(100, 100, 1000, 700)
        
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 控制面板
        self.setup_control_panel(main_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 日志显示区域
        self.setup_log_display(splitter)
        
        # 系统信息面板
        self.setup_system_info(splitter)
        
        # 设置分割器比例
        splitter.setSizes([700, 300])
        
    def setup_control_panel(self, main_layout):
        """设置控制面板"""
        control_layout = QHBoxLayout()
        
        # 日志级别选择
        level_label = QLabel("Log Level:")
        control_layout.addWidget(level_label)
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(self.log_levels)
        self.level_combo.setCurrentText(self.current_level)
        self.level_combo.currentTextChanged.connect(self.on_level_changed)
        control_layout.addWidget(self.level_combo)
        
        # 最大行数设置
        lines_label = QLabel("Max Lines:")
        control_layout.addWidget(lines_label)
        
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(100, 10000)
        self.max_lines_spin.setValue(self.max_lines)
        self.max_lines_spin.valueChanged.connect(self.on_max_lines_changed)
        control_layout.addWidget(self.max_lines_spin)
        
        # 控制按钮
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_logs)
        control_layout.addWidget(self.clear_btn)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        control_layout.addWidget(self.pause_btn)
        
        # 自动滚动
        self.auto_scroll_checkbox = QCheckBox("Auto Scroll")
        self.auto_scroll_checkbox.setChecked(self.auto_scroll)
        self.auto_scroll_checkbox.toggled.connect(self.toggle_auto_scroll)
        control_layout.addWidget(self.auto_scroll_checkbox)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
    def setup_log_display(self, splitter):
        """设置日志显示区域"""
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        # 日志文本区域
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas" if platform.system() == "Windows" else "Courier New", 9))
        
        # 设置样式（Monokai主题）
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #272822;
                color: #f8f8f2;
                border: 1px solid #3c3c3c;
                font-family: 'Consolas', monospace;
            }
        """)
        
        log_layout.addWidget(self.log_text)
        splitter.addWidget(log_widget)
        
    def setup_system_info(self, splitter):
        """设置系统信息面板"""
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # 系统信息组
        system_group = QGroupBox("System Information")
        system_layout = QFormLayout(system_group)
        
        # 系统信息
        system_info = {
            "Platform": platform.platform(),
            "Python Version": sys.version.split()[0],
            "Architecture": platform.architecture()[0],
            "Processor": platform.processor(),
            "Machine": platform.machine(),
            "Node": platform.node(),
            "System": platform.system(),
            "Release": platform.release(),
            "Version": platform.version()
        }
        
        for key, value in system_info.items():
            label = QLabel(str(value))
            label.setWordWrap(True)
            system_layout.addRow(f"{key}:", label)
            
        info_layout.addWidget(system_group)
        
        # 日志统计组
        stats_group = QGroupBox("Log Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.stats_labels = {}
        for level in self.log_levels:
            label = QLabel("0")
            label.setStyleSheet(f"color: {self.get_level_color(level)}")
            self.stats_labels[level] = label
            stats_layout.addRow(f"{level}:", label)
            
        info_layout.addWidget(stats_group)
        
        # 内存使用情况
        memory_group = QGroupBox("Memory Usage")
        memory_layout = QVBoxLayout(memory_group)
        
        self.memory_label = QLabel("Loading...")
        self.memory_label.setWordWrap(True)
        memory_layout.addWidget(self.memory_label)
        
        # 定时器更新内存信息
        self.memory_timer = QTimer()
        self.memory_timer.timeout.connect(self.update_memory_info)
        self.memory_timer.start(2000)  # 每2秒更新一次
        
        info_layout.addWidget(memory_group)
        
        info_layout.addStretch()
        splitter.addWidget(info_widget)
        
    def start_monitoring(self):
        """开始监控日志"""
        self.monitor_thread = LogMonitorThread(self.log_queue)
        self.monitor_thread.log_received.connect(self.on_log_received)
        self.monitor_thread.start()
        
        # 添加启动消息
        self.add_log_message("YR Debug Console started", "INFO")
        
    def on_log_received(self, log_entry):
        """处理接收到的日志"""
        level = log_entry['level']
        
        # 检查日志级别过滤
        if self.log_levels.index(level) < self.log_levels.index(self.current_level):
            return
            
        # 格式化日志消息
        timestamp = log_entry['timestamp'].strftime("%H:%M:%S.%f")[:-3]
        message = f"[{timestamp}] [{level}] {log_entry['logger']}.{log_entry['funcName']}:{log_entry['lineno']} - {log_entry['message']}"
        
        # 添加颜色格式
        self.add_colored_log(message, level)
        
        # 更新统计
        self.update_stats(level)
        
    def add_colored_log(self, message, level):
        """添加带颜色的日志"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # 设置颜色格式
        char_format = QTextCharFormat()
        char_format.setForeground(QColor(self.get_level_color(level)))
        cursor.setCharFormat(char_format)
        
        # 插入文本
        cursor.insertText(message + "\n")
        
        # 限制最大行数
        if self.log_text.document().blockCount() > self.max_lines:
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 
                              self.log_text.document().blockCount() - self.max_lines)
            cursor.removeSelectedText()
            
        # 自动滚动
        if self.auto_scroll:
            self.log_text.moveCursor(QTextCursor.End)
            
    def add_log_message(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_message = f"[{timestamp}] [{level}] YRDebugConsole - {message}"
        self.add_colored_log(formatted_message, level)
        
    def get_level_color(self, level):
        """获取日志级别对应的颜色"""
        colors = {
            'DEBUG': '#75715e',    # 灰色
            'INFO': '#66d9ef',     # 青色
            'WARNING': '#e6db74', # 黄色
            'ERROR': '#f92672',   # 红色
            'CRITICAL': '#ff0000' # 深红色
        }
        return colors.get(level, '#f8f8f2')
        
    def update_stats(self, level):
        """更新日志统计"""
        if level in self.stats_labels:
            current_count = int(self.stats_labels[level].text())
            self.stats_labels[level].setText(str(current_count + 1))
            
    def update_memory_info(self):
        """更新内存使用信息"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            info_text = f"""
RSS: {memory_info.rss / 1024 / 1024:.1f} MB
VMS: {memory_info.vms / 1024 / 1024:.1f} MB
Memory %: {memory_percent:.1f}%
            """.strip()
            
            self.memory_label.setText(info_text)
        except ImportError:
            self.memory_label.setText("psutil not available")
        except Exception as e:
            self.memory_label.setText(f"Error: {str(e)}")
            
    def on_level_changed(self, level):
        """日志级别改变"""
        self.current_level = level
        
    def on_max_lines_changed(self, value):
        """最大行数改变"""
        self.max_lines = value
        
    def clear_logs(self):
        """清除日志"""
        self.log_text.clear()
        # 重置统计
        for label in self.stats_labels.values():
            label.setText("0")
        self.add_log_message("Logs cleared", "INFO")
        
    def toggle_pause(self):
        """切换暂停状态"""
        if self.monitor_thread and self.monitor_thread.isRunning():
            if self.pause_btn.text() == "Pause":
                self.monitor_thread.stop()
                self.pause_btn.setText("Resume")
                self.add_log_message("Log monitoring paused", "WARNING")
            else:
                self.monitor_thread = LogMonitorThread(self.log_queue)
                self.monitor_thread.log_received.connect(self.on_log_received)
                self.monitor_thread.start()
                self.pause_btn.setText("Pause")
                self.add_log_message("Log monitoring resumed", "INFO")
                
    def toggle_auto_scroll(self, enabled):
        """切换自动滚动"""
        self.auto_scroll = enabled
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread.wait()
            
        # 移除日志处理器
        if self.log_handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.log_handler)
            
        event.accept()

class YRDebugConsole_entry:
    """插件入口类"""
    def run(self):
        return YRDebugConsole()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 测试日志
    logger = logging.getLogger("test")
    logger.info("This is a test info message")
    logger.warning("This is a test warning message")
    logger.error("This is a test error message")
    
    console = YRDebugConsole()
    console.show()
    
    sys.exit(app.exec_())
