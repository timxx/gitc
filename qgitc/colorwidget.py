# -*- coding: utf-8 -*-

from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from .stylehelper import dpiScaled


class ColorWidget(QPushButton):

    def __init__(self, parent=None):
        super(ColorWidget, self).__init__(parent)
        self.color = QColor(Qt.black)

        self.clicked.connect(self._onClicked)

    def setColor(self, color):
        self.color = color
        self.update()

    def getColor(self):
        return self.color

    def paintEvent(self, event):
        super(ColorWidget, self).paintEvent(event)

        painter = QPainter(self)
        offset = dpiScaled(5)
        rc = self.rect().adjusted(offset, offset, -offset, -offset)
        painter.fillRect(rc, self.color)
        painter.drawRect(rc)

    def _onClicked(self, checked):
        colorDlg = QColorDialog(self.color, self)
        if colorDlg.exec_() != QDialog.Accepted:
            return

        self.color = colorDlg.currentColor()
        self.update()
