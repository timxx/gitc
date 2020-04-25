# -*- coding: utf-8 -*-

from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from collections import namedtuple

from pygit2 import Repository

from .common import *
from .gitutils import Git
from .findwidget import FindWidget

import re
import bisect


LineItem = namedtuple("LineItem", ["type", "content"])

diff_begin_re = re.compile(r"^@{2,}( (\+|\-)[0-9]+(,[0-9]+)?)+ @{2,}")

sha1_re = re.compile("(?<![a-zA-Z0-9_])[a-f0-9]{7,40}(?![a-zA-Z0-9_])")
email_re = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
url_re = re.compile("((https?|ftp)://[a-zA-Z0-9@:%_+-.~#?&/=()]+)")

diff_encoding = "utf-8"
cr_char = "^M"


def createFormatRange(start, length, fmt):
    formatRange = QTextLayout.FormatRange()
    formatRange.start = start
    formatRange.length = length
    formatRange.format = fmt

    return formatRange


class TreeItemDelegate(QItemDelegate):

    def __init__(self, parent=None):
        super(TreeItemDelegate, self).__init__(parent)
        self.pattern = None

    def paint(self, painter, option, index):
        text = index.data()

        itemSelected = option.state & QStyle.State_Selected
        self.drawBackground(painter, option, index)
        self.drawFocus(painter, option, option.rect)

        textLayout = QTextLayout(text, option.font)
        textOption = QTextOption()
        textOption.setWrapMode(QTextOption.NoWrap)

        textLayout.setTextOption(textOption)

        formats = []
        if index.row() != 0 and self.pattern:
            matchs = self.pattern.finditer(text)
            fmt = QTextCharFormat()
            if itemSelected:
                fmt.setForeground(QBrush(Qt.yellow))
            else:
                fmt.setBackground(QBrush(Qt.yellow))
            for m in matchs:
                rg = createFormatRange(m.start(), m.end() - m.start(), fmt)
                formats.append(rg)

        textLayout.setAdditionalFormats(formats)

        textLayout.beginLayout()
        line = textLayout.createLine()
        line.setPosition(QPointF(0, 0))
        textLayout.endLayout()

        painter.save()
        if itemSelected:
            painter.setPen(option.palette.color(QPalette.HighlightedText))
        else:
            painter.setPen(option.palette.color(QPalette.WindowText))

        textLayout.draw(painter, QPointF(option.rect.topLeft()))
        painter.restore()

    def setHighlightPattern(self, pattern):
        self.pattern = pattern


