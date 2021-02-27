# -*- coding: utf-8 -*-
from PySide6.QtGui import *
from PySide6.QtCore import *

from PySide6.QtWidgets import (
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QDialog)

from .ui_mainwindow import Ui_MainWindow
from .gitview import GitView
from .preferences import Preferences
from .gitutils import Git, GitProcess
from .diffview import PatchViewer
from .aboutdialog import AboutDialog
from .mergewidget import MergeWidget
from .stylehelper import dpiScaled
from .statewindow import StateWindow

import os
import sys
import shlex


class FindSubmoduleThread(QThread):
    def __init__(self, repoDir, parent=None):
        super(FindSubmoduleThread, self).__init__(parent)

        self._repoDir = os.path.normcase(os.path.normpath(repoDir))
        self._submodules = []

    @property
    def submodules(self):
        if self.isFinished() and not self.isInterruptionRequested():
            return self._submodules
        return []

    def run(self):
        self._submodules.clear()
        if self.isInterruptionRequested():
            return

        # try git submodule first
        process = GitProcess(self._repoDir,
                             ["submodule", "foreach", "--quiet", "echo $name"],
                             True)
        data = process.communicate()[0]
        if self.isInterruptionRequested():
            return
        if process.returncode == 0 and data:
            self._submodules = data.rstrip().split('\n')
            self._submodules.insert(0, ".")
            return

        submodules = []
        # some projects may not use submodule or subtree
        max_level = 5 + self._repoDir.count(os.path.sep)
        for root, subdirs, files in os.walk(self._repoDir, topdown=True):
            if self.isInterruptionRequested():
                return
            if os.path.normcase(root) == self._repoDir:
                continue

            if ".git" in subdirs or ".git" in files:
                dir = root.replace(self._repoDir + os.sep, "")
                if dir:
                    submodules.append(dir)
                del subdirs[:]

            if root.count(os.path.sep) >= max_level or root.endswith(".git"):
                del subdirs[:]
            else:
                # ignore all '.dir'
                subdirs[:] = [d for d in subdirs if not d.startswith(".")]

        if submodules:
            submodules.insert(0, '.')

        self._submodules = submodules


