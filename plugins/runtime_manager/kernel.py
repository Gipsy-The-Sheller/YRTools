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

import os
import sys
import json
import shutil
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
                            QTreeWidget, QTreeWidgetItem, QPushButton, QDialog, 
                            QDialogButtonBox, QLineEdit, QFileDialog, QMessageBox, 
                            QScrollArea, QMenu, QInputDialog, QRadioButton)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QCursor

class ModuleEditor(QDialog):
    def __init__(self, parent=None, edit_mode=False, module_data=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setWindowTitle("Module Editor")
        self.setWindowModality(Qt.ApplicationModal)
        # icon
        self.setWindowIcon(QIcon("./icons/package.svg"))
        self.setMinimumSize(400, 300)
        self.plugin_path = ''
        self.edit_mode = edit_mode
        self.module_data = module_data
        self.init_ui()
        
        if edit_mode and module_data:
            self.load_module_data(module_data)
            # disable the path edit
            self.path_edit.setDisabled(True)
            self.browse_btn.setDisabled(True)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Module Name (e.g. numpy)")
        form.addRow("Module Name:", self.name_edit)
        
        self.version_edit = QLineEdit()
        self.version_edit.setPlaceholderText("Version (e.g. 1.21.0)")
        form.addRow("Version:", self.version_edit)
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select Module Folder Path")
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.browse_btn)

        form.addRow("Module Path:", path_layout)        

        # single-select whether it's a python package (then we do not need to specify the path in the dir)
        # or a common module (a folder contains programs that need to be added to the PATH and run directly) 
        module_type_layout = QHBoxLayout()
        self.package_radio = QRadioButton("Python Package")
        self.package_radio.setChecked(True)
        self.common_radio = QRadioButton("Common Module")
        module_type_layout.addWidget(self.package_radio)
        module_type_layout.addWidget(self.common_radio)
        form.addRow("Module Type:", module_type_layout)
    
        
        layout.addLayout(form)
        
        info_label = QLabel("""
        <b>Instructions:</b><br>
        • Module Name: Python package name<br>
        • Version: Module version information<br>
        • Module Path: Path to the folder containing the Python module<br>
        • Module Type: <br>
        &nbsp;&nbsp;- <b>Python Package</b>: Standard Python package (import package_name)<br>
        &nbsp;&nbsp;- <b>Common Module</b>: Scripts/binaries that need direct execution
        """)
        info_label.setStyleSheet("color: #666; font-size: 12px; margin: 10px 0;")
        layout.addWidget(info_label)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
    
    def browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Module Folder")
        if path:
            self.path_edit.setText(path)
    
    def load_module_data(self, data):
        self.name_edit.setText(data.get('name', ''))
        self.version_edit.setText(data.get('version', ''))
        self.path_edit.setText(data.get('path', ''))
        type = data.get('type', 'package')
        if type == 'package':
            self.package_radio.setChecked(True)
        else:
            self.common_radio.setChecked(True)
    def get_module_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'version': self.version_edit.text().strip(),
            'path': self.path_edit.text().strip(),
            'type': 'package' if self.package_radio.isChecked() else 'common'
        }
    
    def copy_module_to_runtime(self, source_path, environment_name, module_name):
        try:
            runtime_base = os.path.join(os.getcwd(), 'runtime')
            env_dir = os.path.join(runtime_base, environment_name)
            target_dir = os.path.join(env_dir, module_name)
            
            os.makedirs(env_dir, exist_ok=True)
            
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            shutil.copytree(source_path, target_dir)
            
            relative_path = os.path.relpath(target_dir, os.getcwd())
            return relative_path
            
        except Exception as e:
            print(f"Copy module failed: {str(e)}")
            return None
    
    def validate_data(self):
        name = self.name_edit.text().strip()
        version = self.version_edit.text().strip()
        path = self.path_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Failed", "Module Name cannot be empty")
            return False
        
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Validation Failed", "Please select a valid module path")
            return False
        
        return True
    
    def accept(self):
        if self.validate_data():
            super().accept()

