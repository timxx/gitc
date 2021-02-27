# -*- coding: utf-8 -*-

from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtCore import *

from .ui_preferences import *
from .mergetool import MergeTool
from .comboboxitemdelegate import ComboBoxItemDelegate
from .stylehelper import dpiScaled
from .linkeditdialog import LinkEditDialog
from .gitutils import Git

import sys
import os
import re


class ToolTableModel(QAbstractTableModel):
    Col_Scenes = 0
    Col_Suffix = 1
    Col_Tool = 2

    suffixExists = Signal(str)

    def __init__(self, parent=None):
        super(ToolTableModel, self).__init__(parent)

        self._data = []
        self._scenes = {MergeTool.Nothing: self.tr("Disabled"),
                        MergeTool.CanDiff: self.tr("Diff"),
                        MergeTool.CanMerge: self.tr("Merge"),
                        MergeTool.Both: self.tr("Both")}

    def _checkSuffix(self, row, suffix):
        for i in range(len(self._data)):
            if i == row:
                continue
            tool = self._data[i]
            if tool.suffix == suffix:
                return False

        return True

    def columnCount(self, parent=QModelIndex()):
        return 3

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal:
            return None
        if role != Qt.DisplayRole:
            return None

        if section == self.Col_Scenes:
            return self.tr("Scenes")
        if section == self.Col_Suffix:
            return self.tr("Suffix")
        if section == self.Col_Tool:
            return self.tr("Tool")

        return None

    def flags(self, index):
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        f |= Qt.ItemIsEditable

        return f

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        tool = self._data[index.row()]
        col = index.column()
        if role == Qt.DisplayRole:
            if col == self.Col_Suffix:
                return tool.suffix
            if col == self.Col_Tool:
                return tool.command
            if col == self.Col_Scenes:
                return self._scenes[tool.capabilities]

        return None

    def setData(self, index, value, role=Qt.EditRole):
        row = index.row()
        col = index.column()
        tool = self._data[row]

        if role == Qt.EditRole:
            value = value.strip()
            if not value:
                return False
            if col == self.Col_Suffix:
                if not self._checkSuffix(row, value):
                    self.suffixExists.emit(value)
                    return False
                tool.suffix = value
            elif col == self.Col_Tool:
                tool.command = value
            elif col == self.Col_Scenes:
                idx = list(self._scenes.values()).index(value)
                tool.capabilities = list(self._scenes.keys())[idx]
        else:
            return False

        self._data[row] = tool
        return True

    def insertRows(self, row, count, parent=QModelIndex()):
        self.beginInsertRows(parent, row, row + count - 1)

        for i in range(count):
            self._data.insert(row, MergeTool(MergeTool.Both))

        self.endInsertRows()

        return True

    def removeRows(self, row, count, parent=QModelIndex()):
        if row >= len(self._data):
            return False

        self.beginRemoveRows(parent, row, row + count - 1)

        for i in range(count - 1 + row, row - 1, -1):
            if i < len(self._data):
                del self._data[i]

        self.endRemoveRows()

        return True

    def rawData(self):
        return self._data

    def setRawData(self, data):
        parent = QModelIndex()

        if self._data:
            self.beginRemoveRows(parent, 0, len(self._data) - 1)
            self._data = []
            self.endRemoveRows()

        if data:
            self.beginInsertRows(parent, 0, len(data) - 1)
            self._data = data
            self.endInsertRows()

    def getSceneNames(self):
        return self._scenes.values()


