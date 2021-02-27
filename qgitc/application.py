# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import (
    Qt,
    QTranslator,
    QLibraryInfo,
    QLocale,
    QUrl,
    QTimer)

from .common import dataDirPath
from .settings import Settings
from .events import (
    BlameEvent,
    ShowCommitEvent,
    OpenLinkEvent)
from .blamewindow import BlameWindow
from .mainwindow import MainWindow
from .gitutils import Git
from .textline import Link
from .versionchecker import VersionChecker
from .newversiondialog import NewVersionDialog

from datetime import datetime

import os
import re


class Application(QApplication):

    LogWindow = 1
    BlameWindow = 2

    def __init__(self, argv):
        super(Application, self).__init__(argv)

        self.setAttribute(Qt.AA_DontShowIconsInMenus, False)
        self.setAttribute(Qt.AA_DontUseNativeMenuBar, True)
        self.setApplicationName("qgitc")

        iconPath = dataDirPath() + "/icons/qgitc.svg"
        self.setWindowIcon(QIcon(iconPath))

        self.setupTranslator()
        self._settings = Settings(self)

        self._logWindow = None
        self._blameWindow = None

        cwd = os.getcwd()
        repoDir = Git.repoTopLevelDir(cwd)
        Git.REPO_DIR = repoDir or cwd

        QTimer.singleShot(0, self._onDelayInit)

    def settings(self):
        return self._settings

    def setupTranslator(self):
        # the Qt translations
        dirPath = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
        translator = QTranslator(self)
        if translator.load(QLocale.system(), "qt", "_", dirPath):
            self.installTranslator(translator)
        else:
            translator = None

        translator = QTranslator(self)
        dirPath = dataDirPath() + "/translations"
        if translator.load(QLocale.system(), "", "", dirPath):
            self.installTranslator(translator)
        else:
            translator = None

    def getWindow(self, type):
        window = None
        if type == Application.LogWindow:
            if not self._logWindow:
                self._logWindow = MainWindow()
                self._logWindow.destroyed.connect(
                    self._onLogWindowDestroyed)
            window = self._logWindow
        elif type == Application.BlameWindow:
            if not self._blameWindow:
                self._blameWindow = BlameWindow()
                self._blameWindow.destroyed.connect(
                    self._onBlameWindowDestroyed)
            window = self._blameWindow

        return window

    def repoName(self):
        url = Git.repoUrl()
        index = url.rfind('/')
        if index == -1:
            return url
        return url[index+1:]

    def event(self, event):
        type = event.type()
        if type == BlameEvent.Type:
            window = self.getWindow(Application.BlameWindow)
            window.blame(event.filePath, event.rev, event.lineNo)
            self._ensureVisible(window)
            return True
        elif type == ShowCommitEvent.Type:
            window = self.getWindow(Application.LogWindow)
            window.showCommit(event.sha1)
            self._ensureVisible(window)
            return True
        elif type == OpenLinkEvent.Type:
            url = None
            link = event.link
            if link.type == Link.Email:
                url = "mailto:" + link.data
            elif link.type == Link.BugId:
                # FIXME: bind the url with pattern?
                repoName = self.repoName()
                sett = self.settings()
                bugPattern = sett.bugPattern(repoName)
                fallback = True

                def _linkData(bugRe, m):
                    if bugRe.groups == 1:
                        return m.group(1)
                    return m.group(2)

                if bugPattern:
                    bugRe = re.compile(bugPattern)
                    m = bugRe.search(link.data)
                    if m:
                        fallback = False
                        bugUrl = sett.bugUrl(repoName)
                        if not bugUrl and sett.fallbackGlobalLinks(repoName):
                            bugUrl = sett.bugUrl(None)
                        if bugUrl:
                            url = bugUrl + _linkData(bugRe, m)

                if fallback and sett.fallbackGlobalLinks(repoName):
                    bugPattern = sett.bugPattern(None)
                    bugUrl = sett.bugUrl(None)
                    if not bugPattern or not bugUrl:
                        return True

                    bugRe = re.compile(bugPattern)
                    m = bugRe.search(link.data)
                    if m:
                        url = bugUrl + _linkData(bugRe, m)
            else:
                url = link.data

            if url:
                QDesktopServices.openUrl(QUrl(url))
            return True

        return super().event(event)

    def _onLogWindowDestroyed(self, obj):
        self._logWindow = None

    def _onBlameWindowDestroyed(self, obj):
        self._blameWindow = None

    def _onNewVersionAvailable(self, version):
        ignoredVersion = self.settings().ignoredVersion()
        if ignoredVersion == version:
            return

        parent = self.activeWindow()
        versionDlg = NewVersionDialog(version, parent)
        versionDlg.exec_()

    def _onVersionCheckFinished(self):
        self._checker = None
        self._settings.setLastCheck(int(datetime.now().timestamp()))

    def _onDelayInit(self):
        checkUpdates = self._settings.checkUpdatesEnabled()
        if checkUpdates:
            ts = self._settings.lastCheck()
            if ts < 86440:
                haveToCheck = True
            else:
                days = self._settings.checkUpdatesInterval()
                dt = datetime.fromtimestamp(ts)
                diff = datetime.now() - dt
                haveToCheck = diff.days >= days

            if haveToCheck:
                self._checker = VersionChecker(self)
                self._checker.newVersionAvailable.connect(
                    self._onNewVersionAvailable)
                self._checker.finished.connect(
                    self._onVersionCheckFinished)
                QTimer.singleShot(0, self._checker.startCheck)

    def _ensureVisible(self, window):
        if window.isVisible():
            if window.isMinimized():
                window.setWindowState(
                    window.windowState() & ~Qt.WindowMinimized)
            window.activateWindow()
            return
        if window.restoreState():
            window.show()
        else:
            window.showMaximized()
