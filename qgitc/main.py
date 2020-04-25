# -*- coding: utf-8 -*-

from PySide2.QtGui import *
from PySide2.QtCore import *

from pygit2 import Repository

from .ui_mainwindow import *
from .gitview import *
from .preferences import *
from .settings import *
from .gitutils import Git
from .diffview import PatchViewer
from .common import dataDirPath, normPath
from .aboutdialog import AboutDialog
from .mergewidget import MergeWidget
from .excepthandler import ExceptHandler
from .stylehelper import dpiScaled

import os
import sys
import argparse
import shlex


class FindSubmoduleThread(QThread):
    def __init__(self, repoDir, parent=None):
        super(FindSubmoduleThread, self).__init__(parent)

        self._repoDir = normPath(repoDir)
        self._submodules = []

    @property
    def submodules(self):
        if self.isFinished():
            return self._submodules
        return []

    def run(self):
        self._submodules.clear()

        repo = Repository(self._repoDir)
        submodules = repo.listall_submodules()
        if submodules:
            self._submodules = ["."]

            # FIXME: the pygit2 doesn't provide a way
            # to list only the checked out submodule
            for mod in submodules:
                dot_git = os.path.join(self._repoDir, mod, ".git")
                if os.path.exists(dot_git):
                    self._submodules.append(mod)

            return self._submodules

        submodules = []
        # some projects may not use submodule or subtree
        for root, subdirs, files in os.walk(self._repoDir, topdown=True):
            if os.path.normcase(root) == self._repoDir:
                continue
            if ".git" in subdirs or ".git" in files:
                dir = root.replace(self._repoDir + os.sep, "")
                if dir:
                    submodules.append(dir)
            # ignore all '.dir'
            subdirs[:] = [d for d in subdirs if not d.startswith(".")]

        if submodules:
            submodules.insert(0, '.')

        self._submodules = submodules


