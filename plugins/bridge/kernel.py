import sys
import json
import subprocess
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
                            QLineEdit, QPushButton, QSpinBox, QComboBox, QCheckBox,
                            QGroupBox, QFileDialog, QTextEdit, QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, QProcess, QByteArray, QTimer
from PyQt5.QtGui import QFont, QFontDatabase
from configparser import ConfigParser
import os
from PyQt5.QtCore import pyqtSignal
from datetime import datetime
import shutil

def add_utf8_bom(filename):
    with open(filename, 'r+', encoding='utf-8') as f:
        content = f.read()
        f.seek(0)
        f.write('\ufeff' + content)
        f.truncate()

class BridgeConfigurator(QWidget):
    saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CLI Bridge Customizer")
        self.setMinimumSize(800, 600)
        self.params = []
        self.init_ui()
        self.force_show_configurator()
        self.plugin_path=os.getcwd()

    def force_show_configurator(self):
        self.toggle_ui_visibility(has_config=True)
        self.load_config()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        self.config_container = QScrollArea()
        self.config_container.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        
        base_group = QGroupBox("Metadata")
        base_layout = QFormLayout()
        self.program_path = QLineEdit()
        self.program_path.setPlaceholderText("Path for executable / Interpreter and targeted script")
        base_layout.addRow("Path:", self.create_path_selector(self.program_path))
        self.program_name = QLineEdit()
        base_layout.addRow("Name:", self.program_name)
        self.program_version = QLineEdit()
        base_layout.addRow("Version:", self.program_version)
        self.icon_path = QLineEdit()
        base_layout.addRow("Icon:", self.create_path_selector(
            self.icon_path, 
            file_filter="Image files (*.png *.jpg *.ico *.svg)"
        ))
        self.plugin_path = QLineEdit()
        self.plugin_path.setPlaceholderText("e.g. Omics or Phylogenetics")
        base_layout.addRow("Plugin path:", self.plugin_path)
        base_group.setLayout(base_layout)
        
        param_group = QGroupBox("Arguments")
        param_layout = QVBoxLayout()
        self.param_scroll = QScrollArea()
        self.param_widget = QWidget()
        self.param_layout = QVBoxLayout()
        self.param_widget.setLayout(self.param_layout)
        self.param_scroll.setWidget(self.param_widget)
        self.param_scroll.setWidgetResizable(True)
        param_layout.addWidget(self.param_scroll)
        
        add_param_btn = QPushButton("+ add an argument")
        add_param_btn.clicked.connect(self.add_parameter)
        param_layout.addWidget(add_param_btn)
        param_group.setLayout(param_layout)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save configuration")
        save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(save_btn)
        
        layout.addWidget(base_group)
        layout.addWidget(param_group)
        layout.addLayout(btn_layout)
        content.setLayout(layout)
        
        self.config_container.setWidget(content)
        
        main_layout.addWidget(self.config_container)
        self.setLayout(main_layout)
        
        self.config_container.setVisible(True)

    def create_path_selector(self, line_edit, file_filter="All files (*.*)"):
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(line_edit)
        btn = QPushButton("Explore...")
        btn.clicked.connect(lambda: self.select_file(line_edit, file_filter))
        layout.addWidget(btn)
        container.setLayout(layout)
        return container

    def select_file(self, line_edit, file_filter="All files (*.*)"):
        path, _ = QFileDialog.getOpenFileName(filter=file_filter)
        if path:
            line_edit.setText(path)

    def add_parameter(self, data=None):
        param_widget = QGroupBox()
        param_widget.setStyleSheet("QGroupBox { border: 1px solid #ddd; margin: 5px; }")
        layout = QFormLayout()
        
        name = QLineEdit()
        name.setObjectName("name")
        layout.addRow("Name:", name)
        flag = QLineEdit()
        flag.setObjectName("flag")
        layout.addRow("Identifier (e.g. --input):", flag)
        ptype = QComboBox()
        ptype.addItems(["Options", "Number", "Text", "File"])
        layout.addRow("Type:", ptype)
        
        advanced = QCheckBox("Advanced arguments?")
        layout.addRow(advanced)
        
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        options = QTextEdit()
        options.setObjectName("options_edit")
        options.setPlaceholderText("Enter one option value per line (example):\nA\nB\nC")
        options.setMaximumHeight(100)
        options.setLineWrapMode(QTextEdit.NoWrap)
        options_layout.addWidget(options)
        options_group.setLayout(options_layout)
        options_group.setVisible(False)
        layout.addRow(options_group)
        
        def toggle_options(typ):
            options_group.setVisible(typ == "Options")
        ptype.currentTextChanged.connect(toggle_options)
        
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(lambda: self.remove_param(param_widget))
        layout.addRow(del_btn)
        
        param_widget.setLayout(layout)
        self.param_layout.addWidget(param_widget)
        
        if data:
            name.setText(data.get('name', ''))
            flag.setText(data.get('flag', ''))
            ptype.setCurrentText(data.get('type', '文本'))
            advanced.setChecked(data.get('advanced', False))
            if ptype.currentText() == "Options":
                options.setPlainText('\n'.join(data.get('options', [])))

    def remove_param(self, widget):
        self.param_layout.removeWidget(widget)
        widget.deleteLater()

    def save_config(self):
        icon_src = self.icon_path.text()
        icon_dest = None
        if icon_src:
            plugin_dir = os.path.dirname(__file__)
            icon_dir = os.path.join(plugin_dir, "icons")
            os.makedirs(icon_dir, exist_ok=True)
            
            ext = os.path.splitext(icon_src)[1]
            icon_dest = f"icon{ext}"
            
            try:
                shutil.copy(icon_src, os.path.join(plugin_dir, icon_dest))
            except Exception as e:
                QMessageBox.warning(self, "Failed to save icon", f"Failed to copy icon: {str(e)}")
                icon_dest = None

        config = {
            "program_path": self.program_path.text(),
            "program_name": self.program_name.text(),
            "version": self.program_version.text(),
            "icon": icon_dest or "",
            "params": [],
            "placement": {
                "path": self.plugin_path.text().strip() or 'CLI Bridge',
                "menu": 'true',
                "toolbar": 'false',
                "icon": icon_dest or ""
            }
        }
        
        for i in range(self.param_layout.count()):
            widget = self.param_layout.itemAt(i).widget()
            if not widget: continue
            
            param = {
                "name": self._find_child_text(widget, QLineEdit, "name"),
                "flag": self._find_child_text(widget, QLineEdit, "flag"),
                "type": widget.findChild(QComboBox).currentText(),
                "advanced": widget.findChild(QCheckBox).isChecked(),
                "options": [line.strip() for line in widget.findChild(QTextEdit, "options_edit").toPlainText().split('\n') if line.strip()]
            }
            config["params"].append(param)
        
        dir_path = os.path.dirname(__file__)
        with open(os.path.join(dir_path, 'bridge_config.json'), 'w') as f:
            json.dump(config, f, indent=2)
            
        config_ini = ConfigParser()
        config_ini['metadata'] = {
            'name': config['program_name'],
            'version': config['version'],
            'author': 'Bridge Plugin',
            'description': f'CLI Bridge Plugin for {config["program_name"]}'
        }
        config_ini['placement'] = {
            'path': self.plugin_path.text().strip() or '',
            'menu': 'true',
            'toolbar': 'false',
            'favicon': config.get('icon', '')
        }
        config_ini['runtime'] = {
            'type': 'pyplug',
            'entry_point': 'kernel.py:BridgePlugin',
            'config': 'bridge_config.json'
        }
        
        with open(os.path.join(dir_path, 'settings.ini'), 'w', encoding='utf-8') as f:
            config_ini.write(f, space_around_delimiters=False)
        
        self.load_config()
        QMessageBox.information(self, "Saved", "Configuration has been saved.", QMessageBox.Ok)
        self.saved.emit()

    def _find_child_text(self, parent, widget_type, name):
        widget = parent.findChild(widget_type, name, Qt.FindChildrenRecursively)
        return widget.text() if widget else ""

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'bridge_config.json')
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
                # 如果存在有效配置则隐藏空状态
                if config.get('program_path') or config.get('params'):
                    self.toggle_ui_visibility(has_config=True)
                
                self.program_path.setText(config.get('program_path', ''))
                self.program_name.setText(config.get('program_name', ''))
                self.program_version.setText(config.get('version', ''))
                self.icon_path.setText(config.get('icon', ''))
                self.plugin_path.setText(config.get('placement', {}).get('path', ''))
                for param in config.get('params', []):
                    self.add_parameter(param)
        else:
            self.toggle_ui_visibility(has_config=False)

    def toggle_ui_visibility(self, has_config=True):  # 强制设为True
        self.config_container.setVisible(True)

    def clone_template(self):
        try:

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"newplugin_{timestamp}"
            dest_path = os.path.join("plugins", new_name)
            
            src_path = os.path.dirname(os.path.abspath(__file__))
            
            if os.path.exists(dest_path):
                raise Exception("Target directory already exists")
            
            # copy directory
            shutil.copytree(src_path, dest_path)
            
            # delete existing config
            config_path = os.path.join(dest_path, 'bridge_config.json')
            if os.path.exists(config_path):
                os.remove(config_path)
                
            # modify settings.ini
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ini_path = os.path.join(dest_path, "settings.ini")
            config = ConfigParser()
            config.read(ini_path, encoding='utf-8-sig')
            config['metadata']['name'] = f"Untitled Bridge_{timestamp}"
            with open(ini_path, 'w', encoding='utf-8-sig') as f:
                config.write(f)

            bat_path = os.path.join(dest_path, "Start Configuration.bat")
            with open(bat_path, 'w', encoding='gbk') as f:
                f.write(f"""@echo off
echo Starting configuration wizard...
start pythonw "{os.path.basename(__file__)}"
echo If the configuration window does not open automatically, please double-click the kernel.py file
pause
""")
            
            print(f"Created start script: {bat_path}")
            
            # open explorer
            if sys.platform == 'win32':
                os.startfile(dest_path)
            else:
                subprocess.Popen(['xdg-open', dest_path])
            
            QMessageBox.information(self, "Clone successful", 
                f"New template created to:\n{dest_path}\n\n" 
                f"Please double-click the 'Start Configuration.bat' file in the directory to configure", 
                QMessageBox.Ok)
            
        except Exception as e:
            print(f"Failed to create batch file: {str(e)}")  # 输出详细错误
            QMessageBox.critical(self, "Clone failed", 
                f"Failed to create new template: {str(e)}", 
                QMessageBox.Ok)

    def load_existing_config(self, config):
        self.program_path.setText(config.get('program_path', ''))
        self.program_name.setText(config.get('program_name', ''))
        self.program_version.setText(config.get('version', ''))
        self.icon_path.setText(config.get('icon', ''))
        self.plugin_path.setText(config.get('placement', {}).get('path', ''))
        
        while self.param_layout.count():
            item = self.param_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        for param in config.get('params', []):
            self.add_parameter(param)

