from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTreeWidget, QTreeWidgetItem, QColorDialog, QScrollArea,
                            QListWidget, QListWidgetItem, QLabel, QFormLayout, QLineEdit, 
                            QDialog, QDialogButtonBox, QStyledItemDelegate, QMessageBox, QStyle, QMenu, QSizePolicy)
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize, QPoint, QEvent, QRect
#from core.plugin_base import BasePlugin
import json
import os
import numpy as np

class GradientBar(QWidget):
    def __init__(self, colors, height=32):
        super().__init__()
        self.colors = colors
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect()
        
        gradient = QLinearGradient(rect.left(), rect.center().y(),
                                 rect.right(), rect.center().y())
        for pos, color in self.colors:
            gradient.setColorAt(pos, color)
        
        painter.fillRect(rect, gradient)

class ColorEditor(QDialog):
    def __init__(self, parent=None, edit_mode=False):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self.setWindowTitle("Color Editor")
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumSize(400, 500)
        self.current_color = QColor(Qt.white)
        self.edit_mode = edit_mode
        self.is_gradient = False  # 初始化is_gradient属性
        self.init_ui()
        self.add_path_editors()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.color_stops = []
        self.stop_list = QListWidget()
        self.stop_list.itemSelectionChanged.connect(self.on_stop_selected)
        layout.addWidget(QLabel("Color Segment Management"))
        layout.addWidget(self.stop_list)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Add Color Segment")
        self.add_btn.clicked.connect(self.add_stop)
        btn_layout.addWidget(self.add_btn)
        
        self.del_btn = QPushButton("🗑️ Delete Selected")
        self.del_btn.clicked.connect(self.del_stop)
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)
        
        self.color_picker = QColorDialog()
        self.color_picker.currentColorChanged.connect(self.update_color)
        
        self.hex_edit = QLineEdit()
        self.hex_edit.setPlaceholderText("HEX Color Value")
        self.hex_edit.textEdited.connect(self.hex_changed)
        self.hex_edit.returnPressed.connect(self._handle_enter)
        
        self.rgb_edit = QLineEdit()
        self.rgb_edit.setPlaceholderText("RGB (0-255, comma separated)")
        self.rgb_edit.textEdited.connect(self.rgb_changed)
        self.rgb_edit.returnPressed.connect(self._handle_enter)
        
        self.cmyk_edit = QLineEdit()
        self.cmyk_edit.setPlaceholderText("CMYK (0-100%, comma separated)")
        self.cmyk_edit.textEdited.connect(self.cmyk_changed)
        self.cmyk_edit.returnPressed.connect(self._handle_enter)
        
        form = QFormLayout()
        form.addRow("HEX:", self.hex_edit)
        form.addRow("RGB:", self.rgb_edit)
        form.addRow("CMYK:", self.cmyk_edit)
        layout.addLayout(form)
        
        # Preview
        self.preview = QLabel()
        self.preview.setFixedHeight(40)
        layout.addWidget(self.preview)
        
        self.update_preview()
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def add_path_editors(self):
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Path (use / to separate)")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Palette Name")
        
        form = self.findChild(QFormLayout)
        form.insertRow(0, "Path:", self.path_edit)
        form.insertRow(1, "Name:", self.name_edit)
        
        # Set visibility based on edit mode
        self.path_edit.setVisible(self.edit_mode)
        self.name_edit.setVisible(self.edit_mode)

    def add_stop(self):
        item = QListWidgetItem(f"Color Segment {len(self.color_stops)+1}")
        item.setData(Qt.UserRole, QColor(Qt.white))
        
        # Smart calculation of insertion position
        if not self.color_stops:
            pos = 0.0
        elif self.stop_list.currentRow() == -1:
            # Insert between existing color segments
            existing_positions = [c[0] for c in self.color_stops]
            for i in range(len(existing_positions)-1):
                if existing_positions[i+1] - existing_positions[i] > 0.1:
                    pos = (existing_positions[i] + existing_positions[i+1]) / 2
                    break
            else:
                pos = 1.0
        else:
            current_index = self.stop_list.currentRow()
            if current_index < len(self.color_stops)-1:
                # Insert after the current selected segment
                prev_pos = self.color_stops[current_index][0]
                next_pos = self.color_stops[current_index+1][0]
                pos = (prev_pos + next_pos) / 2
            else:
                # Insert after the last segment
                pos = min(1.0, self.color_stops[-1][0] + 0.1)
        
        self.color_stops.insert(current_index+1 if self.stop_list.currentRow() != -1 else len(self.color_stops), 
                              (round(pos, 2), QColor(Qt.white)))
        self.stop_list.insertItem(self.stop_list.currentRow()+1, item)
        self.stop_list.setCurrentItem(item)
        self.adjustSize()
        
    def del_stop(self):
        row = self.stop_list.currentRow()
        if row >= 0:
            self.stop_list.takeItem(row)
            del self.color_stops[row]
        
    def on_stop_selected(self):
        row = self.stop_list.currentRow()
        if row >= 0:
            # Safe unpacking of color segment data
            stop_data = self.color_stops[row]
            if isinstance(stop_data, tuple):
                _, color = stop_data
            else:  # Handle discrete color format
                color = stop_data
            self.current_color = color
            self.update_editors()
            self.color_picker.setCurrentColor(color)
        
    def update_color(self, color):
        self.current_color = color
        row = self.stop_list.currentRow()
        if row >= 0:
            # Keep position information when updating color segment data
            stop_data = self.color_stops[row]
            if isinstance(stop_data, tuple):
                pos = stop_data[0]
                self.color_stops[row] = (pos, color)
            else:
                # Generate default position for discrete colors
                pos = row / max(1, len(self.color_stops)-1)
                self.color_stops[row] = (pos, color)
            self.stop_list.currentItem().setData(Qt.UserRole, color)
            self.update_editors()
            self.update_preview()
        
    def update_editors(self):
        color = self.current_color
        self.hex_edit.setText(color.name())
        self.rgb_edit.setText(f"{color.red()}, {color.green()}, {color.blue()}")
        c, m, y, k, _ = color.getCmyk()
        self.cmyk_edit.setText(f"{c/2.55:.0f}%, {m/2.55:.0f}%, {y/2.55:.0f}%, {k/2.55:.0f}%")
        
    def hex_changed(self, text):
        text = text.lstrip('#')
        if not text:
            return
            
        # Auto-complete short format HEX
        if len(text) == 3:
            text = ''.join([c*2 for c in text])
        elif len(text) not in (6, 8):  # Support alpha channel
            return
            
        try:
            color = QColor(f'#{text}')
        except:
            return
            
        if color.isValid():
            self._update_color(color)
            self.update_preview()

    def rgb_changed(self, text):
        try:
            parts = list(map(int, text.split(',')))
            if len(parts) != 3:
                return
            r, g, b = [max(0, min(255, x)) for x in parts]
            self._update_color(QColor(r, g, b))
            self.update_preview()
        except:
            pass

    def cmyk_changed(self, text):
        try:
            parts = list(map(lambda x: int(x.strip('%')), text.split(',')))
            if len(parts) != 4:
                return
            c, m, y, k = [max(0, min(100, x)) for x in parts]
            color = QColor()
            color.setCmyk(
                int(c * 2.55), 
                int(m * 2.55), 
                int(y * 2.55), 
                int(k * 2.55)
            )
            self._update_color(color)
            self.update_preview()
        except:
            pass

    def _update_color(self, color):
        if color.isValid() and color != self.current_color:

            self.current_color = color            

            row = self.stop_list.currentRow()
            if row >= 0:
                pos, _ = self.color_stops[row]
                self.color_stops[row] = (pos, color)
                self.stop_list.currentItem().setData(Qt.UserRole, color)
            
            self.color_picker.blockSignals(True)
            self.color_picker.setCurrentColor(color)
            self.color_picker.blockSignals(False)
            
            self._update_editors()
            self.update_preview()

    def _update_editors(self):
        """Update all input box values"""
        color = self.current_color
        self.hex_edit.blockSignals(True)
        self.rgb_edit.blockSignals(True)
        self.cmyk_edit.blockSignals(True)
        
        self.hex_edit.setText(color.name())
        self.rgb_edit.setText(f"{color.red()}, {color.green()}, {color.blue()}")
        
        c = color.cyan() / 2.55
        m = color.magenta() / 2.55
        y = color.yellow() / 2.55
        k = color.black() / 2.55
        self.cmyk_edit.setText(f"{c:.0f}%, {m:.0f}%, {y:.0f}%, {k:.0f}%")
        
        self.hex_edit.blockSignals(False)
        self.rgb_edit.blockSignals(False)
        self.cmyk_edit.blockSignals(False)

    def update_preview(self):
        pixmap = QPixmap(200, 40)
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), self.current_color)
        painter.end()
        self.preview.setPixmap(pixmap)

    def _handle_enter(self):
        """Handle enter key event"""
        sender = self.sender()
        if sender == self.hex_edit:
            self.hex_changed(sender.text())
        elif sender == self.rgb_edit:
            self.rgb_changed(sender.text())
        elif sender == self.cmyk_edit:
            self.cmyk_changed(sender.text())
        sender.clearFocus()

    def set_palette_data(self, name, path, colors, is_gradient):
        self.path_edit.setText(path)
        self.name_edit.setText(name)
        self.is_gradient = is_gradient
        
        if is_gradient:
            # Gradient colors use (position, color) format
            self.color_stops = colors
        else:
            # Handle discrete color format
            self.color_stops = []
            if colors:
                if isinstance(colors[0], tuple):
                    # If unexpected tuple format, extract colors
                    colors = [c for _, c in colors]
                # Create evenly spaced positions (0.0, 0.5, 1.0 etc.)
                count = len(colors)
                if count > 1:
                    self.color_stops = [(i/(count-1), color) for i, color in enumerate(colors)]
                elif count == 1:
                    self.color_stops = [(0.0, colors[0])]
        
        self.stop_list.clear()
        for pos, color in self.color_stops:
            item = QListWidgetItem(f"Color Segment {len(self.stop_list)+1}")
            item.setData(Qt.UserRole, color)
            self.stop_list.addItem(item)
        self.update_editors()
        self.update_preview()

    def get_palette_data(self):
        path = self.path_edit.text().strip()
        name = self.name_edit.text().strip()
        path = path.replace('\\', '/').replace('//', '/').strip('/')
        if not name:
            name = "Unnamed"
        return (
            name,
            path,
            self.color_stops  # Whether gradient or discrete, keep the same format
        )

