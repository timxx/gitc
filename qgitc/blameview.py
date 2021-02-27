# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QToolButton,
    QSpacerItem,
    QSizePolicy,
    QMenu,
    QFrame,
    QMessageBox)
from PySide6.QtGui import (
    QPainter,
    QFontMetrics,
    QColor,
    QPen)
from PySide6.QtCore import (
    Qt,
    Signal,
    QRect,
    QRectF,
    QPointF,
    QUrl)

from datetime import datetime
from .datafetcher import DataFetcher
from .stylehelper import dpiScaled
from .sourceviewer import SourceViewer
from .textline import LinkTextLine, Link
from .gitutils import Git
from .colorschema import ColorSchema
from .events import (
    BlameEvent,
    ShowCommitEvent,
    OpenLinkEvent)
from .waitingspinnerwidget import QtWaitingSpinner
from .textviewer import TextViewer
from .common import decodeFileData

import re
import os


__all__ = ["BlameView"]

ABBREV_N = 4


class BlameLine:

    def __init__(self):
        self.sha1 = None
        self.oldLineNo = 0
        self.newLineNo = 0
        self.groupLines = 0

        self.author = None
        self.authorMail = None
        self.authorTime = None

        self.committer = None
        self.committerMail = None
        self.committerTime = None

        self.summary = None
        self.previous = None
        self.prevFileName = None
        self.filename = None
        self.text = None


def _timeStr(data):
    dt = datetime.fromtimestamp(float(data))
    return "%d-%02d-%02d %02d:%02d:%02d" % (
        dt.year, dt.month, dt.day,
        dt.hour, dt.minute, dt.second)


def _decode(data):
    return data.decode("utf-8")


class BlameFetcher(DataFetcher):

    dataAvailable = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._curLine = BlameLine()

    def parse(self, data):
        results = []
        # TODO: support utf16 32 split...
        lines = data.rstrip(self.separator).split(self.separator)
        for line in lines:
            if line[0] == 9:  # \t
                self._curLine.text = line[1:]
                results.append(self._curLine)
                self._curLine = BlameLine()
            elif line[0] == 97 and line[1] == 117:  # author
                if line[6] == 32:  # "author "
                    self._curLine.author = _decode(line[7:])
                elif line[7] == 109:  # "author-mail "
                    self._curLine.authorMail = _decode(line[12:])
                elif line[8] == 105:  # "author-time "
                    self._curLine.authorTime = _timeStr(line[12:])
                elif line[8] == 122:  # "author-tz "
                    assert(self._curLine.authorTime is not None)
                    self._curLine.authorTime += _decode(line[9:])
                else:
                    print("Invalid line:", line)
            elif line[0] == 99 and line[1] == 111:  # committer
                if line[9] == 32:  # "committer "
                    self._curLine.committer = _decode(line[10:])
                elif line[10] == 109:  # "committer-mail "
                    self._curLine.committerMail = _decode(line[15:])
                elif line[11] == 105:  # "committer-time "
                    self._curLine.committerTime = _timeStr(line[15:])
                elif line[11] == 122:  # "committer-tz "
                    assert(self._curLine.committerTime is not None)
                    self._curLine.committerTime += _decode(line[12:])
                else:
                    print("Invalid line:", line)
            elif line[0] == 115:  # "summary "
                self._curLine.summary = _decode(line[8:])
            elif line[0] == 112:  # "previous "
                parts = line.split(b' ')
                self._curLine.previous = _decode(parts[1])
                self._curLine.prevFileName = _decode(parts[2])
            elif line[0] == 102 and line[1] == 105:  # "filename "
                self._curLine.filename = _decode(line[9:])
            elif line[0] == 98 and line[1] == 111:  # boundary
                pass
            else:
                parts = line.split(b' ')
                if len(parts) < 3 or len(parts) > 4:
                    print("Invalid line:", line)
                else:
                    self._curLine.sha1 = _decode(parts[0])
                    self._curLine.oldLineNo = int(parts[1])
                    self._curLine.newLineNo = int(parts[2])
                    if len(parts) == 4:
                        self._curLine.groupLines = int(parts[3])

        if results:
            self.dataAvailable.emit(results)

    def makeArgs(self, args):
        file = args[0]
        rev = args[1]

        blameArgs = ["blame", "--porcelain", "--", file]
        if rev:
            blameArgs.insert(1, rev)

        return blameArgs

    def reset(self):
        super().reset()
        self._curLine = BlameLine()