class MainWindow(QMainWindow):

    def __init__(self, mergeMode=False, parent=None):
        super(MainWindow, self).__init__(parent)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.resize(dpiScaled(QSize(800, 600)))

        self.gitViewB = None

        self.findSubmoduleThread = None

        self.mergeWidget = None
        if mergeMode:
            self.mergeWidget = MergeWidget()
            self.mergeWidget.show()
            self.setCompareMode()
            # not allowed changed in this mode
            self.ui.leRepo.setReadOnly(True)
            self.ui.acCompare.setEnabled(False)

        self.ui.cbSubmodule.setVisible(False)
        self.ui.lbSubmodule.setVisible(False)

        self.__setupSignals()
        self.__setupMenus()

    def __setupSignals(self):
        self.ui.acQuit.triggered.connect(QCoreApplication.instance().quit)

        self.ui.acPreferences.triggered.connect(
            self.__onAcPreferencesTriggered)

        self.ui.btnRepoBrowse.clicked.connect(self.__onBtnRepoBrowseClicked)

        self.ui.leRepo.textChanged.connect(self.__onRepoChanged)

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

        if self.mergeWidget:
            self.mergeWidget.requestResolve.connect(
                self.__onRequestResolve)

        # settings
        sett = qApp.instance().settings()

        sett.ignoreWhitespaceChanged.connect(
            self.__onIgnoreWhitespaceChanged)

        sett.showWhitespaceChanged.connect(
            self.ui.acVisualizeWhitespace.setChecked)

        # application
        qApp.focusChanged.connect(self.__updateEditMenu)

        self.ui.cbSubmodule.currentIndexChanged.connect(self.__onSubmoduleChanged)

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

        repo = Git.load(repoDir)
        if not repo:
            QMessageBox.critical(self, self.windowTitle(),
                                 self.tr("The directory you choosen is not a git repository!"))
            return

        self.ui.leRepo.setText(repo.workdir)

    def __isRepoChanged(self, repoDir):
        submodule = self.ui.cbSubmodule.currentText()
        if not submodule or submodule == ".":
            return not isSamePath(Git.repo.workdir, repoDir)

        curRepo = Git.repo.workdir[:-(len(submodule) + 1)]
        return not isSamePath(curRepo, repoDir)

    def __onRepoChanged(self, repoDir):
        needReload = True
        if not Git.repo or self.__isRepoChanged(repoDir):
            Git.repo = Git.load(repoDir)
        else:
            needReload = False

        if not Git.repo:
            msg = self.tr("'{0}' is not a git repository")
            self.ui.statusbar.showMessage(
                msg.format(repoDir),
                5000)  # 5 seconds

            # clear
            if Git.REF_MAP:
                Git.REF_MAP.clear()
            Git.REV_HEAD = None
        else:
            Git.REF_MAP = Git.refs()
            Git.REV_HEAD = Git.revHead()

        reloadSubmodule = needReload or self.ui.cbSubmodule.count() == 0
        if reloadSubmodule:
            self.ui.cbSubmodule.clear()
            self.ui.cbSubmodule.setVisible(False)
            self.ui.lbSubmodule.setVisible(False)

            if self.findSubmoduleThread and self.findSubmoduleThread.isRunning():
                self.findSubmoduleThread.terminate()

        if Git.repo and reloadSubmodule:
            self.ui.leRepo.setDisabled(True)
            self.ui.btnRepoBrowse.setDisabled(True)
            self.findSubmoduleThread = FindSubmoduleThread(Git.repo.workdir, self)
            self.findSubmoduleThread.finished.connect(
                self.__onFindSubmoduleFinished)
            self.findSubmoduleThread.start()

        if needReload or self.ui.gitViewA.branchCount() == 0:
            branch = Git.mergeBranchName() if self.mergeWidget else None
            self.ui.gitViewA.reloadBranches(branch)
            if self.gitViewB:
                self.gitViewB.reloadBranches()

    def __onAcPreferencesTriggered(self):
        settings = qApp.instance().settings()
        preferences = Preferences(settings, self)
        if preferences.exec_() == QDialog.Accepted:
            preferences.save()
            self.ui.gitViewA.updateSettings()
            if self.gitViewB:
                self.gitViewB.updateSettings()

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

        self.ui.gitViewA.updateSettings()
        if self.gitViewB:
            self.gitViewB.updateSettings()

    def __onAcCompareTriggered(self, checked):
        if checked:
            self.setCompareMode()
        else:
            self.setLogMode()

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
        submodule = self.ui.cbSubmodule.currentText()
        # not selected any submodule
        if not submodule:
            return

        top_dir = self.ui.leRepo.text()
        if submodule == ".":
            submodule = ""

        submodule_path = os.path.join(top_dir, submodule)
        if isSamePath(submodule_path, Git.repo.workdir):
            return

        Git.repo = Git.load(submodule_path)
        Git.REF_MAP = Git.refs()
        Git.REV_HEAD = Git.revHead()

        self.ui.gitViewA.reloadBranches(
            self.ui.gitViewA.currentBranch())
        if self.gitViewB:
            self.gitViewB.reloadBranches(
                self.gitViewB.currentBranch())

    def __onFindSubmoduleFinished(self):
        submodules = self.findSubmoduleThread.submodules
        for submodule in submodules:
            self.ui.cbSubmodule.addItem(submodule)
        self.ui.leRepo.setEnabled(True)
        self.ui.btnRepoBrowse.setEnabled(True)
        hasSubmodule = len(submodules) > 0
        self.ui.cbSubmodule.setVisible(hasSubmodule)
        self.ui.lbSubmodule.setVisible(hasSubmodule)

    def saveState(self):
        sett = qApp.instance().settings()
        if not sett.rememberWindowState():
            return False

        state = super(MainWindow, self).saveState()
        geometry = self.saveGeometry()
        sett.setWindowState(state, geometry, self.isMaximized())

        self.ui.gitViewA.saveState(sett, True)
        if self.gitViewB:
            self.gitViewB.saveState(sett, False)

        return True

    def restoreState(self):
        sett = qApp.instance().settings()
        if not sett.rememberWindowState():
            return False

        state, geometry, isMaximized = sett.windowState()
        if state:
            super(MainWindow, self).restoreState(state)
        if geometry:
            self.restoreGeometry(geometry)

        self.ui.gitViewA.restoreState(sett, True)
        if self.gitViewB:
            self.gitViewB.restoreState(sett, False)

        if isMaximized:
            self.setWindowState(self.windowState() | Qt.WindowMaximized)

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

    def closeEvent(self, event):
        self.saveState()
        super(MainWindow, self).closeEvent(event)
        QTimer.singleShot(0, qApp.quit)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            sett = qApp.instance().settings()
            if sett.quitViaEsc():
                self.close()
                return

        super(MainWindow, self).keyPressEvent(event)

    def setRepoDir(self, repoDir):
        self.ui.leRepo.setText(repoDir)

    def setFilterFile(self, filePath):
        if not filePath.startswith("-- "):
            self.ui.leOpts.setText("-- " + filePath)
        else:
            self.ui.leOpts.setText(filePath)
        self.__onOptsReturnPressed()

    def setCompareMode(self):
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
        else:
            branch = "remotes/origin/" + branch

        self.gitViewB.reloadBranches(branch)
        self.ui.acCompare.setChecked(True)

    def setLogMode(self):
        self.ui.gitViewA.setBranchDesc(self.tr("Branch"))

        self.gitViewB.deleteLater()
        self.gitViewB = None

        self.ui.acCompare.setChecked(False)


