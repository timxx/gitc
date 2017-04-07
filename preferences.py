# -*- coding: utf-8 -*-

from PyQt4.QtGui import *
from ui.preferences import *


class Preferences(QDialog):

    def __init__(self, settings, parent=None):
        super(Preferences, self).__init__(parent)

        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.settings = settings

        self.ui.cbFamilyLog.currentFontChanged.connect(
            self.__onFamilyChanged)
        self.ui.cbFamilyDiff.currentFontChanged.connect(
            self.__onFamilyChanged)

        self.__initSettings()

    def __initSettings(self):
        font = self.settings.logViewFont()
        self.ui.cbFamilyLog.setCurrentFont(font)
        self.ui.cbFamilyLog.currentFontChanged.emit(font)

        font = self.settings.diffViewFont()
        self.ui.cbFamilyDiff.setCurrentFont(font)
        self.ui.cbFamilyDiff.currentFontChanged.emit(font)

        self.ui.colorA.setColor(self.settings.commitColorA())
        self.ui.colorB.setColor(self.settings.commitColorB())

        self.ui.leCommitUrl.setText(self.settings.commitUrl())
        self.ui.leBugUrl.setText(self.settings.bugUrl())
        self.ui.leBugPattern.setText(self.settings.bugPattern())

        self.ui.cbShowWhitespace.setChecked(self.settings.showWhitespace())
        self.ui.sbTabSize.setValue(self.settings.tabSize())

        self.ui.cbEsc.setChecked(self.settings.quitViaEsc())
        self.ui.cbState.setChecked(self.settings.rememberWindowState())

        index = self.settings.ignoreWhitespace()
        if index < 0 or index >= self.ui.cbIgnoreWhitespace.count():
            index = 0
        self.ui.cbIgnoreWhitespace.setCurrentIndex(index)

    def __updateFontSizes(self, family, size, cb):
        fdb = QFontDatabase()
        sizes = fdb.pointSizes(family)
        if not sizes:
            sizes = QFontDatabase.standardSizes()

        sizes.sort()
        cb.clear()
        cb.blockSignals(True)

        curIdx = -1
        for i in range(len(sizes)):
            s = sizes[i]
            cb.addItem(str(s))
            # find the best one for @size
            if curIdx == -1 and s >= size:
                if i > 0 and (size - sizes[i - 1] < s - size):
                    curIdx = i - 1
                else:
                    curIdx = i

        cb.blockSignals(False)
        cb.setCurrentIndex(0 if curIdx == -1 else curIdx)

    def __onFamilyChanged(self, font):
        cbSize = self.ui.cbSizeLog
        size = self.settings.logViewFont().pointSize()
        if self.sender() == self.ui.cbFamilyDiff:
            cbSize = self.ui.cbSizeDiff
            size = self.settings.diffViewFont().pointSize()

        self.__updateFontSizes(font.family(), size, cbSize)

    def save(self):
        font = QFont(self.ui.cbFamilyLog.currentText(),
                     int(self.ui.cbSizeLog.currentText()))

        self.settings.setLogViewFont(font)

        font = QFont(self.ui.cbFamilyDiff.currentText(),
                     int(self.ui.cbSizeDiff.currentText()))

        self.settings.setDiffViewFont(font)

        color = self.ui.colorA.getColor()
        self.settings.setCommitColorA(color)

        color = self.ui.colorB.getColor()
        self.settings.setCommitColorB(color)

        value = self.ui.leCommitUrl.text().strip()
        self.settings.setCommitUrl(value)

        value = self.ui.leBugUrl.text().strip()
        self.settings.setBugUrl(value)

        value = self.ui.leBugPattern.text().strip()
        self.settings.setBugPattern(value)

        value = self.ui.cbShowWhitespace.isChecked()
        self.settings.setShowWhitespace(value)

        value = self.ui.sbTabSize.value()
        self.settings.setTabSize(value)

        value = self.ui.cbEsc.isChecked()
        self.settings.setQuitViaEsc(value)

        value = self.ui.cbState.isChecked()
        self.settings.setRememberWindowState(value)

        value = self.ui.cbIgnoreWhitespace.currentIndex()
        self.settings.setIgnoreWhitespace(value)