class BridgePlugin(QWidget):
    def __init__(self, plugin_meta=None):
        super().__init__()
        if not plugin_meta:
            # compatible with old call
            plugin_meta = {
                'dir': os.path.dirname(__file__),
                'meta': {'name': 'YR CLI Bridge Customizer', 'version': '1.0.0'}
            }
        
        # load config
        self.config = self.load_config(plugin_meta)
        self.plugin_dir = plugin_meta['dir']
        
        # validate necessary config
        if not self.config.get('program_path') or len(self.config.get('params', [])) == 0:
            self.show_config_guide()
            self.valid_config = False
        else:
            self.valid_config = True
        
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        if self.valid_config:
            self.init_ui()

    def load_config(self, plugin_meta):
        config_path = os.path.join(plugin_meta['dir'], 'bridge_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    # compatible with old favicon config
                    if 'icon' not in config:
                        config['icon'] = config.get('placement', {}).get('favicon', '')
                    return config
            except Exception as e:
                print(f"Failed to load config: {str(e)}")
                
        return {
            'program_name': plugin_meta['meta'].get('name', 'Untitled Program'),
            'version': plugin_meta['meta'].get('version', '1.0.0'),
            'params': [],
            'program_path': '',  # add empty path field
            'icon': '',  # add empty icon path
            'placement': {
                'path': 'bridged_plugins',
                'menu': 'true',
                'toolbar': 'false'
            }
        }

    def show_config_guide(self):
        layout = QVBoxLayout()
        msg = QLabel("""<h3>Bridge Plugin Configuration Wizard</h3>
        <p style='color:#666;margin:10px'>Detected that this bridge plugin is not configured: ❌ No executable file path or ❌ No defined any parameters</p>
        <p style='color:#666;margin:10px'>You can try to fix the plugin or create a new plugin</p>
        <hr style='margin:5px 0'>
        <h4>Plugin Configuration Guide</h4>
        <ol style='color:#666;margin-left:15px'>
        <li>Click the clone button to create a new template</li>
        <li>Run <span style='color:blue'>kernel.py</span> or <span style='color:blue'>click Start Configuration.bat</span> to configure the program path and parameters</li>
        <li>Save the configuration and restart the main program to load the new plugin</li>
        </ol>
        <hr style='margin:5px 0'>
        <h4>FAQ</h4>
        <br>
        <span>If your configured plugin cannot run normally:</span>
        <ul style='color:#666'>
        <span>Check if <span style='color:blue'>settings.ini</span> and <span style='color:blue'>bridge_config.json</span> exist and have not been modified incorrectly</span>
        </ul>
        <p>If kernel.py cannot run/the configuration window cannot display normally:</p>
        <ul style='color:#666'>
        <p style='color:#666'>Missing Python 3.10 environment/dependencies PyQt5 sys json subprocess datetime shutil.</p>
        <p style='color:#666'>It is recommended to clone the plugin and restart the program to find the new plugin and use the built-in button to load the configurator.</p>
        </ul>
        """)
        msg.setWordWrap(True)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        inspect_btn = QPushButton("Open folder to check and fix errors")
        inspect_btn.clicked.connect(lambda: self.open_plugin_folder())
        clone_btn = QPushButton("Clone new bridge plugin template")
        clone_btn.clicked.connect(self.open_configurator)
        
        btn_layout.addWidget(inspect_btn)
        btn_layout.addWidget(clone_btn)
        
        # 独立运行按钮
        standalone_btn = QPushButton("Run configurator (computer without Python 3.10 environment or missing dependencies)")
        standalone_btn.clicked.connect(self.run_standalone_configurator)
        standalone_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        layout.addWidget(msg)
        layout.addLayout(btn_layout)
        layout.addWidget(standalone_btn)
        self.setLayout(layout)

    def open_plugin_folder(self):
        path = os.path.abspath(self.plugin_dir)
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

    def open_configurator(self):
        configurator = BridgeConfigurator()
        configurator.load_existing_config({
            'program_path': self.config['program_path'],
            'program_name': self.config['program_name'],
            'version': self.config['version'],
            'icon': self.config.get('icon', ''),
            'placement': self.config.get('placement', {}),
            'params': self.config['params']
        })
        configurator.saved.connect(self.reload_config)
        configurator.show()

    def reload_config(self):
        self.config = self.load_config({
            'dir': self.plugin_dir,
            'meta': {
                'name': self.config['program_name'],
                'version': self.config['version']
            }
        })
        # clear old interface and reinitialize
        self.setLayout(QVBoxLayout())
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # title
        title = QLabel(f"{self.config['program_name']} v{self.config['version']}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # parameter form
        form = QFormLayout()
        self.param_widgets = {}
        
        # separate normal parameters and advanced parameters
        advanced_group = QGroupBox("Advanced parameters (click to expand)")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QFormLayout()
        
        for param in self.config['params']:
            widget = self.create_param_widget(param)
            if param['advanced']:
                advanced_layout.addRow(QLabel(param['name']), widget)
            else:
                form.addRow(QLabel(param['name']), widget)
            self.param_widgets[param['flag']] = widget
        
        advanced_group.setLayout(advanced_layout)
        layout.addLayout(form)
        layout.addWidget(advanced_group)
        
        # run control
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        # set fixed width font
        font_path = "./fonts/CONSOLA.TTF"
        font_id = QFontDatabase.addApplicationFont(font_path)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        if font_id != -1:
        # get font family name
            families = QFontDatabase.applicationFontFamilies(font_id)
            if not families:
                print("⚠️ Failed to get font family, using default font")
            else:
                font_family = families[0]
                font = QFont(font_family, 10)
        self.output.setFont(font)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.execute)
        self.stop_btn = QPushButton("Stop")
        config_btn = QPushButton("Adjust configuration")
        config_btn.clicked.connect(self.open_configurator)
        
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(run_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(config_btn)
        
        layout.addWidget(self.output)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def create_param_widget(self, param):
        if param['type'] == 'Options':
            combo = QComboBox()
            combo.addItems(param['options'])
            return combo
        elif param['type'] == 'Number':
            spin = QSpinBox()
            spin.setRange(0, 1000000)
            return spin
        elif param['type'] == 'File':
            container = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0,0,0,0)
            edit = QLineEdit()
            btn = QPushButton("Browse...")
            btn.clicked.connect(lambda: self.select_file(edit))
            layout.addWidget(edit)
            layout.addWidget(btn)
            container.setLayout(layout)
            return container
        else:  # text
            return QLineEdit()

    def select_file(self, edit):
        path, _ = QFileDialog.getOpenFileName()
        if path:
            edit.setText(path)

    def execute(self):
        # update button status when starting to execute
        self.stop_btn.setEnabled(True)
        self.output.clear()
        
        cmd = [self.config['program_path']]
        for flag, widget in self.param_widgets.items():
            value = None
            if isinstance(widget, QComboBox):
                value = widget.currentText()
            elif isinstance(widget, QSpinBox):
                value = str(widget.value())
            elif isinstance(widget, QLineEdit):
                value = widget.text()
            elif isinstance(widget, QWidget):
                value = widget.findChild(QLineEdit).text()
            
            if value:
                cmd += [flag, value]
        
        self.output.append(f"Execute command: {' '.join(cmd)}")
        # set working directory to program directory
        work_dir = os.path.dirname(self.config['program_path'])
        self.process.setWorkingDirectory(work_dir)
        
        # use parameter list to execute
        self.process.start(cmd[0], cmd[1:])
        
        # add error handling
        self.process.errorOccurred.connect(self.handle_process_error)

    def handle_output(self):
        # merge standard output and error output
        output = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace').strip()
        error = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace').strip()
        
        if output:
            self.output.append(output)
        if error:
            self.output.append(f"<font color='red'>{error}</font>")
        
        # auto scroll to bottom
        self.output.ensureCursorVisible()
        cursor = self.output.textCursor()
        cursor.movePosition(cursor.End)
        self.output.setTextCursor(cursor)
        
        # update button status when process ends
        if self.process.state() == QProcess.NotRunning:
            self.stop_btn.setEnabled(False)

    def handle_error(self):
        data = self.process.readAllStandardError()
        self.output.append(f"<font color='red'>{data.data().decode().strip()}</font>")

    def handle_process_error(self, error):
        error_types = {
            QProcess.FailedToStart: "Program failed to start (path error or permission denied)",
            QProcess.Crashed: "Program crashed unexpectedly",
            QProcess.Timedout: "Operation timed out",
            QProcess.WriteError: "Failed to write data",
            QProcess.ReadError: "Failed to read data",
            QProcess.UnknownError: "Unknown error"
        }
        error_msg = error_types.get(error, f"Error code: {int(error)}")
        self.output.append(f"<font color='darkred'>⚠️ Process exception: {error_msg}</font>")
        self.stop_btn.setEnabled(False)

    def terminate_process(self):
        """terminate running process"""
        if self.process.state() == QProcess.Running:
            self.process.terminate()
            self.output.append("<font color='orange'>Terminating...</font>")
            QTimer.singleShot(2000, self.kill_if_not_terminated)  # 2 seconds later force to terminate

    def kill_if_not_terminated(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.output.append("<font color='red'>Program has been terminated.</font>")

    def run_standalone_configurator(self):
        """run standalone configurator"""
        configurator = BridgeConfigurator()
        configurator.show()

    def run(self):
        """implement interface needed by main program"""
        if not self.valid_config:
            return self  # return guide interface
        return self  # return self as interface component

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = BridgeConfigurator()
    window.show()
    sys.exit(app.exec_())