class Preferences(QDialog):

    def __init__(self, settings, parent=None):
        super(Preferences, self).__init__(parent)

        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.settings = settings

        self.resize(dpiScaled(QSize(655, 396)))

        model = ToolTableModel(self)
        self.ui.tableView.setModel(model)
        self.ui.tableView.horizontalHeader().setSectionResizeMode(
            ToolTableModel.Col_Tool,
            QHeaderView.Stretch)

        delegate = ComboBoxItemDelegate(model.getSceneNames())
        self.ui.tableView.setItemDelegateForColumn(
            ToolTableModel.Col_Scenes, delegate)

        self.ui.cbFamilyLog.currentFontChanged.connect(
            self._onFamilyChanged)
        self.ui.cbFamilyDiff.currentFontChanged.connect(
            self._onFamilyChanged)

        self.ui.btnAdd.clicked.connect(
            self._onBtnAddClicked)
        self.ui.btnDelete.clicked.connect(
            self._onBtnDeleteClicked)

        self.ui.tableView.model().suffixExists.connect(
            self._onSuffixExists)

        self.ui.btnGlobal.clicked.connect(
            self._onBtnGlobalClicked)
        self.ui.btnDetect.clicked.connect(
            self._onBtnDetectClicked)

        self.ui.lbConfigImgDiff.linkActivated.connect(
            self._onConfigImgDiff)

        # default to General tab
        self.ui.tabWidget.setCurrentIndex(0)

        self.ui.buttonBox.accepted.connect(
            self._onAccepted)

        self.ui.cbCheckUpdates.toggled.connect(
            self._onCheckUpdatesChanged)

        self._initSettings()

    def _initSettings(self):
        # TODO: delay load config for each tab
        checked = self.settings.checkUpdatesEnabled()
        self.ui.cbCheckUpdates.setChecked(checked)
        self._onCheckUpdatesChanged(checked)

        self.ui.sbDays.setValue(
            self.settings.checkUpdatesInterval())

        font = self.settings.logViewFont()
        self.ui.cbFamilyLog.setCurrentFont(font)
        self.ui.cbFamilyLog.currentFontChanged.emit(font)

        font = self.settings.diffViewFont()
        self.ui.cbFamilyDiff.setCurrentFont(font)
        self.ui.cbFamilyDiff.currentFontChanged.emit(font)

        self.ui.colorA.setColor(self.settings.commitColorA())
        self.ui.colorB.setColor(self.settings.commitColorB())

        repoName = qApp.repoName()
        self.ui.linkEditWidget.setCommitUrl(self.settings.commitUrl(repoName))
        self.ui.linkEditWidget.setBugUrl(self.settings.bugUrl(repoName))
        self.ui.linkEditWidget.setBugPattern(
            self.settings.bugPattern(repoName))
        self.ui.cbFallback.setChecked(
            self.settings.fallbackGlobalLinks(repoName))

        self.ui.cbShowWhitespace.setChecked(self.settings.showWhitespace())
        self.ui.sbTabSize.setValue(self.settings.tabSize())

        self.ui.cbEsc.setChecked(self.settings.quitViaEsc())
        self.ui.cbState.setChecked(self.settings.rememberWindowState())

        index = self.settings.ignoreWhitespace()
        if index < 0 or index >= self.ui.cbIgnoreWhitespace.count():
            index = 0
        self.ui.cbIgnoreWhitespace.setCurrentIndex(index)

        tools = self.settings.mergeToolList()
        self.ui.tableView.model().setRawData(tools)

        name = self.settings.diffToolName()
        self.ui.cbDiffName.setCurrentText(name)
        self.ui.leDiffCmd.setText(Git.diffToolCmd(name))

        name = self.settings.mergeToolName()
        self.ui.cbMergeName.setCurrentText(name)
        self.ui.leMergeCmd.setText(Git.mergeToolCmd(name))

    def _updateFontSizes(self, family, size, cb):
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

    def _onFamilyChanged(self, font):
        cbSize = self.ui.cbSizeLog
        size = self.settings.logViewFont().pointSize()
        if self.sender() == self.ui.cbFamilyDiff:
            cbSize = self.ui.cbSizeDiff
            size = self.settings.diffViewFont().pointSize()

        self._updateFontSizes(font.family(), size, cbSize)

    def _onBtnAddClicked(self, checked=False):
        model = self.ui.tableView.model()
        row = model.rowCount()
        if not model.insertRow(row):
            return
        index = model.index(row, ToolTableModel.Col_Suffix)
        self.ui.tableView.edit(index)

    def _onBtnDeleteClicked(self, checked=False):
        indexes = self.ui.tableView.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.information(self,
                                    qApp.applicationName(),
                                    self.tr("Please select one row at least to delete."))
            return

        if len(indexes) > 1:
            text = self.tr(
                "You have selected more than one record, do you really want delete all of them?")
            r = QMessageBox.question(self, qApp.applicationName(),
                                     text,
                                     QMessageBox.Yes,
                                     QMessageBox.No)
            if r != QMessageBox.Yes:
                return

        indexes.sort(reverse=True)
        for index in indexes:
            self.ui.tableView.model().removeRow(index.row())

    def _onSuffixExists(self, suffix):
        QMessageBox.information(self,
                                qApp.applicationName(),
                                self.tr("The suffix you specify is already exists."))

    def _onBtnGlobalClicked(self, clicked):
        linkEditDlg = LinkEditDialog(self)
        commitUrl = self.settings.commitUrl(None)
        bugUrl = self.settings.bugUrl(None)
        bugPattern = self.settings.bugPattern(None)

        linkEdit = linkEditDlg.linkEdit
        linkEdit.setCommitUrl(commitUrl)
        linkEdit.setBugUrl(bugUrl)
        linkEdit.setBugPattern(bugPattern)

        if linkEditDlg.exec_() == QDialog.Accepted:
            self.settings.setCommitUrl(None, linkEdit.commitUrl())
            self.settings.setBugUrl(None, linkEdit.bugUrl())
            self.settings.setBugPattern(None, linkEdit.bugPattern())

    def _onBtnDetectClicked(self):
        url, name, user = self._parseRepo()
        if not url or not name:
            QMessageBox.critical(
                self, self.window().windowTitle(),
                self.tr("Unable to detect current repo's name"))
            return

        linkEdit = self.ui.linkEditWidget
        if self._isQt5Repo(name):
            linkEdit.setBugUrl("https://bugreports.qt.io/browse/")
            linkEdit.setBugPattern("(QTBUG-[0-9]{5,6})")
            if user and self._isGithubRepo(url):
                linkEdit.setCommitUrl(
                    "https://github.com/{}/{}/commit/".format(user, name))
        elif self._isGithubRepo(url):
            linkEdit.setBugPattern("(#([0-9]+))")
            if user:
                linkEdit.setBugUrl(
                    "https://github.com/{}/{}/issues/".format(user, name))
                linkEdit.setCommitUrl(
                    "https://github.com/{}/{}/commit/".format(user, name))
        elif self._isGiteeRepo(url):
            linkEdit.setBugPattern("(I[A-Z0-9]{4,})")
            if user:
                linkEdit.setBugUrl(
                    "https://gitee.com/{}/{}/issues/".format(user, name))
                linkEdit.setCommitUrl(
                    "https://gitee.com/{}/{}/commit/".format(user, name))
        elif self._isGitlabRepo(url):
            linkEdit.setBugPattern("(#([0-9]+))")
            if user:
                linkEdit.setBugUrl(
                    "https://gitlab.com/{}/{}/-/issues/".format(user, name))
                linkEdit.setCommitUrl(
                    "https://gitlab.com/{}/{}/-/commit/".format(user, name))
        else:
            QMessageBox.critical(
                self, self.window().windowTitle(),
                self.tr("Unsupported repository"))

    def _onConfigImgDiff(self, link):
        path = self._imgDiffBin()
        if not path:
            QMessageBox.critical(
                self, self.window().windowTitle(),
                self.tr("Unable to find the path of imgdiff!"))
            return

        ret, error = Git.setDiffTool(
            "imgdiff", '%s "$LOCAL" "$REMOTE"' % path)
        if ret != 0:
            QMessageBox.critical(
                self, self.window().windowTitle(),
                error)
            return

        ret, error = Git.setMergeTool(
            "imgdiff", '%s "$BASE" "$LOCAL" "$REMOTE" -o "$MERGED"' % path)
        if ret != 0:
            QMessageBox.critical(
                self, self.window().windowTitle(),
                error)

    def _onAccepted(self):
        if not self._checkBugPattern():
            QMessageBox.critical(
                self, self.window().windowTitle(),
                self.tr("The bug pattern is invalid, please check again."))
            self.ui.tabWidget.setCurrentWidget(self.ui.tabSummary)
            self.ui.linkEditWidget.leBugPattern.setFocus()
            return

        if not self._checkTool(True):
            QMessageBox.critical(
                self, self.window().windowTitle(),
                self.tr("The diff tool name can't be empty!"))
            self.ui.tabWidget.setCurrentWidget(self.ui.tabTools)
            self.ui.cbDiffName.setFocus()
            return

        if not self._checkTool(False):
            QMessageBox.critical(
                self, self.window().windowTitle(),
                self.tr("The merge tool name can't be empty!"))
            self.ui.tabWidget.setCurrentWidget(self.ui.tabTools)
            self.ui.cbMergeName.setFocus()
            return

        self.accept()

    def _onCheckUpdatesChanged(self, checked):
        self.ui.sbDays.setEnabled(checked)

    def _checkBugPattern(self):
        value = self.ui.linkEditWidget.bugPattern().strip()
        if not value:
            return True

        try:
            re.compile(value)
            return True
        except:
            return False

    def _checkTool(self, isDiff):
        if isDiff:
            name = self.ui.cbDiffName.currentText().strip()
            cmd = self.ui.leDiffCmd.text().strip()
        else:
            name = self.ui.cbMergeName.currentText().strip()
            cmd = self.ui.leMergeCmd.text().strip()

        return not cmd or name

    def _imgDiffBin(self):
        def _quote(path):
            if " " in path:
                return '"' + path + '"'
            return path

        exeName = os.path.basename(sys.argv[0])
        exePath = os.path.abspath(os.path.dirname(sys.argv[0]))
        # source version
        if exeName == "qgitc.py":
            path = os.path.join(exePath, "mergetool", "imgdiff.py")
            if not os.path.exists(path):
                return None

            bin = sys.executable
            if bin.endswith(".exe") and not bin.endswith("w.exe"):
                bin = bin.replace(".exe", "w.exe")

            return _quote(bin) + " " + _quote(path)
        else:
            path = os.path.join(exePath, "imgdiff")
            if sys.platform == "win32":
                path += ".exe"
            if not os.path.exists(path):
                return None

            return _quote(path)

        return None

    def _parseRepo(self):
        url = Git.repoUrl()
        name = None
        user = None
        if not url:
            return None, None, None

        index = url.rfind('/')
        if index != -1:
            name = url[index+1:]
            if name.endswith(".git"):
                name = name[:-4]

        # unsupported
        if index == -1 or url.startswith("ssh://"):
            return url, name, user

        if url.startswith("git@"):
            index2 = url.rfind(':', 0, index)
            if index2 != -1:
                user = url[index2+1:index]
        else:
            index2 = url.rfind('/', 0, index)
            if index2 != -1:
                user = url[index2+1:index]

        return url, name, user

    def _isQt5Repo(self, repoName):
        return repoName in [
            "qt5", "qt3d", "qtactiveqt", "qtandroidextras",
            "qtbase", "qtcanvas3d", "qtcharts",
            "qtconnectivity", "qtdatavis3d", "qtdeclarative",
            "qtdoc", "qtgamepad", "qtgraphicaleffects",
            "qtimageformats", "qtlocation", "qtmacextras",
            "qtmultimedia", "qtnetworkauth", "qtpurchasing",
            "qtqa", "qtquickcontrols", "qtquickcontrols2",
            "qtremoteobjects", "qtrepotools", "qtscript",
            "qtscxml", "qtsensors", "qtserialbus",
            "qtserialport", "qtspeech", "qtsvg",
            "qttools", "qttranslations", "qtvirtualkeyboard",
            "qtwayland", "qtwebchannel", "qtwebengine",
            "qtwebglplugin", "qtwebsockets", "qtwebview",
            "qtwinextras", "qtx11extras", "qtxmlpatterns"]

    def _isGithubRepo(self, repoUrl):
        return repoUrl.startswith("git@github.com:") or \
            repoUrl.startswith("https://github.com/")

    def _isGiteeRepo(self, repoUrl):
        return repoUrl.startswith("git@gitee.com:") or \
            repoUrl.startswith("https://gitee.com/")

    def _isGitlabRepo(self, repoUrl):
        return repoUrl.startswith("git@gitlab.com:") or \
            repoUrl.startswith("https://gitlab.com/")

    def save(self):
        # TODO: only update those values that really changed
        value = self.ui.cbCheckUpdates.isChecked()
        self.settings.setCheckUpdatesEnabled(value)

        value = self.ui.sbDays.value()
        self.settings.setCheckUpdatesInterval(value)

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

        value = self.ui.linkEditWidget.commitUrl().strip()
        repoName = qApp.repoName()
        self.settings.setCommitUrl(repoName, value)

        value = self.ui.linkEditWidget.bugUrl().strip()
        self.settings.setBugUrl(repoName, value)

        value = self.ui.linkEditWidget.bugPattern().strip()
        self.settings.setBugPattern(repoName, value)

        value = self.ui.cbFallback.isChecked()
        self.settings.setFallbackGlobalLinks(repoName, value)

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

        tools = self.ui.tableView.model().rawData()
        # TODO: validate if all tool isValid before saving
        self.settings.setMergeToolList(tools)

        name = self.ui.cbDiffName.currentText()
        self.settings.setDiffToolName(name)

        value = self.ui.leDiffCmd.text()
        ret, error = Git.setDiffTool(name, value)
        if ret != 0 and error:
            QMessageBox.critical(
                self, self.window().windowTitle(),
                error)

        name = self.ui.cbMergeName.currentText()
        self.settings.setMergeToolName(name)

        value = self.ui.leMergeCmd.text()
        ret, error = Git.setMergeTool(name, value)

        if ret != 0 and error:
            QMessageBox.critical(
                self, self.window().windowTitle(),
                error)