class RuntimeManagerPlugin(QWidget):
    def __init__(self):
        super().__init__()
        self.environments = {
            'base': {},  # base environment
            'custom': {}  # custom environment
        }
        self.activated_environments = set()  # trace activated environments
        self.load_environments()
        self.init_env()  # scan and initialize activated environments
        self.init_ui()
    
    def init_env(self):
        """
        When YR Runtime Manager is closed abruptly, activated environments will be remained in sys.path and PATH.
        Thus, we need to scan both sys.path and PATH environment variable to initialize activated environments.
        """
        runtime_base = os.path.join(os.getcwd(), 'runtime')
        for path in sys.path:
            if path.startswith(runtime_base):
                rel_path = os.path.relpath(path, runtime_base)
                path_parts = rel_path.split(os.sep)
                
                if len(path_parts) >= 1 and path_parts[0] != '.':
                    env_name = path_parts[0]
                    self.activated_environments.add(env_name)
                    print(f"Detected activated environment from sys.path: {env_name}")

            elif path.startswith('runtime'):
                rel_path = os.path.relpath(path, 'runtime')
                path_parts = rel_path.split(os.sep)
                
                if len(path_parts) >= 1 and path_parts[0] != '.':
                    env_name = path_parts[0]
                    self.activated_environments.add(env_name)
                    print(f"Detected activated environment from sys.path (relative): {env_name}")
        
        current_path = os.environ.get('PATH', '')
        for path in current_path.split(os.pathsep):
            if path.startswith(runtime_base):
                rel_path = os.path.relpath(path, runtime_base)
                path_parts = rel_path.split(os.sep)
                
                if len(path_parts) >= 1 and path_parts[0] != '.':
                    env_name = path_parts[0]
                    self.activated_environments.add(env_name)
                    print(f"Detected activated environment from PATH: {env_name}")

            elif path.startswith('runtime'):
                rel_path = os.path.relpath(path, 'runtime')
                path_parts = rel_path.split(os.sep)
                
                if len(path_parts) >= 1 and path_parts[0] != '.':
                    env_name = path_parts[0]
                    self.activated_environments.add(env_name)
                    print(f"Detected activated environment from PATH (relative): {env_name}")
        
        # base environment should also be checked
        base_env_path = os.path.join(runtime_base, 'base')
        if os.path.exists(base_env_path):
            has_modules = False
            for item in os.listdir(base_env_path):
                item_path = os.path.join(base_env_path, item)
                if os.path.isdir(item_path):
                    has_modules = True
                    break
            
            if has_modules:
                self.activated_environments.add('base')
                print(f"Detected base environment with modules")
        
        if self.activated_environments:
            print(f"Found {len(self.activated_environments)} activated environments: {', '.join(self.activated_environments)}")
    
    def init_ui(self):
        main_layout = QHBoxLayout()
        widget = QScrollArea()
        widget.setWidgetResizable(True)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        
        btn_layout = QHBoxLayout()
        
        self.add_env_btn = QPushButton("➕ Add Environment")
        self.add_env_btn.clicked.connect(self.add_environment)
        
        self.add_module_btn = QPushButton("📦 Add Module")
        self.add_module_btn.clicked.connect(self.add_module)
        
        btn_layout.addWidget(self.add_env_btn)
        btn_layout.addWidget(self.add_module_btn)
        layout.addLayout(btn_layout)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #f8f9fa;
            }
            QTreeWidget::item {
                height: 36px;
                padding: 4px 8px;
                border-bottom: 1px solid #e9ecef;
            }
        """)
        
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.refresh_tree()
        layout.addWidget(self.tree)
        
        widget.setWidget(container)
        main_layout.addWidget(widget)
        self.setLayout(main_layout)
    
    def refresh_tree(self):
        self.tree.clear()
        
        # create base environment node
        base_root = QTreeWidgetItem()
        base_root.setText(0, "Base Environment (base)")
        try:
            base_icon = os.path.join(self.plugin_path, "icon.svg")
            base_root.setIcon(0, QIcon(base_icon))
        except:
            base_root.setIcon(0, QIcon("./icons/runtime_base.svg"))
        base_root.setFlags(base_root.flags() | Qt.ItemIsEnabled)
        base_root.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        base_root.environment_name = 'base'
        
        # add modules in base environment
        for module_name, module_data in self.environments['base'].items():
            item = QTreeWidgetItem()
            item.setText(0, f"{module_data['name']} v{module_data['version']}")
            item.setIcon(0, QIcon("./icons/package.svg"))
            item.module_name = module_name
            item.module_data = module_data
            item.environment_name = 'base'
            base_root.addChild(item)
        
        # create custom environment node
        custom_root = QTreeWidgetItem()
        custom_root.setText(0, "Custom Environment")
        custom_root.setIcon(0, QIcon("./icons/runtime.svg"))
        custom_root.setFlags(custom_root.flags() | Qt.ItemIsEnabled)
        custom_root.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        custom_root.environment_name = 'custom'
        
        # add custom environment
        for env_name, modules in self.environments['custom'].items():
            env_item = QTreeWidgetItem()
            env_item.setText(0, env_name)
            if env_name in self.activated_environments:
                env_item.setIcon(0, QIcon("./icons/folder_activated.svg"))
            else:
                env_item.setIcon(0, QIcon("./icons/folder.svg"))
            env_item.environment_name = 'custom'
            env_item.env_name = env_name
            
            for module_name, module_data in modules.items():
                module_item = QTreeWidgetItem()
                module_item.setText(0, f"{module_data['name']} v{module_data['version']}")
                module_item.setIcon(0, QIcon("./icons/package.svg"))
                module_item.module_name = module_name
                module_item.module_data = module_data
                module_item.environment_name = 'custom'
                module_item.env_name = env_name
                env_item.addChild(module_item)
            
            custom_root.addChild(env_item)
        
        self.tree.addTopLevelItem(base_root)
        self.tree.addTopLevelItem(custom_root)
        
        # self.tree.expandToDepth(2)

        # expand custom environment
        custom_root.setExpanded(True)
        base_root.setExpanded(True)
    
    def add_environment(self):
        name, ok = QInputDialog.getText(self, "Add Environment", "Please enter the environment name:")
        if ok and name.strip():
            env_name = name.strip()
            if env_name not in self.environments['custom']:
                self.environments['custom'][env_name] = {}
                self.save_environments()
                self.refresh_tree()
            else:
                QMessageBox.warning(self, "Error", "Environment name already exists")
    
    def add_module(self):
        env_name = self.select_environment()
        if not env_name:
            return
        
        editor = ModuleEditor(self, edit_mode=True)
        if editor.exec_() == QDialog.Accepted:
            module_data = editor.get_module_data()
            module_name = module_data['name']
            source_path = module_data['path']
            
            if module_name in self.environments[env_name]:
                reply = QMessageBox.question(
                    self, "Module Already Exists", 
                    f"Module '{module_name}' already exists, do you want to overwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            new_path = editor.copy_module_to_runtime(source_path, env_name, module_name)
            if new_path:
                module_data['path'] = new_path
                self.environments[env_name][module_name] = module_data
                self.save_environments()
                self.refresh_tree()
                QMessageBox.information(self, "Success", f"Module '{module_name}' has been copied to runtime environment.")
            else:
                QMessageBox.warning(self, "Error", "Failed to copy module to runtime directory.")
    
    def select_environment(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Environment")
        dialog.setModal(True)
        dialog.resize(300, 200)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Please select the environment to add the module:"))
        
        env_list = QTreeWidget()
        env_list.setHeaderHidden(True)
        
        base_item = QTreeWidgetItem()
        base_item.setText(0, "📁 Base Environment (base)")
        base_item.setData(0, Qt.UserRole, 'base')
        env_list.addTopLevelItem(base_item)
        
        for env_name in self.environments['custom'].keys():
            item = QTreeWidgetItem()
            item.setText(0, f"📁 {env_name}")
            item.setData(0, Qt.UserRole, env_name)
            env_list.addTopLevelItem(item)
        
        layout.addWidget(env_list)
        

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        if dialog.exec_() == QDialog.Accepted:
            current_item = env_list.currentItem()
            if current_item:
                return current_item.data(0, Qt.UserRole)
        return None
    
    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu()
        
        if hasattr(item, 'module_name'):  # module project
            edit_action = menu.addAction(QIcon("./icons/edit.svg"), "Edit")
            edit_action.triggered.connect(lambda: self.edit_module(item))
            
            move_action = menu.addAction(QIcon("./icons/metro_transfer.svg"), "Move to...")
            move_action.triggered.connect(lambda: self.move_module(item))
            
            delete_action = menu.addAction(QIcon("./icons/delete.svg"), "Delete Module")
            delete_action.triggered.connect(lambda: self.delete_module(item))
            
        elif hasattr(item, 'env_name'):  # custom environment project
            if item.env_name in self.activated_environments:
                deactivate_action = menu.addAction(QIcon("./icons/deactivate.svg"), "Deactivate")
                deactivate_action.triggered.connect(lambda: self.deactivate_environment(item))
            else:
                activate_action = menu.addAction(QIcon("./icons/activate.svg"), "Activate")
                activate_action.triggered.connect(lambda: self.activate_environment(item))

            add_module_action = menu.addAction(QIcon("./icons/metro_add.svg"), "Add Module")
            add_module_action.triggered.connect(lambda: self.add_module_to_env(item.env_name))
            
            rename_action = menu.addAction(QIcon("./icons/edit.svg"), "Rename")
            rename_action.triggered.connect(lambda: self.rename_environment(item)) 
            
            delete_env_action = menu.addAction(QIcon("./icons/delete.svg"), "Delete")
            delete_env_action.triggered.connect(lambda: self.delete_environment(item))


        
        # fix menu position: use cursor position for accurate placement
        # This works better when the widget is embedded in other containers
        cursor_pos = QCursor.pos()
        menu.exec_(cursor_pos)
    
    def on_item_double_clicked(self, item, column):
        if hasattr(item, 'module_name'):
            self.edit_module(item)
    
    def edit_module(self, item):
        editor = ModuleEditor(self, edit_mode=True, module_data=item.module_data)
        if editor.exec_() == QDialog.Accepted:
            new_data = editor.get_module_data()
            old_name = item.module_name
            
            if new_data['name'] != old_name:
                del self.environments[item.environment_name][old_name]
                self.environments[item.environment_name][new_data['name']] = new_data
            else:
                self.environments[item.environment_name][old_name] = new_data
            
            self.save_environments()
            self.refresh_tree()
    
    def move_module(self, item):
        target_env = self.select_environment()
        if not target_env or target_env == item.environment_name:
            return
        
        module_data = item.module_data
        module_name = item.module_name
        
        if item.environment_name == 'base':
            del self.environments['base'][module_name]
        else:
            del self.environments['custom'][item.env_name][module_name]
        
        if target_env == 'base':
            self.environments['base'][module_name] = module_data
        else:
            self.environments['custom'][target_env][module_name] = module_data
        
        self.save_environments()
        self.refresh_tree()
    
    def delete_module(self, item):
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete module '{item.module_data['name']}'?\nThis will also remove the module files from runtime directory.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            module_path = item.module_data['path']
            if os.path.exists(module_path):
                try:
                    shutil.rmtree(module_path)
                    print(f"Deleted module files: {module_path}")
                except Exception as e:
                    print(f"Failed to delete module files: {str(e)}")
                    # message box
                    QMessageBox.warning(self, "Error", f"Failed to delete module files: {str(e)}")
            
            if item.environment_name == 'base':
                del self.environments['base'][item.module_name]
            else:
                del self.environments['custom'][item.env_name][item.module_name]
            
            self.save_environments()
            self.refresh_tree()
    
    def add_module_to_env(self, env_name):
        editor = ModuleEditor(self, edit_mode=True)
        if editor.exec_() == QDialog.Accepted:
            module_data = editor.get_module_data()
            module_name = module_data['name']
            source_path = module_data['path']
            
            if module_name in self.environments['custom'][env_name]:
                reply = QMessageBox.question(
                    self, "Module Already Exists", 
                    f"Module '{module_name}' already exists, do you want to overwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            new_path = editor.copy_module_to_runtime(source_path, env_name, module_name)
            if new_path:
                module_data['path'] = new_path
                self.environments['custom'][env_name][module_name] = module_data
                self.save_environments()
                self.refresh_tree()
                QMessageBox.information(self, "Success", f"Module '{module_name}' has been copied to runtime environment.")
            else:
                QMessageBox.warning(self, "Error", "Failed to copy module to runtime directory.")
    
    def rename_environment(self, item):
        new_name, ok = QInputDialog.getText(
            self, "Rename Environment", 
            "Please enter the new environment name:", 
            text=item.env_name
        )
        
        if ok and new_name.strip() and new_name.strip() != item.env_name:
            new_name = new_name.strip()
            if new_name not in self.environments['custom']:
                # rename environment
                modules = self.environments['custom'][item.env_name]
                del self.environments['custom'][item.env_name]
                self.environments['custom'][new_name] = modules
                
                self.save_environments()
                self.refresh_tree()
            else:
                QMessageBox.warning(self, "Error", "Environment name already exists")
    
    def delete_environment(self, item):
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete the environment '{item.env_name}'?\nThis will delete all modules in the environment and remove their files from runtime directory.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            env_dir = os.path.join(os.getcwd(), 'runtime', item.env_name)
            if os.path.exists(env_dir):
                try:
                    shutil.rmtree(env_dir)
                    print(f"Deleted environment directory: {env_dir}")
                except Exception as e:
                    print(f"Failed to delete environment directory: {str(e)}")
            
            del self.environments['custom'][item.env_name]
            self.save_environments()
            self.refresh_tree()
    
    def activate_environment(self, item):
        env_name = item.env_name
        env_dir = os.path.join(os.getcwd(), 'runtime', env_name)
        
        if not os.path.exists(env_dir):
            QMessageBox.warning(self, "Environment Not Found", 
                              f"Environment directory not found: {env_dir}")
            return
        
        added_paths = []
        added_env_paths = []
        
        # 首先添加环境目录本身到sys.path
        if env_dir not in sys.path:
            sys.path.insert(0, env_dir)
            added_paths.append(env_dir)
            print(f"Adding environment directory to sys.path: {env_dir}")
        
        # 获取环境中的所有模块信息
        modules = self.environments['custom'].get(env_name, {})
        
        for module_name, module_data in modules.items():
            module_type = module_data.get('type', 'package')
            module_path = module_data.get('path', '')

            # check if the module path is relative to the environment directory
            if module_path.startswith(env_dir):
                module_path = os.path.join(os.getcwd(), module_path)
            
            if not module_path or not os.path.exists(module_path):
                continue
            
            if module_type == 'package':
                # Python Package: Add module directory to sys.path
                if module_path not in sys.path:
                    print(f"Adding Python package to sys.path: {module_path}")
                    sys.path.insert(0, module_path)
                    added_paths.append(module_path)
            elif module_type == 'common':
                # Common Module: Add module directory to sys.path and PATH environment variable
                if module_path not in sys.path:
                    sys.path.insert(0, module_path)
                    added_paths.append(module_path)
                
                # Add to PATH environment variable
                current_path = os.environ.get('PATH', '')
                if module_path not in current_path:
                    if current_path:
                        os.environ['PATH'] = module_path + os.pathsep + current_path
                    else:
                        os.environ['PATH'] = module_path
                    added_env_paths.append(module_path)
        
        # If there is no module information, use the traditional method (backward compatibility)
        if not modules:
            if env_dir not in sys.path:
                sys.path.insert(0, env_dir)
                added_paths.append(env_dir)
            
            for module_name in os.listdir(env_dir):
                module_path = os.path.join(env_dir, module_name)
                if os.path.isdir(module_path) and module_path not in sys.path:
                    sys.path.insert(0, module_path)
                    added_paths.append(module_path)
        
        # update activate status
        self.activated_environments.add(env_name)
        self.refresh_tree()
        
        if added_paths or added_env_paths:
            message = f"Environment '{env_name}' has been activated.\n"
            if added_paths:
                message += f"Added {len(added_paths)} paths to Python path.\n"
            if added_env_paths:
                message += f"Added {len(added_env_paths)} paths to PATH environment variable."
            QMessageBox.information(self, "Environment Activated", message)
            print(f"Environment '{env_name}' has been activated.\n")
            print(f"Sys.path: {sys.path}")
            print(f"PATH: {os.environ.get('PATH')}")
        else:
            QMessageBox.information(self, "Environment Activated", 
                                  f"Environment '{env_name}' was already activated.")
    
    def deactivate_environment(self, item):
        """去激活环境 - 从sys.path中移除环境路径"""
        env_name = item.env_name
        env_dir = os.path.join(os.getcwd(), 'runtime', env_name)
        
        removed_paths = []
        removed_env_paths = []
        
        # 首先移除环境目录本身
        if env_dir in sys.path:
            sys.path.remove(env_dir)
            removed_paths.append(env_dir)
            print(f"Removing environment directory from sys.path: {env_dir}")
        
        # 获取环境中的所有模块信息
        modules = self.environments['custom'].get(env_name, {})
        
        # 根据模块信息移除路径
        for module_name, module_data in modules.items():
            module_type = module_data.get('type', 'package')
            module_path = module_data.get('path', '')
            
            if module_path:
                # 从sys.path移除
                if module_path in sys.path:
                    sys.path.remove(module_path)
                    removed_paths.append(module_path)
                
                # 从PATH环境变量移除
                if module_type == 'common':
                    current_path = os.environ.get('PATH', '')
                    if module_path in current_path:
                        # 移除路径并重新设置PATH
                        path_parts = current_path.split(os.pathsep)
                        path_parts = [p for p in path_parts if p != module_path]
                        os.environ['PATH'] = os.pathsep.join(path_parts)
                        removed_env_paths.append(module_path)
        
        # 如果没有模块信息，使用传统方法（向后兼容）
        if not modules:
            # 从sys.path中移除环境目录
            if env_dir in sys.path:
                sys.path.remove(env_dir)
                removed_paths.append(env_dir)
            
            # 移除环境中的模块目录
            if os.path.exists(env_dir):
                for module_name in os.listdir(env_dir):
                    module_path = os.path.join(env_dir, module_name)
                    if os.path.isdir(module_path) and module_path in sys.path:
                        sys.path.remove(module_path)
                        removed_paths.append(module_path)
        
        # 更新激活状态
        self.activated_environments.discard(env_name)
        self.refresh_tree()
        
        if removed_paths or removed_env_paths:
            message = f"Environment '{env_name}' has been deactivated.\n"
            if removed_paths:
                message += f"Removed {len(removed_paths)} paths from Python path.\n"
            if removed_env_paths:
                message += f"Removed {len(removed_env_paths)} paths from PATH environment variable."
            QMessageBox.information(self, "Environment Deactivated", message)
        else:
            QMessageBox.information(self, "Environment Deactivated", 
                                  f"Environment '{env_name}' was not activated.")
    
    def load_environments(self):
        path = os.path.join(os.getcwd(), 'plugins', 'runtime_manager', 'environments.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.environments = data
            except Exception as e:
                print(f"Load environment data failed: {str(e)}")
    
    def save_environments(self):
        path = os.path.join(os.getcwd(), 'plugins', 'runtime_manager', 'environments.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.environments, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Save environment data failed: {str(e)}")

class Plugin:
    def run(self):
        return RuntimeManagerPlugin()
