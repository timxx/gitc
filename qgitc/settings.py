# -*- coding: utf-8 -*-

from PySide6.QtCore import (
    QSettings,
    Signal
)
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from .mergetool import MergeTool

import os


is_win = (os.name == "nt")


def fixedFont(pointSize):
    """return a fixed font if available"""
    font = QFont("monospace", pointSize)

    font.setStyleHint(QFont.TypeWriter)
    fontInfo = QFontInfo(font)
    if fontInfo.fixedPitch():
        return QFont(fontInfo.family(), pointSize)

    font.setStyleHint(QFont.Monospace)
    fontInfo = QFontInfo(font)
    if fontInfo.fixedPitch():
        return QFont(fontInfo.family(), pointSize)

    # for Windows
    font.setFamily("Courier")
    return font


class Settings(QSettings):

    showWhitespaceChanged = Signal(bool)
    ignoreWhitespaceChanged = Signal(int)
    logViewFontChanged = Signal(QFont)
    diffViewFontChanged = Signal(QFont)
    bugPatternChanged = Signal(str)
    fallbackGlobalChanged = Signal(bool)
    tabSizeChanged = Signal(int)

    def __init__(self, parent=None):
        super(Settings, self).__init__(
            QSettings.NativeFormat,
            QSettings.UserScope,
            "qgitc",
            parent=parent)

        self._fixedFont = fixedFont(QApplication.font().pointSize())

    def logViewFont(self):
        return self.value("lvFont", QApplication.font())

    def setLogViewFont(self, font):
        self.setValue("lvFont", font)
        self.logViewFontChanged.emit(font)

    def diffViewFont(self):
        font = self.value("dvFont", self._fixedFont)
        return font

    def setDiffViewFont(self, font):
        self.setValue("dvFont", font)
        self.diffViewFontChanged.emit(font)

    def commitColorA(self):
        return self.value("colorA", QColor(255, 0, 0))

    def setCommitColorA(self, color):
        self.setValue("colorA", color)

    def commitColorB(self):
        return self.value("colorB", QColor(112, 48, 160))

    def setCommitColorB(self, color):
        self.setValue("colorB", color)

    def _linkGroup(self, repoName):
        return repoName if repoName else "Global"

    def getLinkValue(self, repoName, key, default=None, type=None):
        self.beginGroup(self._linkGroup(repoName))
        if type is not None:  # BUG!!!
            value = self.value(key, default, type=type)
        else:
            value = self.value(key, default)
        self.endGroup()
        return value

    def setLinkValue(self, repoName, key, value):
        self.beginGroup(self._linkGroup(repoName))
        self.setValue(key, value)
        self.endGroup()

    def commitUrl(self, repoName):
        return self.getLinkValue(repoName, "commitUrl", "")

    def setCommitUrl(self, repoName, url):
        self.setLinkValue(repoName, "commitUrl", url)

    def bugUrl(self, repoName):
        return self.getLinkValue(repoName, "bugUrl", "")

    def setBugUrl(self, repoName, url):
        self.setLinkValue(repoName, "bugUrl", url)

    def bugPattern(self, repoName):
        return self.getLinkValue(repoName, "bugPattern", "")

    def setBugPattern(self, repoName, pattern):
        self.setLinkValue(repoName, "bugPattern", pattern)
        self.bugPatternChanged.emit(pattern)

    def fallbackGlobalLinks(self, repoName):
        return self.getLinkValue(repoName, "fallback", True, type=bool)

    def setFallbackGlobalLinks(self, repoName, fallback):
        self.setLinkValue(repoName, "fallback", fallback)
        self.fallbackGlobalChanged.emit(fallback)

    def showWhitespace(self):
        return self.value("showWhitespace", True, type=bool)

    def setShowWhitespace(self, show):
        self.setValue("showWhitespace", show)
        self.showWhitespaceChanged.emit(show)

    def tabSize(self):
        return self.value("tabSize", 4, type=int)

    def setTabSize(self, size):
        self.setValue("tabSize", size)
        self.tabSizeChanged.emit(size)

    def quitViaEsc(self):
        return self.value("quitViaEsc", False, type=bool)

    def setQuitViaEsc(self, via):
        self.setValue("quitViaEsc", via)

    def rememberWindowState(self):
        return self.value("rememberWindowState", True, type=bool)

    def setRememberWindowState(self, remember):
        self.setValue("rememberWindowState", remember)

    def windowState(self, windowName):
        self.beginGroup(windowName)
        state = self.value("state", None)
        geometry = self.value("geometry", None)
        isMaximized = self.value("maximized", True, type=bool)
        self.endGroup()

        return state, geometry, isMaximized

    def setWindowState(self, windowName, state, geometry, isMaximized):
        self.beginGroup(windowName)
        self.setValue("state", state)
        # FIXME: make a common version
        if not isMaximized or is_win:
            self.setValue("geometry", geometry)
        self.setValue("maximized", isMaximized)
        self.endGroup()

    def gitViewState(self, isBranchA):
        key = "gvStateA" if isBranchA else "gvStateB"
        return self.value(key, None)

    def setGitViewState(self, state, isBranchA):
        key = "gvStateA" if isBranchA else "gvStateB"
        self.setValue(key, state)

    def diffViewState(self, isBranchA):
        key = "dvStateA" if isBranchA else "dvStateB"
        return self.value(key, None)

    def setDiffViewState(self, state, isBranchA):
        key = "dvStateA" if isBranchA else "dvStateB"
        self.setValue(key, state)

    def ignoreWhitespace(self):
        return self.value("ignoreWhitespace", 0, type=int)

    def setIgnoreWhitespace(self, index):
        self.setValue("ignoreWhitespace", index)
        self.ignoreWhitespaceChanged.emit(index)

    def mergeToolList(self):
        tools = [MergeTool(MergeTool.Nothing, ".png", "imgdiff"),
                 MergeTool(MergeTool.Nothing, ".jpg", "imgdiff")]
        return self.value("mergeTool", tools)

    def setMergeToolList(self, tools):
        self.setValue("mergeTool", tools)

    def ignoredVersion(self):
        return self.value("ignoredVersion", "")

    def setIgnoredVersion(self, version):
        self.setValue("ignoredVersion", version)

    def lastCheck(self):
        return self.value("lastCheck", 0, type=int)

    def setLastCheck(self, datetime):
        self.setValue("lastCheck", datetime)

    def checkUpdatesEnabled(self):
        return self.value("checkUpdates", True, type=bool)

    def setCheckUpdatesEnabled(self, enabled):
        self.setValue("checkUpdates", enabled)

    def checkUpdatesInterval(self):
        return self.value("checkInterval", 1, type=int)

    def setCheckUpdatesInterval(self, days):
        self.setValue("checkInterval", days)

    def diffToolName(self):
        return self.value("diffToolName", "")

    def setDiffToolName(self, name):
        self.setValue("diffToolName", name)

    def mergeToolName(self):
        return self.value("mergeToolName", "")

    def setMergeToolName(self, name):
        self.setValue("mergeToolName", name)
