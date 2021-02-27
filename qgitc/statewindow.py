# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QMainWindow,
    QApplication)
from PySide6.QtCore import Qt


__all__ = ["StateWindow"]


class StateWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

    def saveState(self):
        sett = qApp.instance().settings()
        if not sett.rememberWindowState():
            return False

        state = super().saveState()
        geometry = self.saveGeometry()
        sett.setWindowState(
            self.__class__.__name__,
            state, geometry, self.isMaximized())

        return True

    def restoreState(self):
        sett = qApp.instance().settings()
        if not sett.rememberWindowState():
            return False

        state, geometry, isMaximized = sett.windowState(
            self.__class__.__name__)
        if state:
            super().restoreState(state)
        if geometry:
            self.restoreGeometry(geometry)

        if isMaximized:
            self.setWindowState(self.windowState() | Qt.WindowMaximized)

        return True

    def closeEvent(self, event):
        self.saveState()
        super().closeEvent(event)