class Application(QApplication):

    def __init__(self, argv):
        super(Application, self).__init__(argv)

        self.setAttribute(Qt.AA_DontShowIconsInMenus, False)
        self.setApplicationName("qgitc")

        iconPath = dataDirPath() + "/icons/qgitc.svg"
        self.setWindowIcon(QIcon(iconPath))

        self.setupTranslator()
        self._settings = Settings(self)

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


app = None
sys.excepthook = ExceptHandler


def setAppUserId(appId):
    if os.name != "nt":
        return

    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
    except:
        pass


def unsetEnv(varnames):
    if hasattr(os, "unsetenv"):
        for var in varnames:
            os.unsetenv(var)
    else:
        for var in varnames:
            try:
                del os.environ[var]
            except KeyError:
                pass


def main():
    unsetEnv(["QT_SCALE_FACTOR", "QT_AUTO_SCREEN_SCALE_FACTOR"])

    parser = argparse.ArgumentParser()

    parser.add_argument("-r", "--repo",
                        help="Init repositories directory, default to current working dir if it is.")
    parser.add_argument("-f", "--file",
                        help="Filter file")
    parser.add_argument("-c", "--compare-mode", action="store_true",
                        help="Compare mode, show two branches for comparing")
    parser.add_argument("-m", "--merge-mode", action="store_true",
                        help="Merge mode, for helping resolve conflicts")

    args = parser.parse_args()

    setAppUserId("appid.qgitc.xyz")

    filterFile = args.file

    # profile = MyProfile()
    if args.repo:
        Git.repo = Git.load(args.repo)
    else:
        Git.repo = Git.load(os.getcwd())
    # profile = None

    global app
    app = Application(sys.argv)

    if args.merge_mode and not Git.isMergeInProgress():
        QMessageBox.information(None, app.applicationName(),
                                app.translate("app", "Not in merge state, now quit!"))
        sys.exit(0)

    window = MainWindow(args.merge_mode)
    window.setGeometry(QStyle.alignedRect(
        Qt.LeftToRight, Qt.AlignCenter,
        window.size(),
        app.desktop().availableGeometry()))

    # merge mode will also change to compare view
    if not args.merge_mode and args.compare_mode:
        window.setCompareMode()

    if filterFile:
        window.setFilterFile(filterFile)

    if Git.repo:
        window.setRepoDir(Git.repo.workdir)

    if window.restoreState():
        window.show()
    else:
        window.showMaximized()

    app.exec_()
    app.deleteLater()


# tips from http://pyqt.sourceforge.net/Docs/PySide2/gotchas.html
if __name__ == "__main__":
    main()