class DiffFetcher(QThread):

    fetchFinished = Signal()
    diffAvailable = Signal(list, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._row = 0

    def _parse(self, patch):
        lineItems = []
        fileItems = {}

        fileItems[patch.delta.new_file.path] = self._row
        lineItems.append(LineItem(TextLine.File,
                                  patch.delta.new_file.path))
        # renames, keep new file name only
        if patch.delta.new_file.path != patch.delta.old_file.path:
            fileItems[patch.delta.old_file.path] = self._row
        self._row += 1

        lines = patch.text.rstrip().split('\n')

        # file info
        for i in range(1, len(lines)):
            if self.isInterruptionRequested():
                return

            line = lines[i]
            if line.startswith("--- ") or line.startswith("+++ "):
                i += 1
                break

            lineItems.append(LineItem(TextLine.FileInfo, line))
            self._row += 1

        i += 1
        # diff content
        if i < len(lines):
            for line in lines[i:]:
                if self.isInterruptionRequested():
                    return

                lineItems.append(LineItem(TextLine.Diff, line))
                self._row += 1

        # add an empty line
        lineItems.append(LineItem(TextLine.Diff, ''))
        self._row += 1

        if not self.isInterruptionRequested():
            self.diffAvailable.emit(lineItems, fileItems)

    def setBeginRow(self, row):
        self._row = row

    def cancel(self):
        if self.isRunning():
            self.requestInterruption()

    def fetch(self, sha1, branch=None, filterPath=None, args=None):
        self.cancel()

        self._sha1 = sha1
        self._filterPath = filterPath
        self._args = args
        self._repo_dir = Git.repo.workdir
        self._branch = branch

        self.start()

    def run(self):
        repo = Repository(self._repo_dir)

        if self.isInterruptionRequested():
            return

        if self._sha1 == Git.LCC_SHA1 or self._sha1 == Git.LUC_SHA1:
            if self._branch != repo.head.shorthand:
                repo = Git.loadForBranch(repo, self._branch)

        if self.isInterruptionRequested():
            return

        # TODO: filter pattern
        try:
            if self._sha1 == Git.LCC_SHA1:
                diff = repo.diff("HEAD", cached=True)
            elif self._sha1 == Git.LUC_SHA1:
                diff = repo.diff()
            else:
                diff = repo.diff(self._sha1 + "^", self._sha1)

            diff.find_similar()
            for patch in diff:
                self._parse(patch)
        except KeyError:
            pass

        if not self.isInterruptionRequested():
            self.fetchFinished.emit()


class DiffView(QWidget):
    requestCommit = Signal(str, bool, bool)

    beginFetch = Signal()
    endFetch = Signal()

    def __init__(self, parent=None):
        super(DiffView, self).__init__(parent)

        self.viewer = PatchViewer(self)
        self.treeWidget = QTreeWidget(self)
        self.filterPath = None
        self.twMenu = QMenu()
        self.commit = None
        self.branch = None
        self.gitArgs = []
        self.fetcher = DiffFetcher(self)

        self.twMenu.addAction(self.tr("External &diff"),
                              self.__onExternalDiff)
        self.twMenu.addAction(self.tr("&Copy path"),
                              self.__onCopyPath)
        self.twMenu.addAction(self.tr("Copy &Windows path"),
                              self.__onCopyWinPath)
        self.twMenu.addSeparator()
        self.twMenu.addAction(self.tr("&Log this file"),
                              self.__onFilterPath)

        self.splitter = QSplitter(self)
        self.splitter.addWidget(self.viewer)
        self.splitter.addWidget(self.treeWidget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)

        self.treeWidget.setColumnCount(1)
        self.treeWidget.setHeaderHidden(True)
        self.treeWidget.setRootIsDecorated(False)
        self.treeWidget.header().setStretchLastSection(False)
        self.treeWidget.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.itemDelegate = TreeItemDelegate(self)
        self.treeWidget.setItemDelegate(self.itemDelegate)

        width = self.sizeHint().width()
        sizes = [width * 2 / 3, width * 1 / 3]
        self.splitter.setSizes(sizes)

        self.treeWidget.currentItemChanged.connect(self.__onTreeItemChanged)
        self.treeWidget.itemDoubleClicked.connect(
            self.__onTreeItemDoubleClicked)

        self.viewer.fileRowChanged.connect(self.__onFileRowChanged)
        self.viewer.requestCommit.connect(self.requestCommit)

        sett = qApp.instance().settings()
        sett.ignoreWhitespaceChanged.connect(
            self.__onIgnoreWhitespaceChanged)
        self.__onIgnoreWhitespaceChanged(sett.ignoreWhitespace())

        self.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeWidget.customContextMenuRequested.connect(
            self.__onTreeWidgetContextMenuRequested)

        self.fetcher.diffAvailable.connect(
            self.__onDiffAvailable)
        self.fetcher.fetchFinished.connect(
            self.__onFetchFinished)

    def __onTreeItemChanged(self, current, previous):
        if current:
            row = current.data(0, Qt.UserRole)
            self.viewer.scrollToRow(row)

    def __onFileRowChanged(self, row):
        for i in range(self.treeWidget.topLevelItemCount()):
            item = self.treeWidget.topLevelItem(i)
            n = item.data(0, Qt.UserRole)
            if n == row:
                self.treeWidget.blockSignals(True)
                self.treeWidget.setCurrentItem(item)
                self.treeWidget.blockSignals(False)
                break

    def __onExternalDiff(self):
        item = self.treeWidget.currentItem()
        if not item:
            return
        if not self.commit:
            return
        filePath = item.text(0)
        tool = self.__diffToolForFile(filePath)
        Git.externalDiff(self.commit, filePath, tool)

    def __doCopyPath(self, asWin=False):
        item = self.treeWidget.currentItem()
        if not item:
            return

        clipboard = QApplication.clipboard()
        if not asWin:
            clipboard.setText(item.text(0))
        else:
            clipboard.setText(item.text(0).replace('/', '\\'))

    def __onCopyPath(self):
        self.__doCopyPath()

    def __onCopyWinPath(self):
        self.__doCopyPath(True)

    def __onFilterPath(self):
        item = self.treeWidget.currentItem()
        if not item:
            return

        filePath = item.text(0)
        self.window().setFilterFile(filePath)

    def __isCommentItem(self, item):
        # operator not implemented LoL
        # return item and item == self.treeWidget.topLevelItem(0):
        return item and item.data(0, Qt.UserRole) == 0

    def __onTreeItemDoubleClicked(self, item, column):
        if not item or self.__isCommentItem(item):
            return

        if not self.commit:
            return

        filePath = item.text(0)
        tool = self.__diffToolForFile(filePath)
        Git.externalDiff(self.commit, filePath, tool)

    def __onIgnoreWhitespaceChanged(self, index):
        args = ["", "--ignore-space-at-eol",
                "--ignore-space-change"]
        if index < 0 or index >= len(args):
            index = 0

        # TODO: remove args only
        self.gitArgs.clear()
        if index > 0:
            self.gitArgs.append(args[index])

        if self.commit:
            self.showCommit(self.commit, self.branch)

    def __onTreeWidgetContextMenuRequested(self, pos):
        item = self.treeWidget.currentItem()
        if not item:
            return

        if self.treeWidget.topLevelItemCount() < 2:
            return

        if self.__isCommentItem(item):
            return

        self.twMenu.exec_(self.treeWidget.mapToGlobal(pos))

    def __onDiffAvailable(self, lineItems, fileItems):
        self.__addToTreeWidget(fileItems)
        self.viewer.appendData(lineItems)

    def __onFetchFinished(self):
        self.viewer.clearCache()
        self.viewer.tryUpdate()
        self.endFetch.emit()

    def __addToTreeWidget(self, *args):
        """specify the @row number of the file in the viewer"""
        if len(args) == 1 and isinstance(args[0], dict):
            items = []
            for file, row in args[0].items():
                item = QTreeWidgetItem([file])
                item.setData(0, Qt.UserRole, row)
                items.append(item)
            self.treeWidget.addTopLevelItems(items)
        else:
            item = QTreeWidgetItem([args[0]])
            item.setData(0, Qt.UserRole, args[1])
            self.treeWidget.addTopLevelItem(item)

    def __commitDesc(self, sha1):
        if sha1 == Git.LUC_SHA1:
            subject = self.tr(
                "Local uncommitted changes, not checked in to index")
        elif sha1 == Git.LCC_SHA1:
            subject = self.tr(
                "Local changes checked in to index but not committed")
        else:
            subject = Git.commitSubject(sha1)

        return " (" + subject + ")"

    def __commitToLineItems(self, commit):
        items = []

        if not commit.sha1 in [Git.LUC_SHA1, Git.LCC_SHA1]:
            content = self.tr("Author: ") + commit.author + \
                " " + commit.authorDate
            item = LineItem(TextLine.Author, content)
            items.append(item)

            content = self.tr("Committer: ") + \
                commit.committer + " " + commit.committerDate
            item = LineItem(TextLine.Author, content)
            items.append(item)

        for parent in commit.parents:
            content = self.tr("Parent: ") + parent
            content += self.__commitDesc(parent)
            item = LineItem(TextLine.Parent, content)
            items.append(item)

        for child in commit.children:
            content = self.tr("Child: ") + child
            content += self.__commitDesc(child)
            items.append(LineItem(TextLine.Child, content))

        items.append(LineItem(TextLine.Comments, ""))

        comments = commit.comments.split('\n')
        for comment in comments:
            content = comment if not comment else "    " + comment
            item = LineItem(TextLine.Comments, content)
            items.append(item)

        items.append(LineItem(TextLine.Comments, ""))

        return items

    def __diffToolForFile(self, filePath):
        tools = qApp.instance().settings().mergeToolList()
        # ignored case even on Unix platform
        lowercase_file = filePath.lower()
        for tool in tools:
            if tool.canDiff() and tool.isValid():
                if lowercase_file.endswith(tool.suffix.lower()):
                    return tool.command

        return None

    def showCommit(self, commit, branch):
        self.clear()
        self.commit = commit
        self.branch = branch

        self.__addToTreeWidget(self.tr("Comments"), 0)

        item = self.treeWidget.topLevelItem(0)
        self.treeWidget.setCurrentItem(item)

        lineItems = self.__commitToLineItems(commit)
        self.viewer.setData(lineItems)

        self.fetcher.setBeginRow(len(lineItems))
        self.fetcher.fetch(commit.sha1, branch, self.filterPath, self.gitArgs)
        # FIXME: delay showing the spinner when loading small diff to avoid flicker
        self.beginFetch.emit()

    def clear(self):
        self.treeWidget.clear()
        self.viewer.setData(None)

    def setFilterPath(self, path):
        # no need update
        self.filterPath = path

    def updateSettings(self):
        self.viewer.updateSettings()

    def highlightKeyword(self, pattern, field=FindField.Comments):
        self.viewer.highlightKeyword(pattern, field)
        self.treeWidget.viewport().update()

    def saveState(self, settings, isBranchA):
        state = self.splitter.saveState()
        settings.setDiffViewState(state, isBranchA)

    def restoreState(self, settings, isBranchA):
        state = settings.diffViewState(isBranchA)
        if state:
            self.splitter.restoreState(state)


class Cursor():

    def __init__(self):
        self.clear()

    def clear(self):
        self._beginLine = -1
        self._beginPos = -1
        self._endLine = -1
        self._endPos = -1

    def isValid(self):
        return self._beginLine != -1 and \
            self._endLine != -1 and \
            self._beginPos != -1 and \
            self._endPos != -1

    def hasMultiLines(self):
        if not self.isValid():
            return False

        return self._beginLine != self._endLine

    def hasSelection(self):
        if not self.isValid():
            return False

        if self.hasMultiLines():
            return True
        return self._beginPos != self._endPos

    def within(self, line):
        if not self.hasSelection():
            return False

        if line >= self.beginLine() and line <= self.endLine():
            return True

        return False

    def beginLine(self):
        return min(self._beginLine, self._endLine)

    def endLine(self):
        return max(self._beginLine, self._endLine)

    def beginPos(self):
        if self._beginLine == self._endLine:
            return min(self._beginPos, self._endPos)
        elif self._beginLine < self._endLine:
            return self._beginPos
        else:
            return self._endPos

    def endPos(self):
        if self._beginLine == self._endLine:
            return max(self._beginPos, self._endPos)
        elif self._beginLine < self._endLine:
            return self._endPos
        else:
            return self._beginPos

    def moveTo(self, line, pos):
        self._beginLine = line
        self._beginPos = pos
        self._endLine = line
        self._endPos = pos

    def selectTo(self, line, pos):
        self._endLine = line
        self._endPos = pos


class Link():
    Sha1 = 0
    BugId = 1
    Email = 2
    Url = 3

    def __init__(self, start, end, linkType, lineType):
        self.start = start
        self.end = end
        self.type = linkType
        self.data = None
        self.lineType = lineType

    def setData(self, data):
        self.data = data

    def hitTest(self, pos):
        return self.start <= pos and pos <= self.end


class TextLine():

    Author = 0
    Parent = 1
    Child = 2
    Branch = 3
    Comments = 4
    File = 5
    FileInfo = 6
    Diff = 7

    def __init__(self, viewer, type, text):
        self._viewer = viewer
        self._type = type
        self._text = text
        self._layout = None
        self._links = []
        self._lineNo = 0
        self._patterns = None
        self._rehighlight = True
        self._invalidated = True
        self._font = viewer.defFont

        self._defOption = viewer.diffOption \
            if type == TextLine.Diff \
            else viewer.defOption

    def __relayout(self):
        self._layout.beginLayout()
        line = self._layout.createLine()
        self._layout.endLayout()

    def __findLinks(self, patterns):
        if self.isInfoType():
            return

        foundLinks = []
        for linkType, pattern in patterns.items():
            # only find email if item is author
            if linkType != Link.Email and \
                    self._type == TextLine.Author:
                continue

            matches = pattern.finditer(self._text)
            for m in matches:
                found = False
                i = bisect.bisect_left(foundLinks, (m.start(), m.end()))
                for x in range(i, len(foundLinks)):
                    start, end = foundLinks[x]
                    if (start <= m.start() and m.start() <= end) \
                            or (start <= m.end() and m.end() <= end):
                        found = True
                        break
                # not allow links in the same range
                if found:
                    continue

                link = Link(m.start(), m.end(), linkType, self._type)
                link.setData(m.group(0 if pattern.groups == 0 else 1))

                self._links.append(link)
                bisect.insort(foundLinks, (m.start(), m.end()))

    def createLinksFormats(self):
        if not self._links:
            return None

        fmt = QTextCharFormat()
        fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        fmt.setForeground(ColorSchema.Link)

        formats = []
        for link in self._links:
            rg = createFormatRange(link.start, link.end - link.start, fmt)
            formats.append(rg)

        return formats

    def type(self):
        return self._type

    def isInfoType(self):
        return self._type == TextLine.File or \
            self._type == TextLine.FileInfo

    def text(self):
        return self._text

    def layout(self):
        self.ensureLayout()
        return self._layout

    def defOption(self):
        return self._defOption

    def setDefOption(self, option):
        showWhitespace = option.flags() & QTextOption.ShowTabsAndSpaces
        oldShowWhitespace = self._defOption.flags() & QTextOption.ShowTabsAndSpaces if \
            self._defOption else False

        self._rehighlight = showWhitespace != oldShowWhitespace
        self._defOption = option

        if self._layout:
            self._layout.setTextOption(option)
            if self._rehighlight:
                self.rehighlight()
                self._rehighlight = False

    def setFont(self, font):
        self._font = font
        if self._layout:
            self._layout.setFont(self._font)
            self._invalidated = True

    def lineNo(self):
        return self._lineNo

    def setLineNo(self, n):
        self._lineNo = n

    def ensureLayout(self):
        if not self._layout:
            self._layout = QTextLayout(self._text, self._font)
            if self._defOption:
                self._layout.setTextOption(self._defOption)

            patterns = {Link.Sha1: sha1_re,
                        Link.Email: email_re,
                        Link.Url: url_re}
            if self._patterns:
                patterns.update(self._patterns)
            self.__findLinks(patterns)

        if self._rehighlight:
            self.rehighlight()
            self._rehighlight = False
            # need relayout
            self._invalidated = True

        if self._invalidated:
            self.__relayout()
            self._invalidated = False

    def boundingRect(self):
        self.ensureLayout()
        return self._layout.boundingRect()

    def offsetForPos(self, pos):
        self.ensureLayout()
        line = self._layout.lineAt(0)
        return line.xToCursor(pos.x())

    def offsetToX(self, offset):
        self.ensureLayout()
        line = self._layout.lineAt(0)
        x, _ = line.cursorToX(offset)
        return x

    def draw(self, painter, pos, selections=None, clip=QRectF()):
        self.ensureLayout()
        self._layout.draw(painter, pos, selections, clip)

    def rehighlight(self):
        formats = self.createLinksFormats()
        if formats:
            self._layout.setAdditionalFormats(formats)

    def setCustomLinkPatterns(self, patterns):
        self._links.clear()
        self._patterns = patterns

        if self._layout:
            if patterns:
                patterns[Link.Sha1] = sha1_re
                patterns[Link.Email] = email_re
                patterns[Link.Url] = url_re
                self.__findLinks(patterns)
            self.rehighlight()
        else:
            self._rehighlight = True

    def hitTest(self, pos):
        for link in self._links:
            if link.hitTest(pos):
                return link
        return None

    def hasCR(self):
        return False


class DiffTextLine(TextLine):

    def __init__(self, viewer, text):
        self._hasCR = text.endswith('\r')
        if self._hasCR:
            text = text[:-1]
        super(DiffTextLine, self).__init__(viewer, TextLine.Diff, text)

        self._crWidth = 0
        self.__updateCRWidth()

    def hasCR(self):
        return self._hasCR

    def setDefOption(self, option):
        super(DiffTextLine, self).setDefOption(option)
        self.__updateCRWidth()

    def setFont(self, font):
        super(DiffTextLine, self).setFont(font)
        self.__updateCRWidth()

    def boundingRect(self):
        br = super(DiffTextLine, self).boundingRect()
        br.setWidth(br.width() + self._crWidth)

        return br

    def draw(self, painter, pos, selections=None, clip=QRectF()):
        super(DiffTextLine, self).draw(painter, pos, selections, clip)

        if self._hasCR and self.__showWhitespaces():
            br = super(DiffTextLine, self).boundingRect()
            rect = self.boundingRect()
            rect.setTopLeft(br.topRight())
            rect.moveTo(rect.topLeft() + pos)

            painter.save()
            painter.setFont(self._font)
            painter.setPen(ColorSchema.Whitespace)
            painter.drawText(rect, Qt.AlignCenter | Qt.AlignVCenter, cr_char)
            painter.restore()

    def rehighlight(self):
        text = self.text()

        formats = []
        tcFormat = QTextCharFormat()
        if diff_begin_re.search(text) or text.startswith(r"\ No newline "):
            tcFormat.setForeground(ColorSchema.Newline)
        elif text.startswith("++"):
            tcFormat.setFontWeight(QFont.Bold)
        elif text.startswith(" +"):
            tcFormat.setFontWeight(QFont.Bold)
            tcFormat.setForeground(ColorSchema.Adding)
        elif text.startswith("+"):
            tcFormat.setForeground(ColorSchema.Adding)
        elif text.startswith(" -"):
            tcFormat.setFontWeight(QFont.Bold)
            tcFormat.setForeground(ColorSchema.Deletion)
        elif text.startswith("-"):
            tcFormat.setForeground(ColorSchema.Deletion)

        if tcFormat.isValid():
            formats.append(createFormatRange(0, len(text), tcFormat))

        if self._defOption:
            if self._defOption.flags() & QTextOption.ShowTabsAndSpaces:
                self.__applyWhitespaces(text, formats)

        linkFmt = self.createLinksFormats()
        if linkFmt:
            formats.extend(linkFmt)

        if formats:
            self._layout.setAdditionalFormats(formats)

    def __applyWhitespaces(self, text, formats):
        tcFormat = QTextCharFormat()
        tcFormat.setForeground(ColorSchema.Whitespace)

        offset = 0
        length = len(text)
        while offset < length:
            if text[offset].isspace():
                start = offset
                offset += 1
                while offset < length and text[offset].isspace():
                    offset += 1
                rg = createFormatRange(start, offset - start, tcFormat)
                formats.append(rg)
            else:
                offset += 1

    def __showWhitespaces(self):
        flags = self._defOption.flags()
        return flags & QTextOption.ShowTabsAndSpaces

    def __updateCRWidth(self):
        if self._hasCR and self.__showWhitespaces():
            fm = QFontMetrics(self._font)
            self._crWidth = fm.width(cr_char)
        else:
            self._crWidth = 0


class InfoTextLine(TextLine):

    def __init__(self, viewer, type, text):
        super(InfoTextLine, self).__init__(viewer, type, text)

    def rehighlight(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold)
        fmtRg = createFormatRange(0, len(self.text()), fmt)

        formats = []
        formats.append(fmtRg)

        self._layout.setAdditionalFormats(formats)


class ColorSchema():

    Newline = QColor(0, 0, 255)
    Adding = QColor(0, 128, 0)
    Deletion = QColor(255, 0, 0)
    Info = QColor(170, 170, 170)
    Link = QColor(Qt.blue)
    Whitespace = QColor(Qt.lightGray)
    SelFocus = QColor(173, 214, 255)
    SelNoFocus = QColor(229, 235, 241)


class PatchViewer(QAbstractScrollArea):
    fileRowChanged = Signal(int)
    requestCommit = Signal(str, bool, bool)

    def __init__(self, parent=None):
        super(PatchViewer, self).__init__(parent)

        self._lineItems = None
        self._textLines = {}
        # only when all data loaded can clear _lineItems
        self._canClearCache = False

        self.defOption = QTextOption()
        self.defOption.setWrapMode(QTextOption.NoWrap)

        self.updateSettings()

        self.highlightPattern = None
        self.highlightField = FindField.Comments
        self.wordPattern = None
        self.findPattern = None

        self.cursor = Cursor()
        self.tripleClickTimer = QElapsedTimer()
        self.clickOnLink = False
        self.currentLink = None
        self.cursorChanged = False

        self.menu = QMenu()
        self.findWidget = None

        action = self.menu.addAction(
            self.tr("&Open commit in browser"), self.__onOpenCommit)
        self.acOpenCommit = action
        self.menu.addSeparator()

        action = self.menu.addAction(self.tr("&Copy"), self.__onCopy)
        action.setIcon(QIcon.fromTheme("edit-copy"))
        action.setShortcuts(QKeySequence.Copy)
        self.acCopy = action

        self.menu.addAction(self.tr("Copy &All"), self.__onCopyAll)
        self.acCopyLink = self.menu.addAction(
            self.tr("Copy &Link"), self.__onCopyLink)

        self.menu.addSeparator()

        action = self.menu.addAction(
            self.tr("&Select All"), self.__onSelectAll)
        action.setIcon(QIcon.fromTheme("edit-select-all"))
        action.setShortcuts(QKeySequence.SelectAll)

        # FIXME: show scrollbar always to prevent dead loop
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.verticalScrollBar().valueChanged.connect(
            self.__onVScollBarValueChanged)

        self.viewport().setCursor(Qt.IBeamCursor)
        self.viewport().setMouseTracking(True)

    def updateSettings(self):
        settings = QApplication.instance().settings()

        # to save the time call settings every time
        self.defFont = settings.diffViewFont()

        fm = QFontMetrics(self.defFont)
        # total height of a line
        self.lineHeight = fm.height()

        tabSize = settings.tabSize()
        tabstopWidth = fm.width(' ') * tabSize

        self.diffOption = QTextOption(self.defOption)
        self.diffOption.setTabStop(tabstopWidth)

        if settings.showWhitespace():
            flags = self.diffOption.flags()
            self.diffOption.setFlags(flags | QTextOption.ShowTabsAndSpaces)

        self.bugUrl = settings.bugUrl()
        self.bugRe = re.compile(settings.bugPattern())

        pattern = None
        if self.bugUrl and self.bugRe:
            pattern = {Link.BugId: self.bugRe}

        for i, line in self._textLines.items():
            if line.type() == TextLine.Diff:
                line.setDefOption(self.diffOption)
            line.setFont(self.defFont)
            line.setCustomLinkPatterns(pattern)

        self.__adjust()
        self.viewport().update()

    def setData(self, items):
        self._lineItems = items
        self._textLines.clear()
        self._canClearCache = False
        self.currentLink = None
        self.clickOnLink = False
        self.cursor.clear()
        self.wordPattern = None

        hScrollBar = self.horizontalScrollBar()
        vScrollBar = self.verticalScrollBar()
        hScrollBar.blockSignals(True)
        vScrollBar.blockSignals(True)

        hScrollBar.setValue(0)
        vScrollBar.setValue(0)

        hScrollBar.blockSignals(False)
        vScrollBar.blockSignals(False)

        self.__adjust()
        self.viewport().update()

    def appendData(self, items):
        if not items:
            return

        prevTotalLines = self.textLineCount()

        if self._lineItems:
            self._lineItems.extend(items)
        else:
            self._lineItems = items

        linesPerPage = self.__linesPerPage()
        totalLines = self.textLineCount()

        vScrollBar = self.verticalScrollBar()
        vScrollBar.setRange(0, totalLines - linesPerPage)

        if prevTotalLines < linesPerPage and totalLines >= linesPerPage:
            self.__updateHScrollBar()
            self.viewport().update()

    def tryUpdate(self):
        """update if total lines less than one page"""
        linesPerPage = self.__linesPerPage()
        totalLines = self.textLineCount()

        if totalLines < linesPerPage:
            self.__updateHScrollBar()
            self.viewport().update()

    def textLineCount(self):
        if self._lineItems:
            return len(self._lineItems)

        return len(self._textLines)

    def hasTextLines(self):
        return self.textLineCount() > 0

    def textLineAt(self, index):
        if not self._lineItems:
            if not index in self._textLines:
                return None

        if index in self._textLines:
            return self._textLines[index]
        elif index < 0 or index >= len(self._lineItems):
            return None

        item = self._lineItems[index]

        text = item.content
        if item.type == TextLine.Diff:
            textLine = DiffTextLine(self, text)
        elif item.type == TextLine.File or \
                item.type == TextLine.FileInfo:
            textLine = InfoTextLine(self, item.type, text)
        else:
            textLine = TextLine(self, item.type, text)

        textLine.setLineNo(index)

        if self.bugUrl and self.bugRe:
            pattern = {Link.BugId: self.bugRe}
            textLine.setCustomLinkPatterns(pattern)

        self._textLines[index] = textLine

        # clear lineItems since all converted
        if self._canClearCache and \
                len(self._textLines) == len(self._lineItems):
            self._lineItems = None

        return textLine

    def scrollToRow(self, row):
        vScrollBar = self.verticalScrollBar()
        if vScrollBar.value() != row:
            vScrollBar.blockSignals(True)
            vScrollBar.setValue(row)
            vScrollBar.blockSignals(False)
            self.__updateHScrollBar()
            self.viewport().update()

    def highlightKeyword(self, pattern, field):
        self.highlightPattern = pattern
        self.highlightField = field
        self.viewport().update()

    def contentOffset(self):
        if not self.hasTextLines():
            return QPointF(0, 0)

        x = self.horizontalScrollBar().value()

        return QPointF(-x, -0)

    def mapToContents(self, pos):
        x = pos.x() + self.horizontalScrollBar().value()
        y = pos.y() + 0
        return QPoint(x, y)

    def firstVisibleLine(self):
        return self.verticalScrollBar().value()

    def textLineForPos(self, pos):
        """return the TextLine for @pos
        """
        if not self.hasTextLines():
            return None

        n = int(pos.y() / self.lineHeight)
        n += self.firstVisibleLine()

        if n >= self.textLineCount():
            n = self.textLineCount() - 1

        return self.textLineAt(n)

    def hasSelection(self):
        return self.cursor.hasSelection()

    def copy(self):
        self.__onCopy()

    def selectAll(self):
        self.__onSelectAll()

    def executeFind(self):
        if not self.findWidget:
            self.findWidget = FindWidget(self)
            self.findWidget.find.connect(self.__onFind)
            self.findWidget.findNext.connect(self.__onFindNext)
            self.findWidget.findPrevious.connect(self.__onFindPrevious)

        if self.cursor.hasSelection():
            # first line only
            beginLine = self.cursor.beginLine()
            beginPos = self.cursor.beginPos()

            endPos = self.cursor.endPos() \
                if not self.cursor.hasMultiLines() \
                else None
            text = self.__makeContent(beginLine, beginPos, endPos)
            self.findWidget.setText(text)
        self.findWidget.showAnimate()

    def ensureVisible(self, lineNo, start, end):
        if not self.hasTextLines():
            return

        startLine = self.firstVisibleLine()
        endLine = startLine + self.__linesPerPage()
        endLine = min(self.textLineCount(), endLine)

        if lineNo < startLine or lineNo >= endLine:
            self.verticalScrollBar().setValue(lineNo)

        hbar = self.horizontalScrollBar()

        textLine = self.textLineAt(lineNo)
        x1 = textLine.offsetToX(start)
        x2 = textLine.offsetToX(end)

        viewWidth = self.viewport().width()
        offset = hbar.value()

        if x1 < offset or x2 > (offset + viewWidth):
            hbar.setValue(x1)

    def clearCache(self):
        self._canClearCache = True
        if self._lineItems:
            if not self._textLines or (len(self._textLines) == len(self._lineItems)):
                self._lineItems = None

    def mouseMoveEvent(self, event):
        if self.tripleClickTimer.isValid():
            self.tripleClickTimer.invalidate()

        if not self.hasTextLines():
            return

        self.clickOnLink = False

        leftButtonPressed = event.buttons() & Qt.LeftButton
        self.__updateCursorAndLink(event.pos(), leftButtonPressed)

        if not leftButtonPressed:
            return

        self.__updateSelection()
        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return
        n = textLine.lineNo()
        offset = textLine.offsetForPos(self.mapToContents(event.pos()))
        self.cursor.selectTo(n, offset)
        self.wordPattern = None
        self.__updateSelection()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        if not self.hasTextLines():
            return

        self.clickOnLink = self.currentLink is not None

        timeout = QApplication.doubleClickInterval()
        # triple click
        isTripleClick = False
        if self.tripleClickTimer.isValid():
            isTripleClick = not self.tripleClickTimer.hasExpired(timeout)
            self.tripleClickTimer.invalidate()

        self.__updateSelection()
        self.wordPattern = None

        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return

        if isTripleClick:
            self.cursor.moveTo(textLine.lineNo(), 0)
            self.cursor.selectTo(textLine.lineNo(), len(textLine.text()))
            self.__updateSelection()
        else:
            offset = textLine.offsetForPos(self.mapToContents(event.pos()))
            self.cursor.moveTo(textLine.lineNo(), offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and \
                self.clickOnLink and self.currentLink:
            self.__openLink(self.currentLink)

        self.clickOnLink = False
        self.__updateCursorAndLink(event.pos(), False)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        self.tripleClickTimer.restart()

        if self.currentLink:
            return

        self.__updateSelection()
        self.cursor.clear()

        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return

        offset = textLine.offsetForPos(self.mapToContents(event.pos()))

        # find the word
        content = textLine.text()
        begin = offset
        end = offset

        if offset < len(content) and self.__isLetter(content[offset]):
            for i in range(offset - 1, -1, -1):
                if self.__isLetter(content[i]):
                    begin = i
                    continue
                break

            for i in range(offset + 1, len(content)):
                if self.__isLetter(content[i]):
                    end = i
                    continue
                break

        end += 1
        word = content[begin:end]

        if word:
            word = re.escape(word)
            self.wordPattern = re.compile('\\b' + word + '\\b')
            self.cursor.moveTo(textLine.lineNo(), begin)
            self.cursor.selectTo(textLine.lineNo(), end)
        else:
            self.wordPattern = None

        self.viewport().update()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.__doCopy()
        elif event.matches(QKeySequence.SelectAll):
            self.__onSelectAll()
        elif event.key() == Qt.Key_Home:
            self.verticalScrollBar().triggerAction(
                QScrollBar.SliderToMinimum)
        elif event.key() == Qt.Key_End:
            self.verticalScrollBar().triggerAction(
                QScrollBar.SliderToMaximum)
        else:
            super(PatchViewer, self).keyPressEvent(event)

    def contextMenuEvent(self, event):
        self.__updateCursorAndLink(event.pos(), False)
        canVisible = False
        if self.currentLink and self.currentLink.type == Link.Sha1:
            sett = qApp.instance().settings()
            url = sett.commitUrl()
            canVisible = url is not None

        self.acOpenCommit.setVisible(canVisible)
        self.acCopy.setEnabled(self.cursor.hasSelection())
        self.acCopyLink.setEnabled(self.currentLink is not None)

        self.menu.exec_(event.globalPos())

    def resizeEvent(self, event):
        self.__adjust()

    def paintEvent(self, event):
        if not self.hasTextLines():
            return

        painter = QPainter(self.viewport())

        startLine = self.firstVisibleLine()
        endLine = startLine + self.__linesPerPage() + 1
        endLine = min(self.textLineCount(), endLine)

        offset = self.contentOffset()
        viewportRect = self.viewport().rect()
        eventRect = event.rect()

        painter.setClipRect(eventRect)

        for i in range(startLine, endLine):
            textLine = self.textLineAt(i)

            r = textLine.boundingRect().translated(offset)

            formats = []
            formats.extend(self.__wordFormatRange(textLine.text()))

            if textLine.type() >= TextLine.Author and textLine.type() <= TextLine.Comments:
                fmt = self.__createCommentsFormats(textLine)
                if fmt:
                    formats.extend(fmt)
            elif textLine.type() == TextLine.Diff:
                fmt = self.__createDiffFormats(textLine)
                if fmt:
                    formats.extend(fmt)

            # selection
            selectionRg = self.__selectionFormatRange(i)
            if selectionRg:
                formats.append(selectionRg)

            if textLine.isInfoType():
                rr = textLine.boundingRect()
                rr.moveTop(rr.top() + r.top())
                rr.setLeft(0)
                rr.setRight(viewportRect.width() - offset.x())
                painter.fillRect(rr, ColorSchema.Info)

            textLine.draw(painter, offset, formats, QRectF(eventRect))

            offset.setY(offset.y() + r.height())

    def __highlightFormatRange(self, text):
        formats = []
        if self.highlightPattern:
            matchs = self.highlightPattern.finditer(text)
            fmt = QTextCharFormat()
            fmt.setBackground(QBrush(Qt.yellow))
            for m in matchs:
                rg = createFormatRange(m.start(), m.end() - m.start(), fmt)
                formats.append(rg)
        return formats

    def __wordFormatRange(self, text):
        if not self.wordPattern:
            return []

        formats = []
        fmt = QTextCharFormat()
        fmt.setTextOutline(QPen(QColor(68, 29, 98)))
        matches = self.wordPattern.finditer(text)
        for m in matches:
            rg = createFormatRange(m.start(), m.end() - m.start(), fmt)
            formats.append(rg)

        return formats

    def __selectionFormatRange(self, lineIndex):
        if not self.cursor.within(lineIndex):
            return None

        textLine = self.textLineAt(lineIndex)
        start = 0
        end = len(textLine.text())

        if self.cursor.beginLine() == lineIndex:
            start = self.cursor.beginPos()
        if self.cursor.endLine() == lineIndex:
            end = self.cursor.endPos()

        fmt = QTextCharFormat()
        if self.hasFocus() or (self.findWidget and self.findWidget.isVisible()):
            fmt.setBackground(QBrush(ColorSchema.SelFocus))
        else:
            fmt.setBackground(QBrush(ColorSchema.SelNoFocus))

        return createFormatRange(start, end - start, fmt)

    def __createCommentsFormats(self, textLine):
        if self.highlightField == FindField.Comments or \
                self.highlightField == FindField.All:
            return self.__highlightFormatRange(textLine.text())

        return None

    def __createDiffFormats(self, textLine):
        if self.highlightField == FindField.All:
            return self.__highlightFormatRange(textLine.text())
        elif FindField.isDiff(self.highlightField):
            text = textLine.text().lstrip()
            if text.startswith('+') or text.startswith('-'):
                return self.__highlightFormatRange(textLine.text())

        return None

    def __linesPerPage(self):
        return int(self.viewport().height() / self.lineHeight)

    def __adjust(self):

        hScrollBar = self.horizontalScrollBar()
        vScrollBar = self.verticalScrollBar()

        if not self.hasTextLines():
            hScrollBar.setRange(0, 0)
            vScrollBar.setRange(0, 0)
            return

        linesPerPage = self.__linesPerPage()
        totalLines = self.textLineCount()

        vScrollBar.setRange(0, totalLines - linesPerPage)
        vScrollBar.setPageStep(linesPerPage)

        self.__updateHScrollBar()

    def __updateHScrollBar(self):
        hScrollBar = self.horizontalScrollBar()
        vScrollBar = self.verticalScrollBar()

        if not self.hasTextLines():
            hScrollBar.setRange(0, 0)
            return

        linesPerPage = self.__linesPerPage()
        totalLines = self.textLineCount()

        offsetY = vScrollBar.value()
        maxY = min(totalLines, offsetY + linesPerPage)

        maxWidth = 0
        for i in range(offsetY, maxY):
            width = self.textLineAt(i).boundingRect().width()
            maxWidth = max(maxWidth, width)

        hScrollBar.setRange(0, maxWidth - self.viewport().width())
        hScrollBar.setPageStep(self.viewport().width())

    def __onVScollBarValueChanged(self, value):
        self.__updateHScrollBar()

        if not self.hasTextLines():
            return

        # TODO: improve
        for i in range(value, -1, -1):
            textLine = self.textLineAt(i)
            if textLine.type() == TextLine.File:
                self.fileRowChanged.emit(i)
                break
            elif textLine.type() == TextLine.Parent or textLine.type() == TextLine.Author:
                self.fileRowChanged.emit(0)
                break

    def __onOpenCommit(self):
        assert self.currentLink

        sett = qApp.instance().settings()
        url = sett.commitUrl()
        assert url

        url += self.currentLink.data
        QDesktopServices.openUrl(QUrl(url))

    def __onCopy(self):
        self.__doCopy()

    def __onCopyAll(self):
        self.__doCopy(False)

    def __onCopyLink(self):
        url = self.__makeLinkUrl(self.currentLink)
        if url:
            clipboard = QApplication.clipboard()
            mimeData = QMimeData()
            mimeData.setText(url)
            mimeData.setUrls([QUrl(url)])
            clipboard.setMimeData(mimeData)

    def __onSelectAll(self):
        if not self.hasTextLines():
            return

        self.wordPattern = None
        self.cursor.moveTo(0, 0)
        lastLine = self.textLineCount() - 1
        self.cursor.selectTo(lastLine, len(self.textLineAt(lastLine).text()))
        self.__updateSelection()

    def __onFind(self, text):
        if not self.hasTextLines():
            self.findWidget.updateFindStatus(False)
            return

        self.highlightPattern = None
        self.cursor.clear()
        self.viewport().update()

        if not text:
            self.findPattern = None
            self.findWidget.updateFindStatus(True)
            return

        # text only for now
        textRe = re.compile(re.escape(text))
        found = False

        for i in range(0, self.textLineCount()):
            if self.__findTextLine(i, textRe):
                found = True
                break

        self.findPattern = textRe
        self.findWidget.updateFindStatus(found)

    def __onFindNext(self):
        if not self.findPattern:
            return

        beginLine = 0
        if self.cursor.hasSelection():
            curLine = self.cursor.endLine()
            offset = self.cursor.endPos()
            beginLine = curLine + 1

            if self.__findTextLine(curLine, self.findPattern, pos=offset):
                self.findWidget.updateFindStatus(True)
                return

        for i in range(beginLine, self.textLineCount()):
            if self.__findTextLine(i, self.findPattern):
                self.findWidget.updateFindStatus(True)
                break

        # never set find status to NotFound

    def __onFindPrevious(self):
        if not self.findPattern:
            return

        beginLine = self.textLineCount() - 1
        if self.cursor.hasSelection():
            curLine = self.cursor.beginLine()
            offset = self.cursor.beginPos()
            beginLine = curLine - 1

            if self.__findTextLine(curLine, self.findPattern, endPos=offset, reverse=True):
                self.findWidget.updateFindStatus(True)
                return

        for i in range(beginLine, -1, -1):
            if self.__findTextLine(i, self.findPattern, reverse=True):
                self.findWidget.updateFindStatus(True)
                break

        # never set find status to NotFound

    def __findTextLine(self, lineNo, findPattern, pos=0, endPos=-1, reverse=False):
        text = self.textLineAt(lineNo).text()
        if endPos == -1:
            endPos = len(text)

        mo = None
        if reverse:
            iter = findPattern.finditer(text, pos=pos, endpos=endPos)
            if not iter:
                return False
            for mo in iter:
                pass
        else:
            mo = findPattern.search(text, pos=pos, endpos=endPos)

        if mo:
            self.__setFindResult(findPattern, lineNo, mo.start(), mo.end())
            return True

        return False

    def __setFindResult(self, textRe, lineNo, start, end):
        self.highlightPattern = textRe
        self.highlightField = FindField.All

        self.cursor.moveTo(lineNo, start)
        self.cursor.selectTo(lineNo, end)

        self.ensureVisible(lineNo, start, end)
        self.viewport().update()

    def __makeContent(self, lineNo, begin=None, end=None):
        textLine = self.textLineAt(lineNo)
        return textLine.text()[begin:end]

    def __doCopy(self, selectionOnly=True):
        if not self.hasTextLines():
            return
        if selectionOnly and not self.cursor.hasSelection():
            return

        if selectionOnly:
            beginLine = self.cursor.beginLine()
            beginPos = self.cursor.beginPos()
            endLine = self.cursor.endLine()
            endPos = self.cursor.endPos()
        else:
            beginLine = 0
            beginPos = 0
            endLine = self.textLineCount() - 1
            endPos = len(self.textLineAt(endLine - 1).text()) - 1

        content = ""
        # only one line
        if beginLine == endLine:
            content = self.__makeContent(beginLine, beginPos, endPos)
        else:
            # first line
            content = self.__makeContent(beginLine, beginPos, None)
            beginLine += 1

            # middle lines
            for i in range(beginLine, endLine):
                content += "\n" + self.__makeContent(i)

            # last line
            content += "\n" + \
                self.__makeContent(endLine, 0, endPos)

        clipboard = QApplication.clipboard()
        mimeData = QMimeData()
        mimeData.setText(content)

        # TODO: html format support
        clipboard.setMimeData(mimeData)

    def __updateSelection(self):
        if self.wordPattern:
            self.viewport().update()
            return

        if not self.cursor.hasSelection():
            return

        begin = self.cursor.beginLine()
        end = self.cursor.endLine()

        x = 0
        y = (begin - self.firstVisibleLine()) * self.lineHeight
        w = self.viewport().width()
        h = (end - begin + 1) * self.lineHeight

        rect = QRect(x, y, w, h)
        # offset for some odd fonts LoL
        offset = int(self.lineHeight / 2)
        rect.adjust(0, -offset, 0, offset)
        self.viewport().update(rect)

    def __isLetter(self, char):
        if char >= 'a' and char <= 'z':
            return True
        if char >= 'A' and char <= 'Z':
            return True

        if char == '_':
            return True

        if char.isdigit():
            return True

        return False

    def __updateCursorAndLink(self, pos, leftButtonPressed):
        self.currentLink = None
        textLine = self.textLineForPos(pos)
        if textLine:
            onText = textLine.boundingRect().right() >= pos.x()
            if onText:
                offset = textLine.offsetForPos(self.mapToContents(pos))
                self.currentLink = textLine.hitTest(offset)

        if not leftButtonPressed and self.currentLink:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)

    def __makeLinkUrl(self, link):
        if link.type == Link.Sha1:
            sett = qApp.instance().settings()
            url = sett.commitUrl()
            url += link.data
        elif link.type == Link.Email:
            url = "mailto:" + link.data
        elif link.type == Link.BugId:
            url = self.bugUrl + link.data
        else:
            url = link.data

        return url

    def __openLink(self, link):
        url = None
        if link.type == Link.Sha1:
            isNear = link.lineType in (TextLine.Parent, TextLine.Child)
            goNext = link.lineType == TextLine.Parent
            self.requestCommit.emit(link.data, isNear, goNext)
        elif link.type == Link.Email:
            url = "mailto:" + link.data
        elif link.type == Link.BugId:
            url = self.bugUrl + link.data
        else:
            url = link.data

        if url:
            QDesktopServices.openUrl(QUrl(url))
