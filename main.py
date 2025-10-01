# YRTools.py - A one-for-all plugin-based desktop platform for (more than) bioinformatics.
# Copyright (C) 2025  Zhi-Jie Xu, Yi-Yang Jia
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__version__ = "0.0.2 pre-release"

import sys
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, 
                            QTreeWidget, QTreeWidgetItem, QWidget,
                            QVBoxLayout, QLabel, QPushButton, QLineEdit, QSpinBox, QTextEdit, QComboBox, QProgressBar, QTabWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import Qt, QUrl, QSize
from PyQt5.QtGui import QFont, QFontDatabase, QIcon
from jinja2 import Template
import importlib
import json
import subprocess
import shlex
from PyQt5.QtCore import pyqtSlot
from configparser import ConfigParser
import traceback
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
import datetime
from core.custom_tabbar import ChromeTabBar
import inspect
import logging
from core.crash_handler import handle_exception
from core.config_loader import config_loader

# basic plugin dependencies
## NOTE: This part may be removed from source code after the development of YRRuntimeManager
## TODO: plugin - YRRuntimeManager

import numpy
import pandas
import matplotlib
import seaborn
import scipy
import Bio
import Bio.Seq
import Bio.SeqIO
import Bio.SeqRecord
import Bio.SeqFeature
import Bio.SeqRecord
import matplotlib.backends.backend_qt5agg
import matplotlib.figure
from plotnine import *

# allow using customized python libraries
try:
    runtime_base_path = "runtime/base"
    if os.path.exists(runtime_base_path):
        # 扫描runtime/base目录中的所有模块
        for item in os.listdir(runtime_base_path):
            item_path = os.path.join(runtime_base_path, item)
            if os.path.isdir(item_path):
                # 检查是否为Python包（有__init__.py）
                init_file = os.path.join(item_path, "__init__.py")
                if os.path.exists(init_file):
                    # Python Package: 添加到sys.path
                    if item_path not in sys.path:
                        sys.path.insert(0, item_path)
                        print(f"✅ Added Python package to sys.path: {item}")
                else:
                    # Common Module: 添加到sys.path和PATH环境变量
                    if item_path not in sys.path:
                        sys.path.insert(0, item_path)
                        print(f"✅ Added common module to sys.path: {item}")
                    
                    # 添加到PATH环境变量
                    current_path = os.environ.get('PATH', '')
                    if item_path not in current_path:
                        if current_path:
                            os.environ['PATH'] = item_path + os.pathsep + current_path
                        else:
                            os.environ['PATH'] = item_path
                        print(f"✅ Added common module to PATH: {item}")
    else:
        print("⚠️ Runtime base directory not found, creating...")
        os.makedirs(runtime_base_path, exist_ok=True)
except Exception as e:
    print(f"❌ Failed to initialize runtime environment: {str(e)}")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(threadName)s] %(name)s.%(funcName)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ],
    force=True
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

print("Current working dir:", os.getcwd())
print("Root:", BASE_DIR)
print("Python path:", sys.path)

def scan_plugins():
    """
    扫描所有插件，支持INI和JSON配置格式
    返回统一的插件配置列表
    """
    print("🔍 Scanning plugins with enhanced config loader...")
    
    # 使用新的配置加载器
    plugins = config_loader.get_all_plugins("plugins")
    
    print(f"Scanning completed! Found a total of {len(plugins)} valid plugins.")
    return plugins

