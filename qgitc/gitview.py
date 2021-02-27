# -*- coding: utf-8 -*-

from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtCore import *
import PySide6

from .ui_gitview import *
from .common import *
from .gitutils import Git
from .stylehelper import dpiScaled
from .events import BlameEvent

import re


class GitView(QWidget):
    reqCommit = Signal()
    reqFind = Signal()

    def __init__(self, parent=None):
        super(GitView, self).__init__(parent)

        self.ui = Ui_GitView()
        self.ui.setupUi(self)

        self.logArgs = None
        self.branchA = True
        self.findPattern = None
        self.findNext = True
        self.findField = FindField.Comments

        self.ui.logView.setLogGraph(self.ui.logGraph)
        self.ui.logWidget.setStretchFactor(0, 0)
        self.ui.logWidget.setStretchFactor(1, 1)

        n = self.ui.logWidget.handleWidth()
        self.ui.logWidget.setHandleWidth(dpiScaled(n))

        n = self.ui.logWidget.lineWidth()
        self.ui.logWidget.setLineWidth(dpiScaled(n))

        height = self.ui.splitter.sizeHint().height()
        sizes = [height * 1 / 4, height * 3 / 4]
        self.ui.splitter.setSizes(sizes)

        self.ui.cbBranch.setInsertPolicy(QComboBox.NoInsert)
        self.ui.cbBranch.setEditable(True)

        self.ui.cbBranch.completer().setFilterMode(Qt.MatchContains)
        self.ui.cbBranch.completer().setCompletionMode(
            QCompleter.PopupCompletion)

        height = self.ui.lbBranch.height() // 6
        self.ui.branchSpinner.setLineLength(height)
        self.ui.branchSpinner.setInnerRadius(height)
        self.ui.branchSpinner.setNumberOfLines(14)

        self.ui.diffSpinner.setLineLength(height)
        self.ui.diffSpinner.setInnerRadius(height)
        self.ui.diffSpinner.setNumberOfLines(14)

        self.ui.findSpinner.setLineLength(height)
        self.ui.findSpinner.setInnerRadius(height)
        self.ui.findSpinner.setNumberOfLines(14)

        self.__setupSignals()

    def __setupSignals(self):
        self.ui.cbBranch.currentIndexChanged.connect(self.__onBranchChanged)
        self.ui.logView.currentIndexChanged.connect(self.__onCommitChanged)
        self.ui.logView.findFinished.connect(self.__onFindFinished)
        self.ui.logView.beginFetch.connect(self.__onBeginFetch)
        self.ui.logView.endFetch.connect(self.__onEndFetch)

        self.ui.diffView.requestCommit.connect(self.__onRequestCommit)
        self.ui.diffView.requestBlame.connect(self.__onRequestBlame)
        self.ui.diffView.beginFetch.connect(self.__onBeginFetch)
        self.ui.diffView.endFetch.connect(self.__onEndFetch)

        self.reqCommit.connect(self.__onReqCommit)
        self.reqFind.connect(self.__onFindCommit)

        self.ui.tbPrev.clicked.connect(self.__onPreFindCommit)
        self.ui.tbNext.clicked.connect(self.__onNextFindCommit)

        self.ui.leSha1.returnPressed.connect(self.reqCommit)
        self.ui.leFindWhat.returnPressed.connect(self.reqFind)

    def __updateBranches(self, activeBranch=None):
        self.ui.cbBranch.clear()
        self.ui.logView.clear()
        self.ui.diffView.clear()
        self.ui.leSha1.clear()

        if not Git.REPO_DIR:
            return

        branches = Git.branches()
        if not branches:
            self.window().showMessage(self.tr("Can't get branch"))
            return

        curBranchIdx = -1
        self.ui.cbBranch.blockSignals(True)

        for branch in branches:
            branch = branch.strip()
            if branch.startswith("remotes/origin/"):
                if not branch.startswith("remotes/origin/HEAD"):
                    self.ui.cbBranch.addItem(branch)
                    if activeBranch and activeBranch == branch:
                        curBranchIdx = self.ui.cbBranch.count() - 1
            elif branch:
                if branch.startswith("*"):
                    pure_branch = branch.replace("*", "").strip()
                    self.ui.cbBranch.addItem(pure_branch)
                    if curBranchIdx == -1 and (not activeBranch or activeBranch == pure_branch):
                        curBranchIdx = self.ui.cbBranch.count() - 1
                else:
                    if branch.startswith("+ "):
                        branch = branch[2:]
                    self.ui.cbBranch.addItem(branch.strip())
                    if activeBranch and activeBranch == branch:
                        curBranchIdx = self.ui.cbBranch.count() - 1

        if curBranchIdx != -1:
            self.ui.cbBranch.setCurrentIndex(curBranchIdx)

        self.ui.cbBranch.blockSignals(False)
        branchIdx = self.ui.cbBranch.currentIndex()
        self.__onBranchChanged(branchIdx)

    def __onBranchChanged(self, index):
        if self.ui.cbBranch.count() == 0:
            return
        if isinstance(index, int) and index == -1:
            return
        if isinstance(index, str) and not index:
            return

        self.ui.logView.clear()
        self.ui.diffView.clear()

        branch = self.ui.cbBranch.currentText()
        branchDir = Git.branchDir(branch)
        self.ui.diffView.setBranchDir(branchDir)

        self.ui.logView.showLogs(
            branch,
            self.logArgs)

    def __onCommitChanged(self, index):
        if self.ui.logView.cancelFindCommit(False):
            self.unsetCursor()
        if index != -1:
            commit = self.ui.logView.getCommit(index)
            self.ui.leSha1.setText(commit.sha1)
            self.ui.diffView.showCommit(commit)
        else:
            self.ui.leSha1.clear()
            self.ui.diffView.clear()

    def __onBeginFetch(self):
        o = self.sender()
        if isinstance(o, LogView):
            self.ui.branchSpinner.start()
        elif isinstance(o, DiffView):
            self.ui.diffSpinner.start()

    def __onEndFetch(self):
        o = self.sender()
        if isinstance(o, LogView):
            self.ui.branchSpinner.stop()
        elif isinstance(o, DiffView):
            self.ui.diffSpinner.stop()

    def __doFindCommit(self, beginCommit=0, findNext=True):
        findWhat = self.ui.leFindWhat.text().strip()
        self.findField = self.ui.cbFindWhat.currentIndex()
        findType = self.ui.cbFindType.currentIndex()
        self.findNext = findNext

        if not findWhat:
            self.ui.logView.highlightKeyword(None)
            self.ui.diffView.highlightKeyword(None)
            self.ui.logView.clearFindData()
            return

        if beginCommit == -1 or \
                beginCommit == self.ui.logView.getCount():
            self.__onFindFinished(FIND_NOTFOUND)
            return

        pattern = findWhat
        # not regexp, escape the special chars
        if findType != FIND_REGEXP:
            pattern = re.escape(findWhat)

        flags = re.IGNORECASE if findType == FIND_IGNORECASE else 0
        self.findPattern = re.compile(pattern, flags)
        findRange = range(beginCommit, self.ui.logView.getCount()
                          ) if findNext else range(beginCommit, -1, -1)

        if self.findField == FindField.Comments:
            self.ui.findSpinner.start()
            self.setCursor(Qt.WaitCursor)
            result = self.ui.logView.findCommitSync(self.findPattern,
                                                    findRange,
                                                    self.findField)
            self.__onFindFinished(result)
        else:
            param = FindParameter(findRange, findWhat,
                                  self.findField, findType)
            findStarted = self.ui.logView.findCommitAsync(param)
            if findStarted:
                self.ui.findSpinner.start()
                self.setCursor(Qt.WaitCursor)

    def __onReqCommit(self):
        sha1 = self.ui.leSha1.text().strip()
        if sha1:
            ok = self.ui.logView.switchToCommit(sha1)
            if not ok:
                msg = self.tr("Revision '{0}' is not known")
                self.window().showMessage(msg.format(sha1))

    def __onFindCommit(self):
        beginCommit = self.ui.logView.currentIndex()
        self.__doFindCommit(beginCommit, True)

    def __onPreFindCommit(self, checked=False):
        beginCommit = self.ui.logView.currentIndex() - 1
        self.__doFindCommit(beginCommit, False)

    def __onNextFindCommit(self, checked=False):
        beginCommit = self.ui.logView.currentIndex() + 1
        self.__doFindCommit(beginCommit, True)

    def __onFindFinished(self, result):
        self.ui.findSpinner.stop()
        self.unsetCursor()

        pattern = self.findPattern
        if self.findField == FindField.Comments:  # comments
            self.ui.logView.highlightKeyword(pattern)
        else:
            self.ui.logView.highlightKeyword(None)
        self.ui.diffView.highlightKeyword(pattern, self.findField)

        if result >= 0:
            self.ui.logView.setCurrentIndex(result)
        elif result == FIND_NOTFOUND:
            message = None
            if self.findNext:
                message = self.tr("Find reached the end of logs.")
            else:
                message = self.tr("Find reached the beginning of logs.")

            self.window().showMessage(message)

    def __onRequestCommit(self, sha1, isNear, goNext):
        if isNear:
            self.ui.logView.switchToNearCommit(sha1, goNext)
        else:
            self.ui.logView.switchToCommit(sha1)

    def __onRequestBlame(self, filePath, toParent):
        sha1 = None
        if toParent:
            idx = self.ui.logView.currentIndex()
            if idx != -1:
                commit = self.ui.logView.getCommit(idx)
                sha1 = commit.parents[0] if commit.parents else None

        rev = sha1 if sha1 else self.currentBranch()
        QCoreApplication.postEvent(qApp,
                                   BlameEvent(filePath, rev))

    def setBranchDesc(self, desc):
        self.ui.lbBranch.setText(desc)

    def setBranchB(self):
        self.branchA = False
        self.ui.logView.setBranchB()

    def reloadBranches(self, activeBranch=None):
        self.__updateBranches(activeBranch)

    def setCurrentBranch(self, branch):
        index = self.ui.cbBranch.findText(branch)
        if index == -1:
            index = self.ui.cbBranch.findText(branch, Qt.MatchEndsWith)
        if index != -1:
            self.ui.cbBranch.setCurrentIndex(index)

    def currentBranch(self):
        # use currentIndex to get the real branch
        index = self.ui.cbBranch.currentIndex()
        if index != -1:
            return self.ui.cbBranch.itemText(index)
        return ""

    def filterLog(self, args):
        paths = []
        # FIXME: file args should always the last one
        for arg in args:
            if not arg.startswith("-"):
                paths.append(arg)

        self.ui.diffView.setFilterPath(paths)
        self.ui.logView.setFilterPath(paths)

        if args != self.logArgs:
            self.logArgs = args
            index = self.ui.cbBranch.currentIndex()
            preSha1 = None
            curIdx = self.ui.logView.currentIndex()
            if curIdx != -1:
                preSha1 = self.ui.logView.getCommit(curIdx).sha1

            self.__onBranchChanged(index)

            if preSha1:
                self.ui.logView.switchToCommit(preSha1)

    def saveState(self, settings, isBranchA):
        state = self.ui.splitter.saveState()
        settings.setGitViewState(state, isBranchA)

        self.ui.diffView.saveState(settings, isBranchA)

    def restoreState(self, settings, isBranchA):
        state = settings.gitViewState(isBranchA)

        if state:
            self.ui.splitter.restoreState(state)

        self.ui.diffView.restoreState(settings, isBranchA)

    def setBranchChangeble(self, canChange):
        self.ui.cbBranch.setEnabled(canChange)