class RevisionPanel(TextViewer):

    revisionActivated = Signal(BlameLine)

    def __init__(self, viewer):
        self._viewer = viewer
        self._revs = []

        super().__init__(viewer)

        self._activeRev = None
        self._sha1Pattern = re.compile(r"^[a-f0-9]{%s}" % ABBREV_N)

        self._hoveredLine = -1
        self._menu = None

        viewer.textLineClicked.connect(
            self._onTextLineClicked)
        self.textLineClicked.connect(
            self._onTextLineClicked)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)

        settings = qApp.settings()
        settings.diffViewFontChanged.connect(self.delayUpdateSettings)

    def toTextLine(self, text):
        textLine = super().toTextLine(text)
        textLine.useBuiltinPatterns = False
        textLine.setCustomLinkPatterns({Link.Sha1: self._sha1Pattern})
        return textLine

    def reloadSettings(self):
        self.updateFont(qApp.settings().diffViewFont())

        fm = QFontMetrics(self._font)
        self._sha1Width = fm.horizontalAdvance('a') * ABBREV_N
        self._dateWidth = fm.horizontalAdvance("2020-05-27")
        self._space = fm.horizontalAdvance(' ')
        self._digitWidth = fm.horizontalAdvance('9')
        self._maxNameWidth = 12 * fm.horizontalAdvance('W')

        width = self._sha1Width + self._space * 6
        width += self._dateWidth
        width += self._maxNameWidth
        width += self._digitWidth * 6
        self.resize(width, self._viewer.height())

    def appendRevisions(self, revs):
        texts = []
        for rev in revs:
            text = rev.sha1[:ABBREV_N]
            self._fix_rev(rev)
            if not self._revs or self._revs[len(self._revs) - 1].sha1 != rev.sha1:
                text += " " + rev.authorTime.split(" ")[0]
                text += " " + rev.author

            texts.append(text)
            self._revs.append(rev)

        self.appendLines(texts)
        self.update()

    def updateLinkData(self, link, lineNo):
        link.setData(self._revs[lineNo].sha1)

    def firstVisibleLine(self):
        return self._viewer.firstVisibleLine()

    @property
    def revisions(self):
        return self._revs

    def clear(self):
        super().clear()
        self._revs.clear()
        self._activeRev = None
        self.update()

    def getFileBySHA1(self, sha1):
        if not sha1:
            return None

        for rev in self._revs:
            if rev.filename and rev.sha1 == sha1:
                return rev.filename
            if rev.prevFileName and rev.previous == sha1:
                return rev.prevFileName
        return None

    def setActiveRevByLineNumber(self, lineNo):
        if lineNo >= 0 and lineNo < len(self._revs):
            self._updateActiveRev(lineNo)

    def _onTextLineClicked(self, textLine):
        self._updateActiveRev(textLine.lineNo())

    def _updateActiveRev(self, lineNo):
        rev = self._revs[lineNo]
        sha1 = rev.sha1
        if sha1 == self._activeRev:
            return

        self._activeRev = sha1

        lines = []
        for i in range(len(self._revs)):
            if self._revs[i].sha1 == sha1:
                lines.append(i)

        self._viewer.highlightLines(lines)
        self.update()

        self.revisionActivated.emit(rev)

    def _drawActiveRev(self, painter, lineNo, x, y):
        if self._activeRev and self._revs[lineNo].sha1 == self._activeRev:
            line = self.textLineAt(lineNo)
            br = line.boundingRect()
            fr = QRectF(br)
            fr.moveTop(fr.top() + y)
            fr.moveLeft(x)
            painter.fillRect(fr, QColor(192, 237, 197))

    def _reloadTextLine(self, textLine):
        textLine.setFont(self._font)

    def _fix_rev(self, rev):
        if rev.author:
            return
        for i in range(len(self._revs) - 1, -1, -1):
            r = self._revs[i]
            if r.sha1 == rev.sha1:
                rev.author = r.author
                rev.authorMail = r.authorMail
                rev.authorTime = r.authorTime
                rev.committer = r.committer
                rev.committerMail = r.committerMail
                rev.committerTime = r.committerTime
                rev.summary = r.summary
                rev.previous = r.previous
                rev.prevFileName = r.prevFileName
                rev.filename = r.filename
                break

    def _onMenuShowCommitLog(self):
        if self._hoveredLine == -1:
            return

        rev = self._revs[self._hoveredLine]
        event = ShowCommitEvent(rev.sha1)
        qApp.postEvent(qApp, event)

    def _onMenuBlamePrevCommit(self):
        if self._hoveredLine == -1:
            return

        rev = self._revs[self._hoveredLine]
        if rev.previous:
            pass

        file = self.getFileBySHA1(rev.previous)
        event = BlameEvent(file, rev.previous, rev.oldLineNo)
        qApp.postEvent(qApp, event)

    def paintEvent(self, event):
        painter = QPainter(self.viewport())

        eventRect = event.rect()
        painter.setClipRect(eventRect)
        painter.setFont(self._font)

        onePixel = dpiScaled(1)
        painter.fillRect(self.rect().adjusted(onePixel, onePixel, 0, 0),
                         QColor(250, 250, 250))

        y = 0
        width = self.width()

        textLineCount = self.textLineCount()
        digitCount = max(3, len(str(textLineCount)))
        x = width - digitCount * self._digitWidth - self._space * 2
        pen = QPen(Qt.darkGray)
        oldPen = painter.pen()
        painter.setPen(pen)
        painter.drawLine(x, y, x, self.height())
        painter.setPen(oldPen)

        maxLineWidth = x - self._space

        if not self.hasTextLines():
            return

        startLine = self.firstVisibleLine()
        ascent = QFontMetrics(self._font).ascent()

        for i in range(startLine, textLineCount):
            line = self.textLineAt(i)

            lineClipRect = QRectF(0, y, maxLineWidth, self._viewer.lineHeight)
            painter.save()
            painter.setClipRect(lineClipRect)

            self._drawActiveRev(painter, i, self._space, y)
            line.draw(painter, QPointF(self._space, y))

            painter.restore()

            lineNumber = str(i + 1)
            x = width - len(lineNumber) * self._digitWidth - self._space
            painter.setPen(pen)
            painter.drawText(x, y + ascent, lineNumber)
            painter.setPen(oldPen)

            y += self._viewer.lineHeight
            if y > self.height():
                break

    def contextMenuEvent(self, event):
        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return

        self._hoveredLine = textLine.lineNo()

        if not self._menu:
            self._menu = QMenu(self)
            self._menu.addAction(
                self.tr("Show commit log"),
                self._onMenuShowCommitLog)
            action = self._menu.addAction(
                self.tr("Blame previous commit"),
                self._onMenuBlamePrevCommit)
            self._acBlamePrevCommit = action

        rev = self._revs[self._hoveredLine]
        self._acBlamePrevCommit.setEnabled(rev.previous is not None)
        self._menu.exec_(event.globalPos())

    def update(self):
        self.viewport().update()
        super().update()