# class TreeItemDelegate(QStyledItemDelegate):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self._hover_row = -1
#         self.delete_icon = QIcon("./icons/delete.svg")  # 需要准备关闭图标资源

#     def paint(self, painter, option, index):
#         super().paint(painter, option, index)
#         # 在右侧绘制删除按钮
#         if option.state & QStyle.State_MouseOver:
#             rect = option.rect
#             btn_size = 16
#             btn_rect = QRect(
#                 rect.right() - btn_size - 4,
#                 rect.top() + (rect.height() - btn_size) // 2,
#                 btn_size,
#                 btn_size
#             )
#             self.delete_icon.paint(painter, btn_rect)

#     def editorEvent(self, event, model, option, index):
#         if event.type() == QEvent.MouseMove:
#             self._hover_row = index.row()
#             option.widget.viewport().update()
#         return super().editorEvent(event, model, option, index)

class CustomPalettePlugin(QWidget):
    def __init__(self):
        super().__init__()
        # Ensure data structure is initialized correctly
        self.palettes = {
            'gradients': {},
            'discrete': {}
        }
        # Load data correctly
        loaded_data = self.load_palettes()
        self.palettes['gradients'].update(loaded_data['gradients'])
        self.palettes['discrete'].update(loaded_data['discrete'])
        self.create_widget()

        
    def create_widget(self):
        main_layout = QHBoxLayout()
        widget = QScrollArea()
        widget.setWidgetResizable(True)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Operation buttons
        btn_layout = QHBoxLayout()
        self.add_gradient_btn = QPushButton("➕ Add Gradient Color")
        self.add_gradient_btn.clicked.connect(lambda: self.add_gradient())
        
        self.add_discrete_btn = QPushButton("🎨 Add Discrete Color")
        self.add_discrete_btn.clicked.connect(lambda: self.add_discrete())
        
        btn_layout.addWidget(self.add_gradient_btn)
        btn_layout.addWidget(self.add_discrete_btn)
        layout.addLayout(btn_layout)
        
        # Palette list
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(280, 32))
        self.tree.setStyleSheet("""
            QTreeWidget {
                //font-size: 13px;
                background: #f8f9fa;
            }
            QTreeWidget::item {
                height: 36px;
                padding: 4px 8px;
                border-bottom: 1px solid #e9ecef;
            }
        """)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)  # Enable right-click menu
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.refresh_tree()
        layout.addWidget(self.tree)

        # self.tree.setItemDelegate(TreeItemDelegate(self.tree))
        self.tree.setMouseTracking(True)  # Enable mouse tracking
        self.tree.viewport().installEventFilter(self)  # Install event filter
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)  # Add double click event connection
        
        widget.setWidget(container)
        main_layout.addWidget(widget)
        self.setLayout(main_layout)
        
    def refresh_tree(self):
        self.tree.clear()
        
        def add_to_tree(root, parts, item):
            if not parts:
                root.addChild(item)
                return
            current_part = parts[0]
            # Find existing node
            existing = None
            for i in range(root.childCount()):
                child = root.child(i)
                if child.text(0) == current_part:
                    existing = child
                    break
            if not existing:
                existing = QTreeWidgetItem([current_part])
                existing.setIcon(0, QIcon("./icons/folder.svg"))  # Add folder icon
                existing.setFlags(existing.flags() | Qt.ItemIsEnabled)
                existing.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
                root.addChild(existing)
            add_to_tree(existing, parts[1:], item)

        # Create new root node
        grad_root = QTreeWidgetItem()
        grad_root.setText(0, "🌈 Gradient Color Palette")
        grad_root.setFlags(grad_root.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        grad_root.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        
        disc_root = QTreeWidgetItem()
        disc_root.setText(0, "🎨 Discrete Color Palette")
        disc_root.setFlags(disc_root.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        disc_root.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)

        # Handle gradient colors
        for full_path, colors in self.palettes['gradients'].items():
            item = QTreeWidgetItem()
            item.setIcon(0, self.create_gradient_icon(colors))
            *path_parts, name = full_path.split('/')
            item.setText(0, name)
            item.colors = colors
            item.setData(0, Qt.UserRole, full_path)
            parts = path_parts
            add_to_tree(grad_root, parts, item)

        # Handle discrete colors
        for full_path, colors in self.palettes['discrete'].items():
            item = QTreeWidgetItem()
            item.setIcon(0, self.create_discrete_icon([c for _, c in colors]))
            item.setToolTip(0, full_path)
            item.setData(0, Qt.UserRole, full_path)  # Store full path
            *path_parts, name = full_path.split('/')
            item.setText(0, name)
            item.colors = colors
            item.setData(0, Qt.UserRole, full_path)
            parts = path_parts
            add_to_tree(disc_root, parts, item)

        # Add root node to tree widget
        self.tree.addTopLevelItem(grad_root)
        self.tree.addTopLevelItem(disc_root)
        
        # Expand all nodes
        self.tree.expandToDepth(3)
        
    def create_gradient_icon(self, colors):
        pixmap = QPixmap(280, 32)
        painter = QPainter(pixmap)
        
        # Sort by position and remove duplicates
        # sorted_colors = sorted({c[0]: c[1] for c in colors}.items())
        # if not sorted_colors:
        #     return QIcon(pixmap)
        sorted_colors = colors
            
        # Create gradient object
        gradient = QLinearGradient(0, 0, 280, 0)
        width = 1.00/(len(sorted_colors)-1)

        for i in range(len(sorted_colors)):
            gradient.setColorAt(i*width, sorted_colors[i][1])
        
        painter.fillRect(pixmap.rect(), gradient)
        painter.end()
        return QIcon(pixmap)
        # # 添加所有颜色段
        # for pos, color in sorted_colors:
        #     # 确保位置在0-1范围内
        #     pos = max(0.0, min(1.0, pos))
        #     gradient.setColorAt(pos, color)
        
        # # 在颜色段之间创建插值
        # if len(sorted_colors) >= 2:
        #     # 生成插值点
        #     positions = np.linspace(0, 1, 256)
            
        #     # 获取颜色段位置和颜色
        #     stops = np.array([c[0] for c in sorted_colors])
        #     colors_rgba = np.array([[c.red(), c.green(), c.blue(), c.alpha()] 
        #                            for c in [c[1] for c in sorted_colors]])
            
        #     # 创建插值函数
        #     interp_r = np.interp(positions, stops, colors_rgba[:,0])
        #     interp_g = np.interp(positions, stops, colors_rgba[:,1])
        #     interp_b = np.interp(positions, stops, colors_rgba[:,2])
        #     interp_a = np.interp(positions, stops, colors_rgba[:,3])
            
        #     # 重新设置渐变颜色
        #     for i, (r, g, b, a) in enumerate(zip(interp_r, interp_g, interp_b, interp_a)):
        #         gradient.setColorAt(i/255.0, QColor(int(r), int(g), int(b), int(a)))
        
    def create_discrete_icon(self, colors):
        pixmap = QPixmap(280, 32)
        painter = QPainter(pixmap)
        
        total_width = 280
        color_count = len(colors)
        if color_count == 0:
            return QIcon()
            
        step = total_width // color_count
        remainder = total_width % color_count
        
        for i, color in enumerate(colors):
            # Handle width of the last color block
            width = step + (remainder if i == color_count-1 else 0)
            x = i * step
            painter.fillRect(int(x), 0, int(width), 32, color)
        
        painter.end()
        return QIcon(pixmap)
        
    def add_gradient(self):
        try:
            main_window = self.window() if self else None
            editor = ColorEditor(main_window, edit_mode=True)
            if editor.exec_() == QDialog.Accepted:
                name, path, colors = editor.get_palette_data()
                # Uniform path generation: use standard path splitting
                path_parts = [p.strip() for p in path.split('/') if p.strip()]
                full_path = '/'.join(path_parts + [name.strip()])
                self.palettes['gradients'][full_path] = colors
                self.save_palettes()
                self.refresh_tree()
        except Exception as e:
            print(f"Failed to open color editor: {str(e)}")
            
    def add_discrete(self):
        try:
            main_window = self.window() if self else None
            editor = ColorEditor(main_window, edit_mode=True)
            if editor.exec_() == QDialog.Accepted:
                name, path, colors = editor.get_palette_data()
                full_path = "/".join(filter(None, [path.strip('/'), name.strip('/')]))  # 统一路径生成方式
                self.palettes['discrete'][full_path] = colors
                self.save_palettes()
                self.refresh_tree()
        except Exception as e:
            print(f"Failed to open color editor: {str(e)}")
        
    def load_palettes(self):
        # path = os.path.join(self.config['dir'], 'palettes.json')
        path = os.path.join(os.getcwd(), 'plugins', 'color_palette_selfdef', 'palettes.json')
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print("Loaded palette keys:")
                    print("Gradient colors:", data['gradients'].keys())
                    print("Discrete colors:", data['discrete'].keys())
                    return self._convert_color_data(data)
            except Exception as e:
                print(f"Failed to load palette data: {str(e)}")
        # Return default empty data
        return {'gradients': {}, 'discrete': {}}
        
    def _convert_color_data(self, data):
        """Convert color strings in JSON to QColor objects"""
        converted = {'gradients': {}, 'discrete': {}}
        
        # Handle gradient colors (keep original logic)
        for name, stops in data.get('gradients', {}).items():
            converted['gradients'][name] = [
                (float(pos), QColor(str(color_str))) for pos, color_str in stops
            ]
        
        # Fix discrete color processing logic
        for name, colors in data.get('discrete', {}).items():
            color_tuples = []
            # Compatible with new and old data formats
            for entry in colors:
                if isinstance(entry, list):  # Old format [position, color]
                    pos = float(entry[0])
                    color = QColor(str(entry[1]))
                else:  # New format (position, QColor) serialized form
                    pos = float(entry[0]) if isinstance(entry, (list, tuple)) else 0.0
                    color = QColor(str(entry[1])) if isinstance(entry, (list, tuple)) else QColor(str(entry))
                color_tuples.append( (pos, color) )
            converted['discrete'][name] = color_tuples  # Keep original key name
        
        return converted
        
    def on_item_double_clicked(self, item, column):
        # Display the same menu as right-click
        pos = self.tree.visualItemRect(item).center()
        self.show_context_menu(pos)

    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item and hasattr(item, 'colors'):
            menu = QMenu()
            
            # Add operations with icons
            delete_action = menu.addAction(QIcon("./icons/delete.svg"), "Delete")
            delete_action.triggered.connect(lambda: self.delete_palette(item))
            
            edit_action = menu.addAction(QIcon("./icons/edit.svg"), "Edit")
            edit_action.triggered.connect(lambda: self.edit_palette_item(item))
            
            menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def edit_palette_item(self, item):
        full_path = item.data(0, Qt.UserRole)
        if not full_path:
            # Rebuild path logic is the same as deletion
            parts = []
            parent = item.parent()
            while parent and parent.parent():
                parts.append(parent.text(0))
                parent = parent.parent()
            parts.reverse()
            full_path = "/".join(parts + [item.text(0)]).strip('/')
        
        # Get category
        def find_root_parent(current_item):
            while current_item.parent():
                current_item = current_item.parent()
            return current_item
        
        root_parent = find_root_parent(item)
        is_gradient = root_parent.text(0).startswith("🌈")
        
        # Get color data
        category = 'gradients' if is_gradient else 'discrete'
        colors = self.palettes[category].get(full_path, [])
        
        if colors:
            self.edit_palette(full_path, colors, is_gradient)

    def delete_palette(self, item):
        full_path = item.data(0, Qt.UserRole)
        if not full_path:
            # Precise rebuild path logic
            parts = []
            parent = item.parent()
            while parent and parent.parent():  # Exclude root node
                parts.append(parent.text(0))
                parent = parent.parent()
            parts.reverse()
            full_path = "/".join(parts + [item.text(0)]).strip('/')  # Key modification
        
        # New category judgment logic: traverse to top parent node
        def find_root_parent(current_item):
            while current_item.parent():
                current_item = current_item.parent()
            return current_item
        
        root_parent = find_root_parent(item)
        if root_parent.text(0).startswith("🌈"):
            category = 'gradients'
        else:
            category = 'discrete'

        # Debug output
        print(f"Category judgment result: {category}")
        print(f"Full path: {full_path}")
        print(f"Current {category} palette keys: {self.palettes[category].keys()}")
        
        # Confirm dialog
        reply = QMessageBox.question(
            self,
            'Confirm Delete',
            f'Confirm to delete palette "{item.text(0)}" ?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if full_path in self.palettes[category]:
                del self.palettes[category][full_path]
            else:
                print(f"No matching key found: {full_path}")
            
            self.save_palettes()
            self.refresh_tree()

    def edit_palette(self, full_path, colors, is_gradient):
        try:
            print(f"Editing palette: {full_path}")
            print(f"Original color data: {colors[:2]}... (total {len(colors)} color segments)")
            
            # Handle empty path case
            if '/' not in full_path:
                path_parts = []
                name = full_path
            else:
                *path_parts, name = full_path.split('/')
            path = '/'.join(path_parts) if path_parts else ""
            
            main_window = self.window() if self else None
            editor = ColorEditor(main_window, edit_mode=True)
            
            # Uniform data format: discrete colors use pure color list
            if not is_gradient:
                print("Processing discrete color palette data format conversion")
                # Deep clean data format
                clean_colors = []
                for c in colors:
                    if isinstance(c, tuple):
                        clean_colors.append(c[1])
                        print(f"Convert tuple data: {c} -> {c[1]}")
                    elif isinstance(c, QColor):
                        clean_colors.append(c)
                    else:
                        print(f"Found abnormal data format: {type(c)} - {c}")
                        clean_colors.append(QColor(c))
                colors = clean_colors
                print(f"Converted color data: {[c.name() for c in colors[:2]]}...")
            
            editor.set_palette_data(name, path, colors, is_gradient=is_gradient)
            
            if editor.exec_() == QDialog.Accepted:
                new_name, new_path, new_colors = editor.get_palette_data()
                new_full_path = f"{new_path}/{new_name}" if new_path else new_name
                
                # Update data
                category = 'gradients' if is_gradient else 'discrete'
                del self.palettes[category][full_path]
                self.palettes[category][new_full_path] = new_colors
                self.save_palettes()
                self.refresh_tree()
        except Exception as e:
            print(f"Failed to edit palette: {str(e)}")

    def add_to_tree(self, root, parts, item):
        if not parts:
            root.addChild(item)
            return
        current_part = parts[0]
        for i in range(root.childCount()):
            child = root.child(i)
            if child.text(0) == current_part:
                self.add_to_tree(child, parts[1:], item)
                return
        new_item = QTreeWidgetItem([current_part])
        new_item.setFlags(new_item.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        new_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        new_item.setIcon(0, QIcon())  # Folder icon can be added by yourself
        root.addChild(new_item)
        if len(parts) == 1:
            new_item.addChild(item)
        else:
            self.add_to_tree(new_item, parts[1:], item)

    def save_palettes(self):
        # path = os.path.join(self.config['dir'], 'palettes.json')
        path = os.path.join(os.getcwd(), 'plugins', 'color_palette_selfdef', 'palettes.json')
        # Convert QColor to serializable format
        save_data = {
            'gradients': {
                name: [
                    (pos, color.name()) for pos, color in colors
                ] for name, colors in self.palettes['gradients'].items()
            },
            'discrete': {
                name: [
                    (pos, color.name()) for pos, color in colors
                ] for name, colors in self.palettes['discrete'].items()
            }
        }
        print("Saved palette keys:")
        print("Gradient colors:", save_data['gradients'].keys())
        print("Discrete colors:", save_data['discrete'].keys())
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2)

    def eventFilter(self, source, event):
        if source is self.tree.viewport() and event.type() == QEvent.MouseButtonRelease:
            index = self.tree.indexAt(event.pos())
            if index.isValid():
                item = self.tree.itemFromIndex(index)
                # Calculate delete button area
                rect = self.tree.visualRect(index)
                btn_size = 16
                btn_rect = QRect(
                    rect.right() - btn_size - 4,
                    rect.top() + (rect.height() - btn_size) // 2,
                    btn_size,
                    btn_size
                )
                if btn_rect.contains(event.pos()):
                    self.delete_item(item)
                    return True
        return super().eventFilter(source, event)

    def delete_item(self, item):
        if hasattr(item, 'colors'):
            # Get parent node type (gradient or discrete)
            parent = item.parent()
            category = 'gradients' if parent.text(0).startswith("🌈") else 'discrete'
            full_path = item.text(0)
            
            # Confirm dialog
            confirm = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Confirm to delete palette '{full_path}' ?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                del self.palettes[category][full_path]
                self.save_palettes()
                self.refresh_tree() 

class Plugin:
    def run(self):
        return CustomPalettePlugin()