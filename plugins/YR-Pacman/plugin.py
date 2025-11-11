# YR-Pacman - Decentralized Package Manager for YRTools
# Copyright (C) 2025 Zhi-Jie Xu & Yi-Yang Jia
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

import sys
import os
import json
import requests
import zipfile
import tempfile
import shutil
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
                            QTreeWidget, QTreeWidgetItem, QPushButton, QDialog, 
                            QDialogButtonBox, QLineEdit, QFileDialog, QMessageBox, 
                            QScrollArea, QMenu, QInputDialog, QRadioButton,
                            QApplication, QTabWidget, QTextEdit, QListWidget,
                            QListWidgetItem, QComboBox, QProgressBar, QSizePolicy)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QCursor

class GitHubSearchThread(QThread):
    """线程用于在GitHub上搜索插件"""
    search_finished = pyqtSignal(list)
    search_error = pyqtSignal(str)
    
    def __init__(self, query):
        super().__init__()
        self.query = query
    
    def run(self):
        try:
            # 使用GitHub API搜索带有yr-plugin标签的仓库
            url = f"https://api.github.com/search/repositories?q=topic:{self.query}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                plugins = []
                for item in data.get('items', []):
                    plugin_info = {
                        'name': item['name'],
                        'full_name': item['full_name'],
                        'description': item['description'],
                        'html_url': item['html_url'],
                        'clone_url': item['clone_url'],
                        'default_branch': item['default_branch'],
                        'updated_at': item['updated_at']
                    }
                    plugins.append(plugin_info)
                
                self.search_finished.emit(plugins)
            else:
                self.search_error.emit(f"GitHub API request failed with status code: {response.status_code}")
        except Exception as e:
            self.search_error.emit(str(e))


class PluginValidatorThread(QThread):
    """线程用于验证插件是否有效"""
    validation_finished = pyqtSignal(dict)
    validation_error = pyqtSignal(str, str)  # plugin_name, error
    
    def __init__(self, plugin_info):
        super().__init__()
        self.plugin_info = plugin_info
    
    def run(self):
        try:
            # 尝试获取插件的settings.ini文件
            settings_url = f"https://raw.githubusercontent.com/{self.plugin_info['full_name']}/{self.plugin_info['default_branch']}/settings.ini"
            response = requests.get(settings_url)
            
            if response.status_code == 200:
                # 简单验证是否包含必要的插件信息
                content = response.text
                if 'name' in content and 'entry_point' in content:
                    self.plugin_info['validated'] = True
                    self.validation_finished.emit(self.plugin_info)
                else:
                    self.plugin_info['validated'] = False
                    self.validation_finished.emit(self.plugin_info)
            else:
                self.plugin_info['validated'] = False
                self.validation_finished.emit(self.plugin_info)
        except Exception as e:
            self.validation_error.emit(self.plugin_info['name'], str(e))


class ReleaseFetcherThread(QThread):
    """线程用于获取插件的发布版本"""
    releases_fetched = pyqtSignal(str, list)  # plugin_name, releases
    fetch_error = pyqtSignal(str, str)  # plugin_name, error
    
    def __init__(self, plugin_name, full_name):
        super().__init__()
        self.plugin_name = plugin_name
        self.full_name = full_name
    
    def run(self):
        try:
            # 获取插件的发布版本
            url = f"https://api.github.com/repos/{self.full_name}/releases"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                releases = []
                for item in data:
                    release_info = {
                        'tag_name': item['tag_name'],
                        'name': item['name'],
                        'published_at': item['published_at'],
                        'zipball_url': item['zipball_url'],
                        'tarball_url': item['tarball_url']
                    }
                    releases.append(release_info)
                
                self.releases_fetched.emit(self.plugin_name, releases)
            else:
                self.fetch_error.emit(self.plugin_name, f"Failed to fetch releases: {response.status_code}")
        except Exception as e:
            self.fetch_error.emit(self.plugin_name, str(e))