class BlameSourceViewer(SourceViewer):

    revisionActivated = Signal(BlameLine)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPanel(RevisionPanel(self))

        self._panel.revisionActivated.connect(
            self.revisionActivated)
        self._panel.linkActivated.connect(
            self.linkActivated)

        self._curIndexForMenu = -1
        self._preferEncoding = "utf-8"
        self._detected = False

    def clear(self):
        super().clear()
        self._panel.clear()
        self._detected = False

    def beginReading(self):
        super().beginReading()
        self._panel.beginReading()

    def endReading(self):
        super().endReading()
        self._panel.endReading()

    def toTextLine(self, data):
        if not self._detected:
            self._preferEncoding = self._detectEncoding(data)
            self._detected = True

        text, encoding = decodeFileData(data, self._preferEncoding)
        if encoding:
            self._preferEncoding = encoding
        return super().toTextLine(text)

    def createContextMenu(self):
        menu = super().createContextMenu()
        menu.addSeparator()
        menu.addAction(
            self.tr("Show commit log"),
            self._onMenuShowCommitLog)
        self._acBlamePrev = menu.addAction(
            self.tr("Blame previous commit"),
            self._onMenuBlamePrevCommit)
        return menu

    def updateContextMenu(self, pos):
        super().updateContextMenu(pos)

        enabled = False
        textLine = self.textLineForPos(pos)
        if textLine:
            self._curIndexForMenu = textLine.lineNo()
            rev = self._panel.revisions[textLine.lineNo()]
            enabled = rev.previous is not None
        else:
            self._curIndexForMenu = -1
        self._acBlamePrev.setEnabled(enabled)

    def appendBlameLines(self, lines):
        texts = []
        for line in lines:
            texts.append(line.text)
            # to save memory as revision panel no need text
            line.text = None

        self._panel.appendRevisions(lines)
        self.appendLines(texts)

    def _onMenuShowCommitLog(self):
        if self._curIndexForMenu == -1:
            return

        rev = self._panel.revisions[self._curIndexForMenu]
        event = ShowCommitEvent(rev.sha1)
        qApp.postEvent(qApp, event)

    def _onMenuBlamePrevCommit(self):
        if self._curIndexForMenu == -1:
            return

        rev = self._panel.revisions[self._curIndexForMenu]
        if rev.previous:
            pass

        file = self._panel.getFileBySHA1(rev.previous)
        event = BlameEvent(file, rev.previous, rev.oldLineNo)
        qApp.postEvent(qApp, event)

    def _lineRect(self, lineNo):
        firstLine = self.firstVisibleLine()
        if lineNo < firstLine:
            return QRect()
        if lineNo > firstLine + self._linesPerPage():
            return QRect()

        offset = self.contentOffset()
        offset.setY(offset.y() + (lineNo - firstLine) * self._lineHeight)

        textLine = self.textLineAt(self._cursor.beginLine())
        lineRect = textLine.boundingRect()
        lineRect.translate(offset)
        lineRect.setRight(self.viewport().rect().width()
                          - offset.x()
                          - dpiScaled(1))

        return lineRect.toRect()

    def _detectEncoding(self, data):
        if len(data) < 4:
            return "utf-8"

        b1 = data[0]
        b2 = data[1]
        b3 = data[2]
        b4 = data[3]
        if b1 == 0xFE and b2 == 0xFF:
            return "utf-16be"
        elif b1 == 0xFF and b2 == 0xFE:
            return "utf-16le"
        elif b1 == 0xEF and b2 == 0xBB and b3 == 0xBF:
            return "utf-8"
        elif b1 == 0x00 and b2 == 0x00 and b3 == 0xFE and b4 == 0xFF:
            return "utf-32be"
        elif b1 == 0xFF and b2 == 0xFE and b3 == 0x00 and b4 == 0x00:
            return "utf-32le"

        return "utf-8"

    def mousePressEvent(self, event):
        oldLine = self._cursor.beginLine()
        super().mousePressEvent(event)
        if not self._cursor.isValid():
            return
        if self._cursor.hasSelection():
            return

        newLine = self._cursor.endLine()
        if newLine == oldLine:
            return
        r = self._lineRect(oldLine)
        # if line contains invalid char
        # offset <= 2 is not working as the paintEvent rect
        # is not high enough for repaint
        # even if the update rect seems OK LoL
        offset = dpiScaled(3)
        self.viewport().update(r.adjusted(-offset, -offset, offset, offset))
        r = self._lineRect(newLine)
        offset = dpiScaled(1)
        self.viewport().update(r.adjusted(-offset, -offset, offset, offset))

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._cursor.isValid() and \
                not self._cursor.hasSelection():
            lineNo = self._cursor.beginLine()
            lineRect = self._lineRect(lineNo)
            if not lineRect.isValid():
                return

            painter = QPainter(self.viewport())
            painter.setPen(Qt.gray)
            painter.drawRect(lineRect)