class MainWindow(StateWindow):
    LogMode = 1
    CompareMode = 2
    MergeMode = 3

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.resize(dpiScaled(QSize(800, 600)))

        self.gitViewB = None

        self.isWindowReady = False
        self.findSubmoduleThread = None

        self.mergeWidget = None

        self._delayTimer = QTimer(self)
        self._delayTimer.setSingleShot(True)

        self.ui.cbSubmodule.setVisible(False)
        self.ui.lbSubmodule.setVisible(False)

        self.__setupSignals()
        self.__setupMenus()

    def __setupSignals(self):
        self.ui.acQuit.triggered.connect(self.close)

        self.ui.acPreferences.triggered.connect(
            self.__onAcPreferencesTriggered)

        self.ui.btnRepoBrowse.clicked.connect(self.__onBtnRepoBrowseClicked)

        self.ui.leRepo.textChanged.connect(self.__onDelayRepoChanged)

        self.ui.acIgnoreNone.triggered.connect(
            self.__onAcIgnoreNoneTriggered)
        self.ui.acIgnoreEOL.triggered.connect(
            self.__onAcIgnoreEOLTriggered)
        self.ui.acIgnoreAll.triggered.connect(
            self.__onAcIgnoreAllTriggered)

        self.ui.acCompare.triggered.connect(
            self.__onAcCompareTriggered)

        self.ui.acCopy.triggered.connect(
            self.__onCopyTriggered)

        self.ui.acSelectAll.triggered.connect(
            self.__onSelectAllTriggered)

        self.ui.acFind.triggered.connect(
            self.__onFindTriggered)

        self.ui.menu_Edit.aboutToShow.connect(
            self.__updateEditMenu)

        self.ui.acVisualizeWhitespace.triggered.connect(
            self.__onAcVisualizeWhitespaceTriggered)

        self.ui.leOpts.returnPressed.connect(
            self.__onOptsReturnPressed)

        self.ui.acAbout.triggered.connect(
            self.__onAboutTriggered)

        self.ui.acAboutQt.triggered.connect(
            qApp.aboutQt)

        # settings
        sett = qApp.instance().settings()

        sett.ignoreWhitespaceChanged.connect(
            self.__onIgnoreWhitespaceChanged)

        sett.showWhitespaceChanged.connect(
            self.ui.acVisualizeWhitespace.setChecked)

        # application
        qApp.focusChanged.connect(self.__updateEditMenu)

        self.ui.cbSubmodule.currentIndexChanged.connect(self.__onSubmoduleChanged)

        self._delayTimer.timeout.connect(
            self.__onDelayTimeout)

    def __setupMenus(self):
        acGroup = QActionGroup(self)
        acGroup.addAction(self.ui.acIgnoreNone)
        acGroup.addAction(self.ui.acIgnoreEOL)
        acGroup.addAction(self.ui.acIgnoreAll)

    def __updateEditMenu(self):
        fw = qApp.focusWidget()

        self.ui.acCopy.setEnabled(False)
        self.ui.acSelectAll.setEnabled(False)
        self.ui.acFind.setEnabled(False)

        if not fw:
            pass
        elif isinstance(fw, PatchViewer):
            self.ui.acCopy.setEnabled(fw.hasSelection())
            self.ui.acSelectAll.setEnabled(True)
            self.ui.acFind.setEnabled(True)
        elif isinstance(fw, QLineEdit):
            self.ui.acCopy.setEnabled(fw.hasSelectedText())
            self.ui.acSelectAll.setEnabled(True)
            self.ui.acFind.setEnabled(False)

    def __onBtnRepoBrowseClicked(self, checked):
        repoDir = QFileDialog.getExistingDirectory(self,
                                                   self.tr(
                                                       "Choose repository directory"),
                                                   "",
                                                   QFileDialog.ShowDirsOnly)
        if not repoDir:
            return

        repoDir = Git.repoTopLevelDir(repoDir)
        if not repoDir:
            QMessageBox.critical(self, self.windowTitle(),
                                 self.tr("The directory you choosen is not a git repository!"))
            return

        self.ui.leRepo.setText(repoDir)

    def __onRepoChanged(self, repoDir):
        self.ui.cbSubmodule.clear()
        self.ui.cbSubmodule.setVisible(False)
        self.ui.lbSubmodule.setVisible(False)

        if not Git.repoTopLevelDir(repoDir):
            msg = self.tr("'{0}' is not a git repository")
            self.ui.statusbar.showMessage(
                msg.format(repoDir),
                5000)  # 5 seconds
            # let gitview clear the old branches
            repoDir = None
            # clear
            Git.REPO_DIR = None
            Git.REPO_TOP_DIR = None
            if Git.REF_MAP:
                Git.REF_MAP.clear()
            Git.REV_HEAD = None
        else:
            Git.REPO_DIR = repoDir
            Git.REPO_TOP_DIR = repoDir
            Git.REF_MAP = Git.refs()
            Git.REV_HEAD = Git.revHead()

        if self.findSubmoduleThread and self.findSubmoduleThread.isRunning():
            self.findSubmoduleThread.disconnect(self)
            self.findSubmoduleThread.requestInterruption()
            self.findSubmoduleThread.wait()

        if repoDir:
            self.ui.leRepo.setReadOnly(True)
            self.ui.btnRepoBrowse.setDisabled(True)
            self.findSubmoduleThread = FindSubmoduleThread(repoDir, self)
            self.findSubmoduleThread.finished.connect(
                self.__onFindSubmoduleFinished)
            self.findSubmoduleThread.start()

        branch = Git.mergeBranchName() if self.mergeWidget else None
        if branch and branch.startswith("origin/"):
            branch = "remotes/" + branch
        self.ui.gitViewA.reloadBranches()
        if self.gitViewB:
            self.gitViewB.reloadBranches(branch)

    def __onAcPreferencesTriggered(self):
        settings = qApp.instance().settings()
        preferences = Preferences(settings, self)
        if preferences.exec_() == QDialog.Accepted:
            preferences.save()

    def __onIgnoreWhitespaceChanged(self, index):
        actions = [self.ui.acIgnoreNone,
                   self.ui.acIgnoreEOL,
                   self.ui.acIgnoreAll]
        if index < 0 or index >= len(actions):
            index = 0

        actions[index].setChecked(True)

    def __onAcIgnoreNoneTriggered(self, checked):
        sett = qApp.instance().settings()
        sett.setIgnoreWhitespace(0)

    def __onAcIgnoreEOLTriggered(self, checked):
        sett = qApp.instance().settings()
        sett.setIgnoreWhitespace(1)

    def __onAcIgnoreAllTriggered(self, checked):
        sett = qApp.instance().settings()
        sett.setIgnoreWhitespace(2)

    def __onAcVisualizeWhitespaceTriggered(self, checked):
        sett = qApp.instance().settings()
        sett.setShowWhitespace(checked)

    def __onAcCompareTriggered(self, checked):
        if checked:
            self.setMode(MainWindow.CompareMode)
        else:
            self.setMode(MainWindow.LogMode)

    def __onOptsReturnPressed(self):
        opts = self.ui.leOpts.text().strip()
        self.filterOpts(opts, self.ui.gitViewA)
        self.filterOpts(opts, self.gitViewB)

    def __onCopyTriggered(self):
        fw = qApp.focusWidget()
        assert fw
        fw.copy()

    def __onSelectAllTriggered(self):
        fw = qApp.focusWidget()
        assert fw
        fw.selectAll()

    def __onFindTriggered(self):
        fw = qApp.focusWidget()
        assert fw and isinstance(fw, PatchViewer)
        fw.executeFind()

    def __onAboutTriggered(self):
        aboutDlg = AboutDialog(self)
        aboutDlg.exec_()

    def __onRequestResolve(self, filePath):
        self.setFilterFile(filePath)

    def __onSubmoduleChanged(self, index):
        newRepo = Git.REPO_TOP_DIR
        if index > 0:
            newRepo = os.path.join(Git.REPO_TOP_DIR, self.ui.cbSubmodule.currentText())
        if os.path.normcase(os.path.normpath(newRepo)) == os.path.normcase(os.path.normpath(Git.REPO_DIR)):
            return

        Git.REPO_DIR = newRepo
        self.ui.gitViewA.reloadBranches(
            self.ui.gitViewA.currentBranch())
        if self.gitViewB:
            self.gitViewB.reloadBranches(
                self.gitViewB.currentBranch())

    def __onFindSubmoduleFinished(self):
        submodules = self.findSubmoduleThread.submodules
        for submodule in submodules:
            self.ui.cbSubmodule.addItem(submodule)
        if not self.mergeWidget:
            self.ui.leRepo.setReadOnly(False)
            self.ui.btnRepoBrowse.setEnabled(True)
        hasSubmodule = len(submodules) > 0
        self.ui.cbSubmodule.setVisible(hasSubmodule)
        self.ui.lbSubmodule.setVisible(hasSubmodule)

    def __onDelayTimeout(self):
        repoDir = self.ui.leRepo.text()
        self.__onRepoChanged(repoDir)

    def __onDelayRepoChanged(self, text):
        self._delayTimer.start(500)

    def saveState(self):
        sett = qApp.instance().settings()
        if not sett.rememberWindowState():
            return False

        super().saveState()

        self.ui.gitViewA.saveState(sett, True)
        if self.gitViewB:
            self.gitViewB.saveState(sett, False)

        return True

    def restoreState(self):
        sett = qApp.instance().settings()
        if not sett.rememberWindowState():
            return False

        super().restoreState()

        self.ui.gitViewA.restoreState(sett, True)
        if self.gitViewB:
            self.gitViewB.restoreState(sett, False)

        self.__onIgnoreWhitespaceChanged(sett.ignoreWhitespace())
        self.ui.acVisualizeWhitespace.setChecked(
            sett.showWhitespace())

        return True

    def filterOpts(self, opts, gitView):
        if not gitView:
            return

        # don't knonw if cygwin works or not
        args = shlex.split(opts, posix=sys.platform != "win32")
        gitView.filterLog(args)

    def showMessage(self, msg, timeout=5000):
        self.ui.statusbar.showMessage(msg, timeout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            sett = qApp.instance().settings()
            if sett.quitViaEsc():
                self.close()
                return

        super(MainWindow, self).keyPressEvent(event)

    def showEvent(self, event):
        super(MainWindow, self).showEvent(event)
        if not self.isWindowReady:
            self.isWindowReady = True
            if Git.REPO_DIR:
                self.ui.leRepo.setText(Git.REPO_DIR)

    def closeEvent(self, event):
        super().closeEvent(event)
        if self.mergeWidget:
            self.mergeWidget.close()

    def setFilterFile(self, filePath):
        if filePath and not filePath.startswith("-- "):
            self.ui.leOpts.setText("-- " + filePath)
        else:
            self.ui.leOpts.setText(filePath)
        self.__onOptsReturnPressed()

    def setMode(self, mode):
        if mode == MainWindow.LogMode:
            self.ui.gitViewA.setBranchDesc(self.tr("Branch"))

            if self.gitViewB:
                self.gitViewB.deleteLater()
                self.gitViewB = None

            self.ui.acCompare.setChecked(False)
        elif mode == MainWindow.CompareMode:
            self.gitViewB = GitView(self)
            self.ui.splitter.addWidget(self.gitViewB)

            self.ui.gitViewA.setBranchDesc(self.tr("Branch A:"))
            self.gitViewB.setBranchDesc(self.tr("Branch B:"))
            self.gitViewB.setBranchB()

            opts = self.ui.leOpts.text().strip()
            if opts:
                self.filterOpts(opts, self.gitViewB)

            branch = self.ui.gitViewA.currentBranch()
            if branch.startswith("remotes/origin/"):
                branch = branch[15:]
            elif branch:
                branch = "remotes/origin/" + branch

            if not self.mergeWidget:
                self.gitViewB.reloadBranches(branch)
            self.ui.acCompare.setChecked(True)
        elif mode == MainWindow.MergeMode:
            self.mergeWidget = MergeWidget()
            self.mergeWidget.requestResolve.connect(
                self.__onRequestResolve)

            # delay a while to let it show front to mainwindow
            QTimer.singleShot(0, self.mergeWidget.show)
            if not self.gitViewB:
                self.setMode(MainWindow.CompareMode)
            # not allowed changed in this mode
            self.ui.leRepo.setReadOnly(True)
            self.ui.acCompare.setEnabled(False)
            self.ui.btnRepoBrowse.setEnabled(False)

    def showCommit(self, sha1):
        if not sha1:
            return

        # Ugly code
        self.ui.gitViewA.ui.logView.switchToCommit(sha1, True)
        if self.gitViewB:
            self.gitViewB.ui.logView.switchToCommit(sha1, True)