class PluginInstallerThread(QThread):
    """线程用于安装插件"""
    install_finished = pyqtSignal(str, bool)  # plugin_name, success
    install_progress = pyqtSignal(str, int, int)  # plugin_name, current, total
    install_error = pyqtSignal(str, str)  # plugin_name, error
    
    def __init__(self, plugin_info, install_path):
        super().__init__()
        self.plugin_info = plugin_info
        self.install_path = install_path
    
    def run(self):
        try:
            plugin_name = self.plugin_info['name']
            self.install_progress.emit(plugin_name, 0, 100)
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                self.install_progress.emit(plugin_name, 10, 100)
                
                # 下载ZIP文件
                zip_url = self.plugin_info['zipball_url']
                zip_path = os.path.join(temp_dir, f"{plugin_name}.zip")
                
                response = requests.get(zip_url, stream=True)
                if response.status_code != 200:
                    self.install_error.emit(plugin_name, f"Failed to download plugin: {response.status_code}")
                    return
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.install_progress.emit(plugin_name, 50, 100)
                
                # 解压文件
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                self.install_progress.emit(plugin_name, 70, 100)
                
                # 查找解压后的插件目录
                extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                if not extracted_dirs:
                    self.install_error.emit(plugin_name, "No directory found in downloaded archive")
                    return
                
                plugin_source = os.path.join(temp_dir, extracted_dirs[0])
                plugin_dest = os.path.join(self.install_path, plugin_name)
                
                # 如果目标目录已存在，先删除
                if os.path.exists(plugin_dest):
                    shutil.rmtree(plugin_dest)
                
                # 移动插件到目标位置
                shutil.move(plugin_source, plugin_dest)
                
                self.install_progress.emit(plugin_name, 100, 100)
                self.install_finished.emit(plugin_name, True)
                
        except Exception as e:
            self.install_error.emit(plugin_name, str(e))


class YRPacmanWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plugins = {}  # 存储已发现的插件
        self.current_plugin = None  # 当前查看的插件
        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # logo + 标题
        logo_icon = QIcon(os.path.join(self.plugin_path, "logo.svg"))
        logo_label = QLabel()
        logo_label.setPixmap(logo_icon.pixmap(QSize(64, 64)))
        logo_label.setAlignment(Qt.AlignRight)
        logo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        title_label = QLabel("YR-Pacman - Decentralized Package Manager")

        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignLeft)
        # 横向布局
        title_layout = QHBoxLayout()
        title_layout.addWidget(logo_label)
        title_layout.addWidget(title_label)
        title_layout.setAlignment(Qt.AlignCenter)
        layout.addLayout(title_layout)
        # layout.addWidget(title_label)
        
        # 搜索和操作区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search keyword (default: yr-plugin)")
        self.search_button = QPushButton("Search Plugins")
        self.search_button.clicked.connect(self.search_plugins)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.search_results_tab = QWidget()
        self.installed_plugins_tab = QWidget()
        self.plugin_details_tab = QWidget()
        
        self.tab_widget.addTab(self.search_results_tab, "Search Results")
        self.tab_widget.addTab(self.installed_plugins_tab, "Installed Plugins")
        self.tab_widget.addTab(self.plugin_details_tab, "Plugin Details")
        
        self.init_search_results_tab()
        self.init_installed_plugins_tab()
        self.init_plugin_details_tab()
        
        layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
    
    def init_search_results_tab(self):
        layout = QVBoxLayout(self.search_results_tab)
        
        # 搜索结果列表
        self.results_list = QTreeWidget()
        self.results_list.setHeaderLabels(["Plugin Name", "Description", "Last Updated", "Validated"])
        self.results_list.itemClicked.connect(self.show_plugin_details)
        layout.addWidget(self.results_list)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install Selected")
        self.install_button.clicked.connect(self.install_plugin)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_results)
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.refresh_button)
        layout.addLayout(button_layout)
    
    def init_installed_plugins_tab(self):
        layout = QVBoxLayout(self.installed_plugins_tab)
        self.installed_list = QListWidget()
        layout.addWidget(self.installed_list)
        
        button_layout = QHBoxLayout()
        self.uninstall_button = QPushButton("Uninstall Selected")
        self.update_button = QPushButton("Update Selected")
        button_layout.addWidget(self.uninstall_button)
        button_layout.addWidget(self.update_button)
        layout.addLayout(button_layout)
    
    def init_plugin_details_tab(self):
        layout = QVBoxLayout(self.plugin_details_tab)
        
        self.details_display = QTextEdit()
        self.details_display.setReadOnly(True)
        layout.addWidget(self.details_display)
        
        # 版本选择和安装按钮
        control_layout = QHBoxLayout()
        self.version_combo = QComboBox()
        self.version_combo.addItem("Latest commit (default branch)")
        self.install_from_details_button = QPushButton("Install This Plugin")
        self.install_from_details_button.clicked.connect(self.install_from_details)
        self.back_button = QPushButton("Back to Search")
        self.back_button.clicked.connect(lambda: self.tab_widget.setCurrentIndex(0))
        
        control_layout.addWidget(QLabel("Version:"))
        control_layout.addWidget(self.version_combo)
        control_layout.addWidget(self.install_from_details_button)
        control_layout.addWidget(self.back_button)
        layout.addLayout(control_layout)
    
    def search_plugins(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            keyword = "yr-plugin"
        
        self.status_label.setText(f"Searching for plugins with keyword: {keyword}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # 启动搜索线程
        self.search_thread = GitHubSearchThread(keyword)
        self.search_thread.search_finished.connect(self.on_search_finished)
        self.search_thread.search_error.connect(self.on_search_error)
        self.search_thread.start()
    
    def on_search_finished(self, plugins):
        self.progress_bar.setVisible(False)
        self.results_list.clear()
        
        if not plugins:
            self.status_label.setText("No plugins found")
            return
        
        self.status_label.setText(f"Found {len(plugins)} plugins. Validating...")
        
        # 保存插件信息并开始验证
        self.plugins = {plugin['name']: plugin for plugin in plugins}
        
        # 创建验证线程
        self.validation_threads = []
        for plugin in plugins:
            thread = PluginValidatorThread(plugin)
            thread.validation_finished.connect(self.on_validation_finished)
            thread.validation_error.connect(self.on_validation_error)
            self.validation_threads.append(thread)
            thread.start()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(plugins))
        self.validation_count = 0
        self.total_validations = len(plugins)
    
    def on_search_error(self, error):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Search error: {error}")
        QMessageBox.critical(self, "Search Error", f"Failed to search plugins: {error}")
    
    def on_validation_finished(self, plugin_info):
        self.validation_count += 1
        self.progress_bar.setValue(self.validation_count)
        
        # 更新UI
        item = QTreeWidgetItem([
            plugin_info['name'],
            plugin_info['description'] or 'No description',
            plugin_info['updated_at'][:10],
            'Yes' if plugin_info.get('validated', False) else 'No'
        ])
        item.setData(0, Qt.UserRole, plugin_info)
        self.results_list.addTopLevelItem(item)
        
        if self.validation_count >= self.total_validations:
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Search completed. Found {self.total_validations} plugins.")
    
    def on_validation_error(self, plugin_name, error):
        self.validation_count += 1
        self.progress_bar.setValue(self.validation_count)
        
        if self.validation_count >= self.total_validations:
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Search completed with errors. Found {self.total_validations} plugins.")
    
    def show_plugin_details(self, item, column):
        plugin_info = item.data(0, Qt.UserRole)
        self.current_plugin = plugin_info
        
        details = f"""
<h2>{plugin_info['name']}</h2>
<p><b>Description:</b> {plugin_info['description'] or 'No description provided'}</p>
<p><b>Repository:</b> <a href="{plugin_info['html_url']}">{plugin_info['full_name']}</a></p>
<p><b>Last Updated:</b> {plugin_info['updated_at']}</p>
<p><b>Validated:</b> {'Yes' if plugin_info.get('validated', False) else 'No'}</p>
"""
        
        if plugin_info.get('validated', False):
            details += "<p><b>Status:</b> This plugin is compatible with YRTools.</p>"
        else:
            details += "<p><b>Status:</b> This plugin may not be compatible with YRTools.</p>"
        
        self.details_display.setHtml(details)
        
        # 获取版本信息
        self.version_combo.clear()
        self.version_combo.addItem("Latest commit (default branch)")
        
        self.fetch_releases(plugin_info['name'], plugin_info['full_name'])
        self.tab_widget.setCurrentIndex(2)  # Switch to details tab
    
    def fetch_releases(self, plugin_name, full_name):
        """获取插件的发布版本"""
        self.status_label.setText(f"Fetching releases for {plugin_name}...")
        
        self.release_thread = ReleaseFetcherThread(plugin_name, full_name)
        self.release_thread.releases_fetched.connect(self.on_releases_fetched)
        self.release_thread.fetch_error.connect(self.on_fetch_error)
        self.release_thread.start()
    
    def on_releases_fetched(self, plugin_name, releases):
        self.status_label.setText(f"Releases fetched for {plugin_name}")
        for release in releases:
            self.version_combo.addItem(f"{release['tag_name']} - {release['name']}", release)
    
    def on_fetch_error(self, plugin_name, error):
        self.status_label.setText(f"Failed to fetch releases for {plugin_name}: {error}")
    
    def install_plugin(self):
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a plugin to install.")
            return
        
        item = selected_items[0]
        plugin_info = item.data(0, Qt.UserRole)
        self.install_plugin_by_info(plugin_info)
    
    def install_from_details(self):
        if not self.current_plugin:
            QMessageBox.warning(self, "No Plugin", "No plugin selected.")
            return
        
        self.install_plugin_by_info(self.current_plugin)
    
    def install_plugin_by_info(self, plugin_info):
        """通过插件信息安装插件"""
        # 获取最新版本的zipball_url
        plugin_info['zipball_url'] = f"https://github.com/{plugin_info['full_name']}/archive/{plugin_info['default_branch']}.zip"
        
        # 检查是否有选择特定版本
        current_data = self.version_combo.currentData()
        if current_data and isinstance(current_data, dict):
            plugin_info['zipball_url'] = current_data['zipball_url']
        
        self.status_label.setText(f"Installing {plugin_info['name']}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # 获取插件安装路径
        install_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins")
        
        # 启动安装线程
        self.install_thread = PluginInstallerThread(plugin_info, install_path)
        self.install_thread.install_finished.connect(self.on_install_finished)
        self.install_thread.install_error.connect(self.on_install_error)
        self.install_thread.install_progress.connect(self.on_install_progress)
        self.install_thread.start()
    
    def on_install_progress(self, plugin_name, current, total):
        if total > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
    
    def on_install_finished(self, plugin_name, success):
        self.progress_bar.setVisible(False)
        if success:
            self.status_label.setText(f"Successfully installed {plugin_name}")
            QMessageBox.information(self, "Installation Complete", f"Plugin {plugin_name} has been successfully installed.")
        else:
            self.status_label.setText(f"Failed to install {plugin_name}")
            QMessageBox.critical(self, "Installation Failed", f"Failed to install plugin {plugin_name}.")
    
    def on_install_error(self, plugin_name, error):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Installation error for {plugin_name}: {error}")
        QMessageBox.critical(self, "Installation Error", f"Failed to install plugin {plugin_name}: {error}")
    
    def refresh_results(self):
        self.search_plugins()


# 插件入口类
class YRPacman_entry:
    def __init__(self):
        self.plugin_path = os.path.dirname(os.path.abspath(__file__))
        self.widget = None
    
    def get_widget(self):
        if self.widget is None:
            self.widget = YRPacmanWidget()
        return self.widget
    
    def run(self):
        """
        YRTools插件接口要求的方法
        返回插件的主窗口部件
        """
        return self.get_widget()