class CommitPanel(TextViewer):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bodyCache = {}

        settings = qApp.settings()
        settings.diffViewFontChanged.connect(self.delayUpdateSettings)

    def showRevision(self, rev):
        super().clear()

        text = self.tr("Commit: ") + rev.sha1
        textLine = LinkTextLine(text, self._font, Link.Sha1)
        self.appendTextLine(textLine)

        text = self.tr("Author: ") + rev.author + " " + \
            rev.authorMail + " " + rev.authorTime
        textLine = LinkTextLine(text, self._font, Link.Email)
        self.appendTextLine(textLine)

        text = self.tr("Committer: ") + rev.committer + " " + \
            rev.committerMail + " " + rev.committerTime
        textLine = LinkTextLine(text, self._font, Link.Email)
        self.appendTextLine(textLine)

        if rev.previous:
            text = self.tr("Previous: ") + rev.previous
            textLine = LinkTextLine(text, self._font, Link.Sha1)
            self.appendTextLine(textLine)

        self.appendLine("")
        self.appendLine(rev.summary)

        if rev.sha1 in self._bodyCache:
            text = self._bodyCache[rev.sha1]
        else:
            args = ["show", "-s", "--pretty=format:%b", rev.sha1]
            data = Git.checkOutput(args)
            text = _decode(data) if data else None
            self._bodyCache[rev.sha1] = text
        if text:
            self.appendLine("")
            text = text.rstrip('\n')
            for line in text.split('\n'):
                self.appendLine(line)

    def clear(self):
        super().clear()
        self._bodyCache.clear()

    def reloadSettings(self):
        super().reloadSettings()
        self.updateFont(qApp.settings().diffViewFont())

    def _reloadTextLine(self, textLine):
        super()._reloadTextLine(textLine)
        textLine.setFont(self._font)


