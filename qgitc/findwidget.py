# -*- coding: utf-8 -*-

from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtCore import *

from .stylehelper import dpiScaled
from .textcursor import TextCursor
from .waitingspinnerwidget import QtWaitingSpinner
from .textviewer import FindPart

import bisect


class FindWidget(QWidget):
    find = Signal(str)
    cursorChanged = Signal(TextCursor)
    afterHidden = Signal()

    def __init__(self, host, parent=None):
        super().__init__(parent)

        self._host = host
        self._findResult = []
        self._curIndex = 0
        self._searching = False

        self._setupUi()
        self._setupSignals()

        width = dpiScaled(300)
        heigth = self._leFind.height()
        self.resize(width, heigth)

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(dpiScaled(15))
        offset = dpiScaled(1)
        effect.setOffset(offset, offset)
        self.setGraphicsEffect(effect)

        self._host.installEventFilter(self)
        self.updateFindResult([], 0)

        self._delayTimer = QTimer(self)
        self._delayTimer.setSingleShot(True)
        self._delayTimer.timeout.connect(
            self._doFind)

    def _setupUi(self):
        self._leFind = QLineEdit(self)
        self._tbPrev = QToolButton(self)
        self._tbNext = QToolButton(self)
        self._tbClose = QToolButton(self)
        self._lbStatus = QLabel(self)
        self._spinner = QtWaitingSpinner(self)

        self._leFind.setFixedWidth(dpiScaled(100))

        height = self._leFind.height() // 6
        self._spinner.setLineLength(height)
        self._spinner.setInnerRadius(height)
        self._spinner.setNumberOfLines(14)

        hlayout = QHBoxLayout(self)
        margin = dpiScaled(3)
        hlayout.setContentsMargins(margin, margin, margin, margin)
        hlayout.setSpacing(margin)

        hlayout.addWidget(self._leFind)
        hlayout.addWidget(self._spinner)
        hlayout.addWidget(self._lbStatus)
        hlayout.addSpacing(dpiScaled(5))
        hlayout.addWidget(self._tbPrev)
        hlayout.addWidget(self._tbNext)
        hlayout.addWidget(self._tbClose)

        self._tbPrev.setText('🡩')
        self._tbNext.setText('🡫')
        self._tbClose.setText('⨉')

    def _setupSignals(self):
        self._leFind.textChanged.connect(self._onDelayFind)
        self._leFind.returnPressed.connect(self._onNextClicked)

        self._tbPrev.clicked.connect(self._onPreviousClicked)
        self._tbNext.clicked.connect(self._onNextClicked)
        self._tbClose.clicked.connect(self.hideAnimate)

    def _updateButtons(self, enable):
        self._tbNext.setEnabled(enable)
        self._tbPrev.setEnabled(enable)

    def _updatePos(self):
        pos = self._host.rect().topLeft()
        offset = self._host.width() - self.width()
        pos.setX(pos.x() + offset)
        pos.setY(pos.y() + dpiScaled(1))

        pos = self._host.mapToGlobal(pos)
        pos = self.parentWidget().mapFromGlobal(pos)

        self.move(pos)

    def _doFind(self):
        self.find.emit(self._leFind.text())

    def _onDelayFind(self, text):
        self._delayTimer.start(200)

    def _onPreviousClicked(self):
        if not self._findResult:
            return

        self._curIndex -= 1
        if self._curIndex < 0:
            self._curIndex = len(self._findResult) - 1

        self._updateStatus()
        self.cursorChanged.emit(self._findResult[self._curIndex])

    def _onNextClicked(self):
        if not self._findResult:
            return

        self._curIndex += 1
        if self._curIndex >= len(self._findResult):
            self._curIndex = 0

        self._updateStatus()
        self.cursorChanged.emit(self._findResult[self._curIndex])

    def _updateStatus(self):
        if self._findResult:
            color = Qt.black
            self._lbStatus.setText("{}/{}".format(
                self._curIndex + 1, len(self._findResult)))
        elif self._searching:
            color = Qt.black
            self._lbStatus.setText(self.tr("Finding..."))
        else:
            color = Qt.red
            self._lbStatus.setText(self.tr("No results"))

        palette = self._lbStatus.palette()
        palette.setColor(self._lbStatus.foregroundRole(), color)
        self._lbStatus.setPalette(palette)

    def showAnimate(self):
        # TODO: make it animate
        self._leFind.setFocus()
        self._leFind.selectAll()
        self.show()

    def hideAnimate(self):
        self.hide()

    def setText(self, text):
        self._leFind.setText(text)

    @property
    def text(self):
        return self._leFind.text()

    def updateFindResult(self, result, curIndex=0, part=FindPart.All):
        if part in [FindPart.CurrentPage, FindPart.All]:
            self._findResult = result[:]
            if curIndex >= 0:
                self._curIndex = curIndex
        elif part == FindPart.BeforeCurPage:
            if curIndex >= 0:
                self._curIndex = curIndex
            else:
                self._curIndex += len(result)
            low = bisect.bisect_left(self._findResult, result[0])
            for i in range(0, len(result)):
                self._findResult.insert(low + i, result[i])
        else:
            if curIndex >= 0:
                self._curIndex = curIndex + len(self._findResult)
            self._findResult.extend(result)

        self._updateButtons(len(self._findResult) > 0)
        self._updateStatus()

    def findStarted(self):
        self._searching = True
        self._spinner.start()

    def findFinished(self):
        self._searching = False
        self._spinner.stop()

    def showEvent(self, event):
        self._updatePos()
        self._leFind.setFocus()
        self._leFind.selectAll()

    def hideEvent(self, event):
        # FIXME: control by caller?
        self.blockSignals(True)
        self._leFind.setText("")
        self.updateFindResult([])
        self.blockSignals(False)
        self.afterHidden.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        onePixel = dpiScaled(1)
        rc = self.rect().adjusted(0, 0, -onePixel, -onePixel)
        painter.fillRect(rc, Qt.white)
        painter.setPen(Qt.gray)
        painter.drawRect(rc)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self._updatePos()

        return super().eventFilter(obj, event)
