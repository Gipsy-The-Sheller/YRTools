"""
YRTools 配置加载器
支持INI和JSON两种配置格式，JSON优先
"""
import json
import os
from configparser import ConfigParser
from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

class PluginConfigLoader:
    """插件配置加载器，支持INI和JSON格式"""
    
    def __init__(self):
        self.supported_formats = ['.json', '.ini']
    
    def load_plugin_config(self, plugin_dir: str) -> Optional[Dict[str, Any]]:
        """
        加载插件配置，优先使用JSON格式
        
        Args:
            plugin_dir: 插件目录路径
            
        Returns:
            配置字典，如果加载失败返回None
        """
        # 优先查找JSON配置文件
        json_config = self._load_json_config(plugin_dir)
        if json_config:
            return self._parse_json_config(json_config, plugin_dir)
        
        # 回退到INI配置文件
        ini_config = self._load_ini_config(plugin_dir)
        if ini_config:
            return self._parse_ini_config(ini_config, plugin_dir)
        
        logger.warning(f"No valid configuration found in {plugin_dir}")
        return None
    
    def _load_json_config(self, plugin_dir: str) -> Optional[Dict]:
        """加载JSON配置文件"""
        json_path = os.path.join(plugin_dir, "settings.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"✅ Loaded JSON config from {json_path}")
                return config
        except Exception as e:
            logger.error(f"❌ Failed to load JSON config from {json_path}: {str(e)}")
            return None
    
    def _load_ini_config(self, plugin_dir: str) -> Optional[ConfigParser]:
        """加载INI配置文件"""
        ini_path = os.path.join(plugin_dir, "settings.ini")
        if not os.path.exists(ini_path):
            return None
        
        try:
            config = ConfigParser()
            config.read(ini_path, encoding='utf-8')
            logger.info(f"✅ Loaded INI config from {ini_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load INI config from {ini_path}: {str(e)}")
            return None
    
    def _parse_json_config(self, config: Dict, plugin_dir: str) -> Dict[str, Any]:
        """解析JSON配置为统一格式"""
        result = {
            'config_type': 'json',
            'plugin_dir': plugin_dir,
            'plugins': []
        }
        
        # 检查是否为多插件配置
        if 'plugins' in config and isinstance(config['plugins'], list):
            # 多插件配置
            result['is_multi_plugin'] = True
            result['plugin_group'] = config.get('plugin_group', 'Unknown')
            result['description'] = config.get('description', '')
            result['shared_resources'] = config.get('shared_resources', {})
            
            for plugin_config in config['plugins']:
                parsed_plugin = self._parse_single_json_plugin(plugin_config, plugin_dir)
                if parsed_plugin:
                    result['plugins'].append(parsed_plugin)
        else:
            # 单插件配置
            result['is_multi_plugin'] = False
            parsed_plugin = self._parse_single_json_plugin(config, plugin_dir)
            if parsed_plugin:
                result['plugins'].append(parsed_plugin)
        
        return result
    
    def _parse_single_json_plugin(self, plugin_config: Dict, plugin_dir: str) -> Optional[Dict[str, Any]]:
        """解析单个插件的JSON配置"""
        try:
            # 验证必需字段
            required_fields = ['name', 'entry_point']
            for field in required_fields:
                if field not in plugin_config:
                    logger.error(f"Missing required field '{field}' in plugin config")
                    return None
            
            return {
                'meta': {
                    'name': plugin_config['name'],
                    'version': plugin_config.get('version', '1.0'),
                    'author': plugin_config.get('author', 'Unknown'),
                    'description': plugin_config.get('description', ''),
                    'category': plugin_config.get('category', 'General')
                },
                'placement': {
                    'path': plugin_config.get('placement', {}).get('path', ''),
                    'priority': int(plugin_config.get('placement', {}).get('priority', 0)),
                    'favicon': plugin_config.get('icon', '')
                },
                'runtime': {
                    'type': plugin_config.get('runtime', {}).get('type', 'pyplug'),
                    'entry_point': plugin_config['entry_point'],
                    'dependencies': plugin_config.get('runtime', {}).get('dependencies', []),
                    'config': plugin_config.get('runtime', {}).get('config', '')
                },
                'dir': plugin_dir,
                'config_file': 'settings.json'
            }
        except Exception as e:
            logger.error(f"Failed to parse JSON plugin config: {str(e)}")
            return None
    
    def _parse_ini_config(self, config: ConfigParser, plugin_dir: str) -> Dict[str, Any]:
        """解析INI配置为统一格式"""
        result = {
            'config_type': 'ini',
            'plugin_dir': plugin_dir,
            'is_multi_plugin': False,
            'plugins': []
        }
        
        try:
            # 验证必需section
            required_sections = ['metadata', 'placement', 'runtime']
            for section in required_sections:
                if not config.has_section(section):
                    raise ValueError(f"Missing required section [{section}]")
            
            plugin_data = {
                'meta': dict(config['metadata']),
                'placement': dict(config['placement']),
                'runtime': dict(config['runtime']),
                'dir': plugin_dir,
                'config_file': 'settings.ini'
            }
            
            # 处理路径
            if plugin_data['placement']['path'] == '':
                plugin_data['placement']['path'] = 'Plugins'
            else:
                plugin_data['placement']['path'] = 'Plugins/' + plugin_data['placement']['path']
            
            # 处理优先级（INI中的priority是字符串）
            plugin_data['placement']['priority'] = int(plugin_data['placement'].get('priority', '0'))
            
            result['plugins'].append(plugin_data)
            
        except Exception as e:
            logger.error(f"Failed to parse INI config: {str(e)}")
            return None
        
        return result
    
    def get_all_plugins(self, plugins_dir: str = "plugins") -> List[Dict[str, Any]]:
        """
        扫描所有插件目录，返回统一的插件配置列表
        
        Args:
            plugins_dir: 插件根目录
            
        Returns:
            所有插件的配置列表
        """
        all_plugins = []
        
        if not os.path.exists(plugins_dir):
            logger.warning(f"Plugins directory not found: {plugins_dir}")
            return all_plugins
        
        for dir_name in os.listdir(plugins_dir):
            dir_path = os.path.join(plugins_dir, dir_name)
            if not os.path.isdir(dir_path):
                continue
            
            logger.info(f"🔍 Scanning plugin directory: {dir_path}")
            
            config_data = self.load_plugin_config(dir_path)
            if config_data:
                all_plugins.extend(config_data['plugins'])
                logger.info(f"✅ Loaded {len(config_data['plugins'])} plugin(s) from {dir_name}")
            else:
                logger.warning(f"❌ Failed to load config from {dir_name}")
        
        # 按优先级排序
        all_plugins.sort(key=lambda x: int(x['placement'].get('priority', 0)))
        
        logger.info(f"📊 Total plugins loaded: {len(all_plugins)}")
        return all_plugins

# 全局配置加载器实例
config_loader = PluginConfigLoader()