class HeaderWidget(QWidget):

    def __init__(self, view=None):
        super().__init__(view)

        self._view = view
        self._histories = []
        self._curIndex = 0
        self._blockAdd = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btnPrev = QToolButton(self)
        layout.addWidget(self._btnPrev)

        self._btnNext = QToolButton(self)
        layout.addWidget(self._btnNext)

        self._waitingSpinner = QtWaitingSpinner(self)
        layout.addWidget(self._waitingSpinner)

        self._lbFile = QLabel(self)
        layout.addWidget(self._lbFile)

        self._lbRev = QLabel(self)
        layout.addWidget(self._lbRev)
        layout.addSpacerItem(QSpacerItem(
            0, 0,
            QSizePolicy.Expanding,
            QSizePolicy.Fixed))

        self._btnPrev.setText("🡰")
        self._btnNext.setText("🡲")

        self._btnPrev.clicked.connect(
            self._onPrevious)
        self._btnNext.clicked.connect(
            self._onNext)

        height = self._lbFile.height() // 6
        self._waitingSpinner.setLineLength(height)
        self._waitingSpinner.setInnerRadius(height)
        self._waitingSpinner.setNumberOfLines(14)

        self._updateInfo()

    def _updateInfo(self):
        if not self._histories:
            file = ""
            rev = ""
        else:
            file, rev = self._histories[self._curIndex]
            if rev is None:
                rev = ""

        self._lbRev.setText(rev)
        self._lbFile.setText(file)

        enablePrev = False
        enableNext = False

        total = len(self._histories)
        if total > 1:
            if self._curIndex != 0:
                enablePrev = True
            if self._curIndex != total - 1:
                enableNext = True
        self._btnPrev.setEnabled(enablePrev)
        self._btnNext.setEnabled(enableNext)

    def _blameCurrent(self):
        self._blockAdd = True
        file, rev = self._histories[self._curIndex]
        self._view.blame(file, rev)
        self._blockAdd = False

    def _onPrevious(self):
        self._curIndex -= 1
        self._updateInfo()
        self._blameCurrent()

    def _onNext(self):
        self._curIndex += 1
        self._updateInfo()
        self._blameCurrent()

    def clear(self):
        self._histories.clear()
        self._updateInfo()

    def addBlameInfo(self, file, rev):
        if self._blockAdd:
            return

        index = -1
        for i in range(len(self._histories)):
            f, r = self._histories[i]
            if file == f and rev == r:
                index = i
                break

        if index != -1:
            self._curIndex = index
        else:
            self._curIndex += 1
            self._histories.insert(self._curIndex, (file, rev))
            if self._curIndex >= len(self._histories):
                self._curIndex = len(self._histories) - 1

        self._updateInfo()

    def notifyFecthingStarted(self):
        self._waitingSpinner.start()

    def notifyFecthingFinished(self):
        self._waitingSpinner.stop()


