import contextlib
import time
import logging
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class PerformanceMonitor(QObject):
    update_stats = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.node_count = 0
        self.last_render = 0
        
    @contextlib.contextmanager
    def log_operation(self, op_name):
        start = time.time()
        yield
        cost = (time.time() - start) * 1000
        logger.debug("操作耗时: %.2fms", cost)
        
    def update_scene_stats(self, scene):
        current_time = time.time()
        time_diff = current_time - self.last_render
        self.node_count = len(scene.items())
        fps = 1/time_diff if self.last_render > 0 and time_diff > 0.001 else 0  # 安全除法
        
        self.update_stats.emit({
            'nodes': self.node_count,
            'fps': fps
        })
        self.last_render = current_time 