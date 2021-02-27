# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QDialog)

from PySide6.QtGui import (
    QKeySequence,
    QIcon)
from PySide6.QtCore import (
    Qt)

from .blameview import BlameView
from .stylehelper import dpiScaled
from .gotodialog import GotoDialog
from .findwidget import FindWidget
from .statewindow import StateWindow
from .textviewer import FindPart


__all__ = ["BlameWindow"]


class BlameWindow(StateWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("QGitc Blame"))

        centralWidget = QWidget(self)
        layout = QVBoxLayout(centralWidget)
        margin = dpiScaled(5)
        layout.setContentsMargins(margin, margin, margin, margin)

        self._view = BlameView(self)
        layout.addWidget(self._view)

        self.setCentralWidget(centralWidget)
        self._setupMenuBar()

        self._findWidget = None
        self._curIndexFound = False

        self._view.blameFileAboutToChange.connect(
            self._onBlameFileAboutToChange)
        self._view.blameFileChanged.connect(
            self._onBlameFileChanged)

        self._view.viewer.findResultAvailable.connect(
            self._onFindResultAvailable)

    def _setupMenuBar(self):
        self._setupFileMenu()
        self._setupEditMenu()

    def _setupFileMenu(self):
        fileMenu = self.menuBar().addMenu(self.tr("&File"))
        acClose = fileMenu.addAction(self.tr("Close &Window"),
                           self.close,
                           QKeySequence("Ctrl+W"))
        acClose.setIcon(QIcon.fromTheme("window-close"))

    def _setupEditMenu(self):
        editMenu = self.menuBar().addMenu(self.tr("&Edit"))
        ac = editMenu.addAction(self.tr("&Go To Line..."),
                                self._onGotoLine,
                                QKeySequence("Ctrl+G"))
        ac.setIcon(QIcon.fromTheme("go-jump"))
        ac = editMenu.addAction(self.tr("&Find"),
                                self.showFindWidget,
                                QKeySequence("Ctrl+F"))
        ac.setIcon(QIcon.fromTheme("edit-find"))
        editMenu.addSeparator()
        ac = editMenu.addAction(self.tr("&Copy"),
                                self._onCopy,
                                QKeySequence("Ctrl+C"))
        ac.setIcon(QIcon.fromTheme("edit-copy"))
        editMenu.addSeparator()
        ac = editMenu.addAction(self.tr("Select &All"),
                                self._onSelectAll,
                                QKeySequence("Ctrl+A"))
        ac.setIcon(QIcon.fromTheme("edit-select-all"))

    def _onGotoLine(self):
        gotoDialog = GotoDialog(self)
        viewer = self._view.viewer
        gotoDialog.setRange(1,
                            viewer.textLineCount(),
                            viewer.currentLineNo + 1)
        ret = gotoDialog.exec_()
        if ret != QDialog.Accepted:
            return

        viewer.gotoLine(gotoDialog.lineNo - 1)

    def _onCopy(self):
        if qApp.focusWidget() == self._view.commitPanel:
            self._view.commitPanel.copy()
        else:
            self._view.viewer.copy()

    def _onSelectAll(self):
        if qApp.focusWidget() == self._view.commitPanel:
            self._view.commitPanel.selectAll()
        else:
            self._view.viewer.selectAll()

    def _onFindFind(self, text):
        viewer = self._view.viewer

        self._findWidget.updateFindResult([])
        viewer.highlightFindResult([])

        if viewer.textLineCount() > 3000:
            self._curIndexFound = False
            if viewer.findAllAsync(text):
                self._findWidget.findStarted()
        else:
            findResult = viewer.findAll(text)
            if findResult:
                self._onFindResultAvailable(findResult, FindPart.All)

    def _onFindCursorChanged(self, cursor):
        self._view.viewer.select(cursor)

    def _onFindHidden(self):
        self._view.viewer.highlightFindResult([])
        self._view.viewer.cancelFind()

    def _onBlameFileAboutToChange(self, file):
        if self._findWidget and self._findWidget.isVisible():
            self._findWidget.updateFindResult([])

    def _onBlameFileChanged(self, file):
        if self._findWidget and self._findWidget.isVisible():
            # redo a find
            self._onFindFind(self._findWidget.text)

    def _onFindResultAvailable(self, result, findPart):
        curFindIndex = 0 if findPart == FindPart.All else -1
        viewer = self._view.viewer

        if findPart in [FindPart.CurrentPage, FindPart.All]:
            textCursor = viewer.textCursor
            if textCursor.isValid() and textCursor.hasSelection() \
                    and not textCursor.hasMultiLines():
                for i in range(0, len(result)):
                    r = result[i]
                    if r == textCursor:
                        curFindIndex = i
                        break
            else:
                curFindIndex = 0
        elif not self._curIndexFound:
            curFindIndex = 0

        if curFindIndex >= 0:
            self._curIndexFound = True

        viewer.highlightFindResult(result, findPart)
        if curFindIndex >= 0:
            viewer.select(result[curFindIndex])

        self._findWidget.updateFindResult(result, curFindIndex, findPart)

    def showFindWidget(self):
        if not self._findWidget:
            self._findWidget = FindWidget(
                self._view.viewer.viewport(), self)
            self._findWidget.find.connect(
                self._onFindFind)
            self._findWidget.cursorChanged.connect(
                self._onFindCursorChanged)
            self._findWidget.afterHidden.connect(
                self._onFindHidden)
            self._view.viewer.findFinished.connect(
                self._findWidget.findFinished)

        text = self._view.viewer.selectedText
        if text:
            text = text.lstrip('\n')
            index = text.find('\n')
            if index != -1:
                text = text[:index]
            self._findWidget.setText(text)

        self._findWidget.showAnimate()

    def blame(self, file, rev=None, lineNo=0):
        self._view.blame(file, rev, lineNo)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self._findWidget and self._findWidget.isVisible():
                self._findWidget.hideAnimate()
            else:
                sett = qApp.instance().settings()
                if sett.quitViaEsc():
                    self.close()
                    return

        super().keyPressEvent(event)
