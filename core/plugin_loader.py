import os
import logging
from PyQt5.QtGui import QIcon
from configparser import ConfigParser

logger = logging.getLogger(__name__)

class PluginConfig:
    _instance = None
    
    @classmethod
    def get(cls, plugin_name, key, default=None):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance.config.get(plugin_name, key, fallback=default)
    
    @classmethod
    def get_workplace_dir(cls):
        """获取工作目录路径"""
        workplace = os.path.join("workplace", "plugins")
        os.makedirs(workplace, exist_ok=True)
        return workplace

    def __init__(self):
        self.config = ConfigParser()
        self.config.read('config/settings.ini', encoding='utf-8')

class PluginLoader:
    def _parse_ini(self, plugin_path):
        # This method is assumed to exist as it's called in the load_plugin method
        # It's not provided in the original file or the code block
        # It's assumed to return a configuration dictionary
        pass

    def load_plugin(self, plugin_path):
        config = self._parse_ini(plugin_path)
        
        # 添加原始路径信息
        config['metadata']['config_file'] = plugin_path
        config['dir'] = os.path.dirname(plugin_path)  # 添加插件目录
        
        # 预加载图标
        icon = QIcon()
        if 'favicon' in config['metadata']:
            icon_path = os.path.join(os.path.dirname(plugin_path), config['metadata']['favicon'])
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
            elif config['metadata']['favicon'].startswith(":/"):
                icon = QIcon(config['metadata']['favicon'])
        
        return {
            'meta': config['metadata'],
            'config_path': plugin_path,
            'dir': os.path.dirname(plugin_path),  # 传递目录信息
            'icon': icon,  # 添加预加载的图标
            # ... 其他字段 ...
        } 