def load_config(plugin_dir):
    config_path = os.path.join(plugin_dir, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_fonts()
        self.plugins = self.load_plugins()
        self.init_ui()
        self.current_plugin = None
        self.show_tips()
        QWebEngineSettings.globalSettings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls, True
        )
        self.load_global_stylesheet()
        self.setWindowTitle(self._generate_greeting())
        self.statusBar().showMessage(self._get_title())

    def init_ui(self):
        # self.setWindowTitle("YR Tools")
        self.setGeometry(300, 300, 1200, 800)
        
        icon = QIcon("./icons/favicon.svg")
        self.setWindowIcon(icon)

        splitter = QSplitter(Qt.Horizontal)
        
        self.plugin_tree = QTreeWidget()
        self.plugin_tree.setHeaderHidden(True)
        self.build_plugin_tree()
        self.plugin_tree.itemClicked.connect(self.load_plugin)
        
        self.tab_widget = QTabWidget()
        tab_bar = ChromeTabBar()
        self.tab_widget.setTabBar(tab_bar)
        tab_bar.tabCloseRequested.connect(self.tab_widget.tabCloseRequested)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)
        
        self.add_home_tab()
        
        splitter.addWidget(self.plugin_tree)
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([200, 1000])
        
        self.setCentralWidget(splitter)
        
        self.setStyleSheet("""
            QWidget {
                --primary-color: #409EFF;
                --success-color: #67C23A;
                --warning-color: #E6A23C;
                --danger-color: #F56C6C;
                --text-primary: #303133;
                --text-regular: #606266;
            }
        """)

    def add_home_tab(self):
        home_widget = QWidget()
        layout = QVBoxLayout(home_widget)
        
        self.default_workspace = QLabel()
        self.default_workspace.setWordWrap(True)
        self.default_workspace.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.default_workspace)
        
        self.default_workspace.setStyleSheet("""
            QLabel {
                font-family: MiSans;
                font-size: 14px;
                color: rgba(255,255,255,0.9);
                line-height: 1.6;
                padding: 20px;
            }
        """)
        
        self.tab_widget.addTab(home_widget, "Home   ")
        self.tab_widget.setCurrentIndex(0)
        self.show_tips()

    def close_tab(self, index):
        if self.tab_widget.count() == 1:
            # Keep a homepage
            self.add_home_tab()
        self.tab_widget.removeTab(index)

    def load_plugins(self):
        """
        加载所有插件，支持新的配置格式
        """
        plugins = []
        for plugin_config in scan_plugins():
            # 新格式的插件配置已经是字典形式，不需要额外处理
            if plugin_config['runtime']['type'] == 'pyplug':
                plugins.append(PluginWrapper(plugin_config))
            elif plugin_config['runtime']['type'] == 'polypyplug':
                plugins.append(PluginWrapper(plugin_config))
            # elif plugin_config['runtime']['type'] == 'cli':
            #     plugins.append(CLIPlugin(plugin_config))
            # This type of plugin has been abandoned
        return plugins

    def build_plugin_tree(self):
        self.plugin_tree.clear()
        root = self.plugin_tree.invisibleRootItem()
        
        path_map = {}
        
        plugins_sorted = sorted(
            scan_plugins(),
            key=lambda x: int(x['placement'].get('priority', 0))
        )
        
        current_parent = root
        current_path = []
        current_path.append('Plugins')
        plugin_icon = QIcon("./icons/plugin.svg")
        flow_icon = QIcon("./icons/flow.svg")
        folder_icon = QIcon("./icons/folder.svg")
        item = QTreeWidgetItem(current_parent)
        item.setText(0, 'Plugins')
        item.setIcon(0, plugin_icon)
        item.setExpanded(True)
        path_map[tuple(current_path)] = item

        # current_path.append('Flowcharts')
        # item = QTreeWidgetItem(current_parent)
        # item.setText(0, 'Flowcharts')
        # item.setIcon(0, flow_icon)
        # item.setExpanded(True)
        # path_map[tuple(current_path)] = item
        
        # Flowchart hasn't been achieved.

        for plugin in plugins_sorted:
            path = plugin['placement']['path'].split('/')
            current_parent = root
            
            current_parent = path_map[tuple(['Plugins'])]
            current_path = []
            for level in path:
                current_path.append(level)
                path_key = tuple(current_path)
                
                if path_key not in path_map:
                    item = QTreeWidgetItem(current_parent)
                    item.setText(0, level)
                    item.setIcon(0, folder_icon)
                    path_map[path_key] = item

                    if len(current_path) <= 2:
                        item.setExpanded(True)
                
                current_parent = path_map[path_key]
            
            plugin_item = QTreeWidgetItem(current_parent)
            plugin_item.setText(0, plugin['meta']['name'])
            
            # 图标处理逻辑保持不变
            if os.path.exists(os.path.join(plugin['dir'], "icon/Metro_usual.svg")):
                icon_path = os.path.join(plugin['dir'], "icon/Metro_usual.svg")
            elif 'favicon' in plugin['placement'] and plugin['placement']['favicon'] != '':
                icon_path = os.path.join(plugin['dir'], plugin['placement']['favicon'])
            else:
                icon_path = None
            if icon_path:
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                    plugin_item.setIcon(0, icon)
                    plugin['icon'] = icon
            
            plugin_item.setData(0, Qt.UserRole, plugin)
        
        self.plugin_tree.setIndentation(12)
        self.plugin_tree.setStyleSheet("QTreeWidget::item { padding-left: 8px; }")

    def load_plugin(self, item):
        print("\n" + "="*40)
        print("Start to load plugins...")
        
        plugin = item.data(0, Qt.UserRole)
        if not plugin:
            print("❌ Invalid add-ons")
            return
        
        print(f"Plugin Information: {plugin['meta']['name']}")
        print(f"Plugin Type: {plugin['runtime']['type']}")
        print(f"Config Type: {plugin.get('config_type', 'unknown')}")
        
        try:
            plugin_type = plugin['runtime']['type']
            
            if plugin_type == 'pyplug':
                # Main type of plugins
                if 'entry_point' not in plugin['runtime']:
                    raise ValueError("Python plugin needs an entry_point!")
                    
                module_path = os.path.join(plugin['dir'], 
                                         plugin['runtime']['entry_point'].split(':')[0])
                spec = importlib.util.spec_from_file_location("plugin_module", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                class_name = plugin['runtime']['entry_point'].split(':')[1]
                plugin_class = getattr(module, class_name)
                
                sig = inspect.signature(plugin_class.__init__)
                param_names = [p.name for p in list(sig.parameters.values())[1:]]  # skip self
                kwargs = {}
                if 'config' in param_names:
                    kwargs['config'] = plugin
                if 'plugin_path' in param_names:
                    kwargs['plugin_path'] = plugin['dir']
                
                plugin_instance = plugin_class(**kwargs)
                
                # Make sure plugin_path is set
                if not hasattr(plugin_instance, 'plugin_path') or plugin_instance.plugin_path is None:
                    plugin_instance.plugin_path = plugin['dir']
                print(f"Successfully initialized: {plugin['meta']['name']}")
                widget = plugin_instance.run()
                # widget.init_ui()
                    
            elif plugin_type == 'polypyplug':
                # Regard the plugin as a Python site-package, which provides polymerized development experience
                if 'entry_point' not in plugin['runtime']:
                    raise ValueError("Poly Python plugin needs an entry_point!")

                entry = plugin['runtime']['entry_point']
                if ':' not in entry:
                    raise ValueError("entry_point must be in format 'package.module:Class'")

                module_name, class_name = entry.split(':', 1)

                # 确保插件目录在 sys.path 以便包式导入
                added_to_path = False
                if plugin['dir'] not in sys.path:
                    sys.path.insert(0, plugin['dir'])
                    added_to_path = True

                try:
                    module = importlib.import_module(module_name)
                    plugin_class = getattr(module, class_name)

                    sig = inspect.signature(plugin_class.__init__)
                    param_names = [p.name for p in list(sig.parameters.values())[1:]]  # skip self
                    kwargs = {}
                    if 'config' in param_names:
                        kwargs['config'] = plugin
                    if 'plugin_path' in param_names:
                        kwargs['plugin_path'] = plugin['dir']

                    plugin_instance = plugin_class(**kwargs)
                    if not hasattr(plugin_instance, 'plugin_path') or plugin_instance.plugin_path is None:
                        plugin_instance.plugin_path = plugin['dir']

                    print(f"Successfully initialized: {plugin['meta']['name']}")
                    widget = plugin_instance.run()
                finally:
                    # 若需严格隔离，可在此移除路径：
                    # if added_to_path and plugin['dir'] in sys.path:
                    #     sys.path.remove(plugin['dir'])
                    pass
            else:
                raise ValueError(f"Unknown plugin type: {plugin_type}")
            
            icon = QIcon()
            try:
                if os.path.exists(os.path.join(plugin['dir'], "icon/Metro_usual.svg")):
                    icon_path = os.path.join(plugin['dir'], "icon/Metro_usual.svg")
                elif 'favicon' in plugin['placement'] and plugin['placement']['favicon'] != '':
                    icon_path = os.path.join(plugin['dir'], plugin['placement']['favicon'])
                else:
                    icon_path = None
                if icon_path:
                    if os.path.exists(icon_path):
                        icon = QIcon(icon_path)
            except KeyError as e:
                print(f"⚠️ {plugin['meta']['name']} lacks favicon configuration: {str(e)}")
                icon = self.default_plugin_icon
            except Exception as e:
                print(f"⚠️ Failed to load icon for {plugin['meta']['name']}: {str(e)}")
                icon = self.default_plugin_icon
            
            self._add_plugin_tab(widget, plugin['meta']['name'], icon)
            
        except Exception as e:
            print(f"❌ Failed to load plugin: {str(e)}")
            traceback.print_exc()
        
        print("="*40 + "\n")

    def _add_plugin_tab(self, widget, title, icon):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(widget)
        
        index = self.tab_widget.addTab(container, icon, title+'   ')
        
        self.tab_widget.setCurrentIndex(index)

    def show_tips(self):

        self.default_workspace.setStyleSheet(f"""
            QWidget {{
                background-color: #ffffff;
                border-radius: 8px;
                padding: 20px;
            }}
        """)

        template = Template("""
        <div>
          {{ content }}
        </div>
        """)
        content = f"""
        <div>
            <h1 style='margin-bottom: 20px; font-weight: 500; font-size: 30px; text-align: center;'>
                <span style="color:#4c638c;">Y</span><span style="color:#b13e43;">R</span><span style="color:#9fa0a0;">Tools</span> v{__version__}
            </h1>
            <div style='color:#727171; text-align: center; margin-bottom: 20px; font-size: 20px'>A One-for-all Plugin-based Desktop Platform for More Than Bioinformatics</div>
            <br>
            <div style='font-size: 20px; line-height: 1; letter-spacing: 0.5px; text-align: left; margin-left: 100%; margin-right: 100%;'>
                <div>
                    In Chinese, <span style="color:#4c638c;">Yi</span><span style="color:#9fa0a0;">-</span><span style="color:#b13e43;">Ran</span> means <i>Likewise</i>. 
                    <b>Plugin</b> is the basic function unit of YRTools. 
                    Any tool or feature you can imagine can be integrated as a <b>plugin</b>.
                </div>
                <br>
                <div><b>Github Repository</b>: <a href="https://github.com/Gipsy-The-Sheller/YRTools">https://github.com/Gipsy-The-Sheller/YRTools</a></div>
                <div><b>Bug Report</b>: <span style="color:#4c638c;">Github Issues</span> or send email to <span style='color:#b13e43;'>zjxmolls@outlook.com</span></div>
                <div><b>Citation</b>: If you use YRTools, please cite its Github Repository.</div>
            </div>
            <br>
            <br>
            <hr>
            <div style='margin-top: 50px; margin-bottom: 50px;'><img src="./icons/badge.svg"></div>
            <p style='margin-top: 15px; font-size: 16px;'>
                To start your work, select a plugin from the left explorer.
            </p>
        </div>
        """
        
        html = template.render(content=content)
        self.default_workspace.setText(html)
        self.default_workspace.setAlignment(Qt.AlignCenter)

    def adjust_text_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        #return '#ffffff' if brightness < 150 else '#333333'
        return '#333333'

    def render_template(self, template_path, context):
        with open(template_path) as f:
            return f.read().format(**context)

    def change_theme(self, theme_name):
        with open(f"styles/{theme_name}.qss") as f:
            theme = f.read()
        
        variables = """
            QWidget {
                --primary-color: #409EFF;
                --background-primary: #f0f2f5;
            }
        """
        self.setStyleSheet(theme + variables)
        
        # Update for plugins
        for plugin in self.plugins:
            if hasattr(plugin, 'on_theme_changed'):
                plugin.on_theme_changed(theme_name)

    def load_global_stylesheet(self):
        try:
            with open("styles/global.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("⚠️ Unable to find global qss. Using default style.")
        except Exception as e:
            print(f"❌ Failed to load qss: {str(e)}")

    def create_plugin(self, plugin_data):
        if plugin_data['runtime']['type'] == 'gui':
            return GUIPlugin(plugin_data)

    def _generate_greeting(self):
        now = datetime.datetime.now()
        return f"YRTools · {now.strftime('%Y-%m-%d %H:%M')}"

    def _get_title(self):
        return f"""YRTools v{__version__}"""

    def load_fonts(self):
        font_path = "fonts/MiSans-Medium.ttf"
        if QFontDatabase.addApplicationFont(font_path) == -1:
            print("❌ Failed to load fonts.")

class PluginWrapper:
    """插件包装器，兼容新的配置格式"""
    def __init__(self, config):
        self.config = config
        self.name = config['meta']['name']
        self.type = config['meta'].get('category', 'General')
        
    def run(self):
        return self.config['kernel']() if 'kernel' in self.config else None

class GUIPlugin:
    def __init__(self, config):
        self.config = config
        self.name = config['metadata']['name']
        self.type = config['metadata']['category']
        
    def run(self):
        return self.config['kernel']()


if __name__ == "__main__":
    sys.excepthook = handle_exception
    
    app = QApplication(sys.argv)
    
    # 加载常规Medium字重
    font_path = "fonts/MiSans-Medium.ttf"  # 确保实际文件名匹配
    font_id = QFontDatabase.addApplicationFont(font_path)
    
    if font_id != -1:
        # 获取字体家族名称
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            print("⚠️ Failed to load font family. Using default fonts.")
        else:
            font_family = families[0]
            app_font = QFont(font_family, 10)
            app_font.setWeight(QFont.Medium)  # 显式设置字重
            app.setFont(app_font)
            print(f"✅ Successfully loaded fonts: {font_family}")
            print(f"Current font: {app_font.toString()}")
    else:
        print("❌ Failed to load fonts. Please check the path: ", font_path)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())