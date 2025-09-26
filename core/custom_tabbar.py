from PyQt5.QtWidgets import QTabBar
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QFont

class ChromeTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.hovered_index = -1
        self.close_button_size = 16  # 恢复标准尺寸
        self.font = QFont("MiSans Medium", 12, QFont.Medium)
        self.hover_font = QFont("MiSans Medium", 12, QFont.Bold)
        self.setTabsClosable(False)  # 禁用默认关闭按钮

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for index in range(self.count()):
            tab_rect = self.tabRect(index)
            close_rect = self.closeButtonRect(tab_rect)
            symbol_rect = QRect(
                close_rect.x() + 4,
                close_rect.y() + 3,
                8, 10
            )

            # 绘制悬停背景
            if index == self.hovered_index:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(0, 0, 0, 26))  # #1A000000
                painter.drawRoundedRect(close_rect, 4, 4)  # 圆角正方形

            # 绘制关闭按钮
            painter.setFont(self.hover_font if index == self.hovered_index else self.font)
            painter.setPen(QColor(102, 102, 102) if index == self.hovered_index else QColor(153, 153, 153))
            painter.drawText(close_rect, Qt.AlignCenter, "×")  # 居中显示符号

            # 设置样式类
            if not self.tabIcon(index).isNull():
                self.setProperty("hasIcon", True)

    def closeButtonRect(self, tab_rect):
        # Chrome标准布局参数
        RIGHT_MARGIN = 6  # 恢复6px边距
        BUTTON_SIZE = 16  # 实际点击区域16x16
        VERTICAL_OFFSET = (tab_rect.height() - BUTTON_SIZE) // 2
        
        return QRect(
            tab_rect.right() - RIGHT_MARGIN - BUTTON_SIZE,
            tab_rect.top() + VERTICAL_OFFSET,
            BUTTON_SIZE,
            BUTTON_SIZE
        )

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        last_hover = self.hovered_index
        self.hovered_index = -1

        for index in range(self.count()):
            if self.closeButtonRect(self.tabRect(index)).contains(event.pos()):
                self.hovered_index = index
                break

        if last_hover != self.hovered_index:
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            for index in range(self.count()):
                if self.closeButtonRect(self.tabRect(index)).contains(pos):
                    self.tabCloseRequested.emit(index)
                    return
        super().mousePressEvent(event) 