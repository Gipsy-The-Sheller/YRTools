from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QIcon
import os
from pathlib import Path

class BasePlugin(QObject):
    # 定义标准信号
    status_changed = pyqtSignal(str)  # 状态更新
    data_ready = pyqtSignal(dict)     # 数据输出
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.widget = None
        
    def create_widget(self):
        """必须由子类实现"""
        raise NotImplementedError
        
    def run(self):
        """执行插件主逻辑"""
        if not self.widget:
            self.widget = self.create_widget()
        return self.widget 

    @classmethod
    def get_icon(cls, plugin_path):
        """获取插件图标，支持多种矢量格式"""
        formats = ['eps', 'emf', 'svg']  # 按优先级排序
        icon_dir = Path(plugin_path).parent
        
        # 搜索所有支持的图标文件
        found = {}
        for f in icon_dir.glob("icon.*"):
            ext = f.suffix[1:].lower()
            if ext in formats:
                found[ext] = f
        
        # 按格式优先级选择
        for fmt in formats:
            if fmt in found:
                return cls._load_vector_icon(found[fmt])
        
        return QIcon()  # 返回空图标

    @staticmethod
    def _load_vector_icon(file_path):
        """加载矢量图标文件"""
        ext = file_path.suffix.lower()
        
        # EPS/EMF需要转换
        if ext in ('.eps', '.emf'):
            try:
                # 使用ghostscript转换EPS/EMF为临时PNG
                from subprocess import run
                temp_png = file_path.with_suffix('.png')
                
                # 添加错误检查和详细日志
                result = run(
                    ['gs', '-dSAFER', '-dBATCH', '-dNOPAUSE', 
                     '-sDEVICE=png16m', f'-sOutputFile={temp_png}',
                     '-r300', str(file_path)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"Ghostscript转换失败 (代码 {result.returncode}):")
                    print(f"错误输出: {result.stderr}")
                    return QIcon()
                
                icon = QIcon(str(temp_png))
                temp_png.unlink()  # 删除临时文件
                return icon
            except Exception as e:
                print(f"EPS转换异常: {str(e)}")
                return QIcon()
        
        # 直接加载SVG
        elif ext == '.svg':
            return QIcon(str(file_path))
        
        return QIcon() 