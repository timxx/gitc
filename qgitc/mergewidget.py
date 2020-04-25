# -*- coding: utf-8 -*-

from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from .gitutils import Git
from .stylehelper import dpiScaled


STATE_CONFLICT = 0
STATE_RESOLVED = 1

RESOLVE_SUCCEEDED = 0
RESOLVE_FAILED = 1

StateRole = Qt.UserRole + 1


class MergeWidget(QWidget):
    requestResolve = Signal(str)
    resolveFinished = Signal(int)

    def __init__(self, parent=None):
        super(MergeWidget, self).__init__(parent)
        self.setWindowTitle(self.tr("Conflict List"))

        self.resolvedCount = 0
        self.iconResolved = self.__makeTextIcon(chr(0x2714), Qt.green)
        self.iconConflict = self.__makeTextIcon('!', Qt.red)

        self.resolveIndex = -1
        self.process = None

        self.__setupUi()
        self.__setupSignals()

        self.updateList()

    def __setupUi(self):
        self.view = QListView(self)
        self.model = QStandardItemModel(self)
        self.proxyModel = QSortFilterProxyModel(self)
        self.proxyModel.setSourceModel(self.model)

        self.view.setModel(self.proxyModel)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.leFilter = QLineEdit(self)

        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self.leFilter)
        vlayout.addWidget(self.view)

        hlayout = QHBoxLayout()

        self.status = QLabel(self)
        self.status.setToolTip(self.tr("Click to refresh the list"))
        self.cbAutoNext = QCheckBox(self.tr("Continuous resolve"))
        self.btnResolve = QPushButton(self.tr("Resolve"))

        hlayout.addWidget(self.status)
        hlayout.addSpacerItem(QSpacerItem(
            20, 20, QSizePolicy.MinimumExpanding))
        hlayout.addWidget(self.cbAutoNext)
        hlayout.addWidget(self.btnResolve)
        vlayout.addLayout(hlayout)

        self.cbAutoNext.setChecked(True)

        self.__setupMenu()

    def __setupMenu(self):
        self.menu = QMenu()
        self.acResolve = self.menu.addAction(
            self.tr("&Resolve"),
            self.__onMenuResolve)
        self.acUndoMerge = self.menu.addAction(
            self.tr("&Undo merge"),
            self.__onMenuUndoMerge)
        self.menu.addSeparator()

        self.menu.addAction(self.tr("Use &ours"),
                            self.__onMenuUseOurs)
        self.menu.addAction(self.tr("Use &theirs"),
                            self.__onMenuUseTheirs)

        self.menu.addSeparator()
        self.menu.addAction(self.tr("&Copy Path"),
                            self.__onMenuCopyPath,
                            QKeySequence("Ctrl+C"))
        self.menu.addAction(self.tr("Copy &Windows Path"),
                            self.__onMenuCopyWinPath)

    def __setupSignals(self):
        self.btnResolve.clicked.connect(self.__onResolveClicked)
        self.view.doubleClicked.connect(self.__onItemDoubleClicked)
        self.status.linkActivated.connect(self.__onStatusRefresh)
        self.leFilter.textChanged.connect(self.__onFilterChanged)

    def __makeTextIcon(self, text, color):
        img = QPixmap(dpiScaled(QSize(32, 32)))
        img.fill(Qt.transparent)

        painter = QPainter(img)
        painter.setPen(color)
        font = QFont()
        font.setPixelSize(dpiScaled(32))
        painter.setFont(font)
        painter.drawText(img.rect(), Qt.AlignCenter, text)
        painter = None

        return QIcon(img)

    def __updateStatus(self):
        # just don't wanna inherit a QLabel LoL
        total = self.model.rowCount()
        self.status.setText(
            "<a href='#refresh'>{}/{}</a>".format(self.resolvedCount,
                                                  total))

    def __resolvedIndex(self, index):
        index = self.proxyModel.mapToSource(index)
        item = self.model.itemFromIndex(index)
        item.setData(STATE_RESOLVED, StateRole)
        item.setIcon(self.iconResolved)
        self.resolvedCount += 1
        self.__updateStatus()

    def __checkCurrentResolve(self, index):
        if self.resolveIndex == index.row():
            text = self.tr(
                "You are resolving this file, please close it first.")
            QMessageBox.information(self,
                                    qApp.applicationName(),
                                    text)
            return False

        return True

    def __onResolveClicked(self, checked=False):
        index = self.view.currentIndex()
        self.resolve(index)

    def __onItemDoubleClicked(self, index):
        self.resolve(index)

    def __onStatusRefresh(self, link):
        if self.process:
            QMessageBox.information(self,
                                    qApp.applicationName(),
                                    self.tr("You can't refresh before close the merge window."))
            return
        self.updateList()

    def __onFilterChanged(self, text):
        self.proxyModel.setFilterRegExp(text)

    def __onMenuResolve(self):
        self.__onResolveClicked()

    def __onMenuUndoMerge(self):
        index = self.view.currentIndex()
        if index.data(StateRole) != STATE_RESOLVED:
            return

        if Git.undoMerge(index.data()):
            index = self.proxyModel.mapToSource(index)
            item = self.model.itemFromIndex(index)
            item.setData(STATE_CONFLICT, StateRole)
            item.setIcon(self.iconConflict)
            self.resolvedCount -= 1
            self.__updateStatus()

    def __onMenuUseOurs(self):
        index = self.view.currentIndex()
        if not self.__checkCurrentResolve(index):
            return
        if index.data(StateRole) == STATE_CONFLICT:
            if Git.resolveBy(True, index.data()):
                self.__resolvedIndex(index)

    def __onMenuUseTheirs(self):
        index = self.view.currentIndex()
        if not self.__checkCurrentResolve(index):
            return
        if index.data(StateRole) == STATE_CONFLICT:
            if Git.resolveBy(False, index.data()):
                self.__resolvedIndex(index)

    def __doCopyPath(self, asWin=False):
        index = self.view.currentIndex()
        if not index.isValid():
            return

        path = index.data(Qt.DisplayRole)
        qApp.clipboard().setText(path if not asWin else path.replace('/', '\\'))

    def __onMenuCopyPath(self):
        self.__doCopyPath()

    def __onMenuCopyWinPath(self):
        self.__doCopyPath(True)

    def __onReadyRead(self):
        # FIXME: since git might not flush all output at one time
        # delay some time to read all data for "Deleted merge"
        QTimer.singleShot(50, self.__onResolveReadyRead)

    def __onResolveReadyRead(self):
        if not self.process or not self.process.bytesAvailable():
            return

        data = self.process.readAllStandardOutput()
        # seems no options to control this buggy prompt
        if b'Continue merging other unresolved paths [y/n]?' in data:
            self.process.write(b"n\n")
        elif b'Deleted merge conflict for' in data:
            text = data.data().decode("utf-8")
            isCreated = "(c)reated" in text
            if isCreated:
                text = text.replace("(c)reated", "created")
            else:
                text = text.replace("(m)odified", "modified")
            text = text.replace("(d)eleted", "deleted")
            text = text.replace("(a)bort", "abort")

            msgBox = QMessageBox(
                QMessageBox.Question, qApp.applicationName(), text, QMessageBox.NoButton, self)
            msgBox.addButton(self.tr("Use &created") if isCreated
                             else self.tr("Use &modified"),
                             QMessageBox.AcceptRole)
            msgBox.addButton(self.tr("&Deleted file"), QMessageBox.RejectRole)
            msgBox.addButton(QMessageBox.Abort)
            r = msgBox.exec_()
            if r == QMessageBox.AcceptRole:
                if isCreated:
                    self.process.write(b"c\n")
                else:
                    self.process.write(b"m\n")
            elif r == QMessageBox.RejectRole:
                self.process.write(b"d\n")
            else:  # r == QMessageBox.Abort:
                self.process.write(b"a\n")
        elif b'Symbolic link merge conflict for' in data:
            text = data.data().decode("utf-8")
            text = text.replace("(l)ocal", "local")
            text = text.replace("(r)emote", "remote")
            text = text.replace("(a)bort", "abort")

            msgBox = QMessageBox(
                QMessageBox.Question, qApp.applicationName(), text, QMessageBox.NoButton, self)
            msgBox.addButton(self.tr("Use &local"), QMessageBox.AcceptRole)
            msgBox.addButton(self.tr("Use &remote"), QMessageBox.RejectRole)
            msgBox.addButton(QMessageBox.Abort)
            r = msgBox.exec_()
            if r == QMessageBox.AcceptRole:
                self.process.write(b"l\n")
            elif r == QMessageBox.RejectRole:
                self.process.write(b"r\n")
            else:
                self.process.write(b"a\n")
        elif b'Was the merge successful [y/n]?' in data:
            # TODO:
            self.process.write(b"n\n")
        elif b'?' in data:
            # TODO: might have other prompt need yes no
            print("unhandled prompt", data)

    def __onResolveFinished(self, exitCode, exitStatus):
        if exitCode == 0:
            index = self.proxyModel.index(self.resolveIndex, 0)
            self.__resolvedIndex(index)

        self.process = None
        curRow = self.resolveIndex
        self.resolveIndex = -1

        self.resolveFinished.emit(RESOLVE_SUCCEEDED if exitCode == 0
                                  else RESOLVE_FAILED)

        self.leFilter.setEnabled(True)
        # auto next only when success
        if exitCode != 0:
            return

        if not self.cbAutoNext.isChecked():
            return

        if self.resolvedCount == self.model.rowCount():
            QMessageBox.information(self, qApp.applicationName(),
                                    self.tr("All resolved!"))
            return

        index = None
        allFilterResolved = True
        noEndConflicts = True
        # search to the end
        for i in range(curRow + 1, self.proxyModel.rowCount()):
            index = self.proxyModel.index(i, 0)
            if index.data(StateRole) == STATE_CONFLICT:
                allFilterResolved = False
                noEndConflicts = False
                break
            index = None

        # search from beginning
        if not index:
            for i in range(curRow):
                index = self.proxyModel.index(i, 0)
                if index.data(StateRole) == STATE_CONFLICT:
                    allFilterResolved = False
                    break
                index = None

        # to avoid show two messagebox if reach to the end
        if allFilterResolved:
            text = self.tr(
                "All filter conflicts are resolved, please clear the filter to resolve the rest.")
            QMessageBox.information(self, qApp.applicationName(), text)
            return
        elif noEndConflicts:
            text = self.tr(
                "Resolve reach to the end of list, do you want to resolve from beginning?")
            r = QMessageBox.question(
                self, qApp.applicationName(), text, QMessageBox.Yes, QMessageBox.No)
            if r == QMessageBox.No:
                return

        self.view.setCurrentIndex(index)
        self.resolve(index)

    def __onResolveError(self):
        data = self.process.readAllStandardError()
        if b'Unknown merge tool' in data:
            text = self.tr(
                "Unknown merge tool, please check your configuration.")
            QMessageBox.information(self,
                                    qApp.applicationName(),
                                    text)

    def contextMenuEvent(self, event):
        index = self.view.currentIndex()
        enabled = index.data(StateRole) == STATE_RESOLVED
        self.acResolve.setEnabled(not enabled)
        self.acUndoMerge.setEnabled(enabled)
        self.menu.exec_(event.globalPos())

    def sizeHint(self):
        return dpiScaled(QSize(500, 700))

    def updateList(self):
        files = Git.conflictFiles()
        self.model.clear()
        if files:
            for f in files:
                item = QStandardItem(self.iconConflict, f)
                item.setData(STATE_CONFLICT, StateRole)
                self.model.appendRow(item)

            index = self.proxyModel.index(0, 0)
            self.view.setCurrentIndex(index)
        self.resolvedCount = 0
        self.__updateStatus()

        for action in self.menu.actions():
            action.setEnabled(not files is None)
        self.btnResolve.setEnabled(not files is None)

    def resolve(self, index):
        if not index.isValid():
            return

        if index.data(StateRole) == STATE_RESOLVED:
            QMessageBox.information(self, qApp.applicationName(),
                                    self.tr("This file is already resolved."))
            return

        if self.process:
            QMessageBox.information(self, qApp.applicationName(),
                                    self.tr("Please resolve current conflicts before start a new one."))
            return

        # since we saved the index, so disabled ...
        self.leFilter.setEnabled(False)
        self.resolveIndex = index.row()
        file = index.data()
        args = ["mergetool", "--no-prompt"]

        tools = qApp.instance().settings().mergeToolList()
        # ignored case even on Unix platform
        lowercase_file = file.lower()
        for tool in tools:
            if tool.canMerge() and tool.isValid():
                if lowercase_file.endswith(tool.suffix.lower()):
                    args.append("--tool={}".format(tool.command))
                    break
        args.append(file)

        # subprocess is not suitable here
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.__onReadyRead)
        self.process.readyReadStandardError.connect(self.__onResolveError)
        self.process.finished.connect(self.__onResolveFinished)
        self.process.setWorkingDirectory(Git.repo.workdir)
        self.process.start("git", args)

        self.requestResolve.emit(file)
