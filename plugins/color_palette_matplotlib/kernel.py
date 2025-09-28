import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QGroupBox,
                            QLabel, QSizePolicy, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QApplication)
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QIcon, QPainterPath
from PyQt5.QtCore import Qt, QRectF, QPoint, QSize
# from core.plugin_base import BasePlugin

try:
    from matplotlib import colormaps
except ImportError:
    colormaps = None

class ColorBar(QWidget):
    def __init__(self, cmap_name, height=30):
        super().__init__()
        self.cmap_name = cmap_name
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRectF(self.rect())
        
        # 创建渐变
        gradient = QLinearGradient(rect.left(), rect.center().y(),
                                 rect.right(), rect.center().y())
        
        try:
            cmap = colormaps[self.cmap_name]
            for i in np.linspace(0, 1, 256):
                color = cmap(i)
                gradient.setColorAt(i, QColor(*[int(c*255) for c in color]))
        except:
            gradient.setColorAt(0, Qt.red)
            gradient.setColorAt(1, Qt.blue)
        
        painter.fillRect(rect, gradient)

class ColorPalettePlugin(QWidget):
    def __init__(self):
        super().__init__()
        self.create_widget()

    def create_widget(self):
        # widget = QWidget()
        main_layout = QVBoxLayout()
        
        # 创建树形导航
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(12)
        self.tree.setIconSize(QSize(280, 32))  # 调整图标尺寸与主程序比例协调
        self.tree.setStyleSheet("""
            QTreeWidget { 
                //font-family: MiSans-Medium;
                font-size: 13px;
                color: #2d2d2d;
                background: #f8f9fa;
            }
            QTreeWidget::item {
                height: 36px;
                padding: 4px 8px;
                border-bottom: 1px solid #e9ecef;
            }
            QTreeWidget::item:hover {
                background: #e9f5fe;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background: #d1e9ff;
            }
        """)
        
        # 按官方分类创建节点
        categories = {
            "Perceptually Uniform Sequential": ['viridis', 'plasma', 'inferno', 'magma', 'cividis'],
            "Sequential": ['Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
                          'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
                          'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn'],
            "Diverging": ['PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
                         'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic'],
            "Cyclic": ['twilight', 'twilight_shifted', 'hsv'],
            "Qualitative": ['Pastel1', 'Pastel2', 'tab10', 'tab20', 'Set1', 'Set2', 'Set3',
                           'Accent', 'Dark2', 'Paired', 'Pastel2'],
            "Miscellaneous": ['flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
                             'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg', 'gist_rainbow',
                             'rainbow', 'jet', 'turbo']
        }

        for category, cmaps in categories.items():
            parent = QTreeWidgetItem(self.tree)
            parent.setText(0, f"🎨 {category} ({len(cmaps)})")
            parent.setExpanded(False)
            
            for cmap in cmaps:
                if cmap not in colormaps:
                    continue
                
                child = QTreeWidgetItem(parent)
                child.cmap_name = cmap
                child.setIcon(0, self.create_large_color_icon(cmap))
                child.setText(0, cmap)
                child.setToolTip(0, f"双击复制色卡名称: {cmap}")

        self.tree.itemDoubleClicked.connect(self.on_item_double_click)
        
        main_layout.addWidget(self.tree)
        
        self.setLayout(main_layout)
        # return widget

    def create_large_color_icon(self, cmap_name):
        """生成专业级色卡缩略图"""
        pixmap = QPixmap(320, 40)  # 宽度320px 高度40px
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)  # 启用抗锯齿
        
        # 创建带圆角的渐变区域
        rect = QRectF(2, 2, 316, 36)
        path = QPainterPath()
        path.addRoundedRect(rect, 4, 4)
        
        gradient = QLinearGradient(0, 0, 320, 0)
        cmap = colormaps[cmap_name]
        for i in np.linspace(0, 1, 256):
            color = cmap(i)
            gradient.setColorAt(i, QColor(*[int(c*255) for c in color]))
        
        painter.fillPath(path, gradient)
        
        # 添加1px边框
        painter.setPen(QColor(0,0,0,20))
        painter.drawPath(path)
        
        painter.end()
        return QIcon(pixmap)

    def on_item_double_click(self, item, column):
        """仅保留复制功能"""
        if hasattr(item, 'cmap_name'):
            clipboard = QApplication.clipboard()
            clipboard.setText(item.cmap_name) 

class Plugin:
    def run(self):
        return ColorPalettePlugin()