class BlameView(QWidget):

    blameFileAboutToChange = Signal(str)
    blameFileChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        mainLayout = QVBoxLayout(self)
        mainLayout.setMargin(0)

        sourceWidget = QWidget(self)
        layout = QVBoxLayout(sourceWidget)
        layout.setMargin(0)

        self._headerWidget = HeaderWidget(self)
        layout.addWidget(self._headerWidget)

        self._viewer = BlameSourceViewer(self)
        layout.addWidget(self._viewer)

        self._commitPanel = CommitPanel(self)

        vSplitter = QSplitter(Qt.Vertical, self)
        vSplitter.addWidget(sourceWidget)
        vSplitter.addWidget(self._commitPanel)

        height = vSplitter.sizeHint().height()
        sizes = [height * 4 / 5, height * 1 / 5]
        vSplitter.setSizes(sizes)

        mainLayout.addWidget(vSplitter)

        self._file = None
        self._rev = None
        self._lineNo = -1

        self._fetcher = BlameFetcher(self)
        self._fetcher.dataAvailable.connect(
            self._onFetchDataAvailable)
        self._fetcher.fetchFinished.connect(
            self._onFetchFinished)

        self._commitPanel.linkActivated.connect(
            self._onLinkActivated)
        self._viewer.linkActivated.connect(
            self._onLinkActivated)
        self._viewer.revisionActivated.connect(
            self._commitPanel.showRevision)

    def _onLinkActivated(self, link):
        if link.type == Link.Sha1:
            if self._rev != link.data:
                file = self._findFileBySHA1(link.data)
                self.blame(file, link.data)
        else:
            qApp.postEvent(qApp, OpenLinkEvent(link))

    def _onFetchDataAvailable(self, lines):
        self._viewer.appendBlameLines(lines)

    def _onFetchFinished(self, exitCode):
        self.blameFileChanged.emit(self._file)
        self._headerWidget.notifyFecthingFinished()
        if self._lineNo > 0:
            self._viewer.gotoLine(self._lineNo - 1)
            self._viewer.panel.setActiveRevByLineNumber(self._lineNo - 1)
            self._lineNo = -1
        self._viewer.endReading()
        if not self._viewer.hasTextLines() and self._fetcher.errorData:
            QMessageBox.critical(self, self.window().windowTitle(),
                                 self._fetcher.errorData.decode("utf-8"))

    def _findFileBySHA1(self, sha1):
        file = self._viewer.panel.getFileBySHA1(sha1)
        return file if file else self._file

    def clear(self):
        self._viewer.clear()
        self._commitPanel.clear()

    def blame(self, file, rev=None, lineNo=0):
        if self._file == file and self._rev == rev:
            return

        self._headerWidget.notifyFecthingStarted()
        self.blameFileAboutToChange.emit(file)
        self.clear()
        self._viewer.beginReading()
        self._fetcher.fetch(file, rev)

        self._file = file
        self._rev = rev
        self._lineNo = lineNo

        self._headerWidget.addBlameInfo(file, rev)

    @property
    def viewer(self):
        return self._viewer

    @property
    def commitPanel(self):
        return self._commitPanel
