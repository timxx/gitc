# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QMenu,
    QScrollBar)
from PySide6.QtGui import (
    QPainter,
    QFontMetrics,
    QTextCharFormat,
    QTextOption,
    QBrush,
    QColor,
    QKeySequence,
    QIcon)
from PySide6.QtCore import (
    Qt,
    QRect,
    QRectF,
    QPoint,
    QPointF,
    Signal,
    QElapsedTimer,
    QTimer,
    QMimeData)

from .textline import (
    TextLine,
    createFormatRange,
    Link)
from .colorschema import ColorSchema
from .textcursor import TextCursor

import re
import bisect


__all__ = ["TextViewer", "FindFlags", "FindPart"]


class FindFlags:

    Backward = 0x01
    CaseSenitively = 0x02
    WholeWords = 0x04
    UseRegExp = 0x08


class FindPart:

    BeforeCurPage = 0
    CurrentPage = 1
    AfterCurPage = 2
    All = 3


class TextViewer(QAbstractScrollArea):

    textLineClicked = Signal(TextLine)
    linkActivated = Signal(Link)
    findResultAvailable = Signal(list, int)
    findFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # raw text lines
        self._lines = None
        # TextLine instances
        self._textLines = {}
        self._inReading = False

        self._convertIndex = 0
        self._convertTimerId = None

        self._option = QTextOption()
        self._option.setWrapMode(QTextOption.NoWrap)

        self.reloadSettings()

        self._maxWidth = 0
        self._highlightLines = []
        self._highlightFind = []

        self._cursor = TextCursor(self)
        self._clickTimer = QElapsedTimer()

        self.viewport().setMouseTracking(True)

        self._clickOnLink = False
        self._link = None

        self._contextMenu = None

        self._findTimerId = None
        self._findIndex = 0
        self._findPattern = None
        self._findCurPageRange = None

        self._settingsTimer = None
        qApp.settings().bugPatternChanged.connect(
            self.delayUpdateSettings)
        qApp.settings().fallbackGlobalChanged.connect(
            self.delayUpdateSettings)

    def updateFont(self, font):
        self._font = font
        fm = QFontMetrics(self._font)
        self._lineHeight = fm.height()

    def reloadSettings(self):
        self.updateFont(self.font())
        self.reloadBugPattern()

    def reloadBugPattern(self):
        repoName = qApp.repoName()
        sett = qApp.settings()
        pattern = sett.bugPattern(repoName)
        globalPattern = sett.bugPattern(
            None) if sett.fallbackGlobalLinks(repoName) else None

        self._bugPattern = None
        if pattern == globalPattern:
            if pattern:
                self._bugPattern = re.compile(pattern)
        elif pattern and globalPattern:
            self._bugPattern = re.compile(pattern + '|' + globalPattern)
        elif pattern:
            self._bugPattern = re.compile(pattern)
        elif globalPattern:
            self._bugPattern = re.compile(globalPattern)

    def toTextLine(self, text):
        return TextLine(text, self._font, self._option)

    def initTextLine(self, textLine, lineNo):
        textLine.setLineNo(lineNo)
        if textLine.useBuiltinPatterns and self._bugPattern:
            patterns = {Link.BugId: self._bugPattern}
            textLine.setCustomLinkPatterns(patterns)

    def appendLine(self, line):
        self.appendLines([line])

    def appendLines(self, lines):
        if self._lines:
            self._lines.extend(lines)
        elif self._inReading:
            self._lines = lines
        else:
            for line in lines:
                textLine = self.toTextLine(line)
                self.appendTextLine(textLine)

        if self._convertTimerId is None:
            self._convertTimerId = self.startTimer(0)

        self.viewport().update()

    def appendTextLine(self, textLine):
        lineNo = self.textLineCount()
        self.initTextLine(textLine, lineNo)
        if self._lines is None:
            self._lines = []
        self._lines.append(None)
        self._textLines[lineNo] = textLine

        if self._convertTimerId is None:
            self._convertTimerId = self.startTimer(0)

        self.viewport().update()

    def beginReading(self):
        """ Call before reading lines to TextViewer """
        self._inReading = True

    def endReading(self):
        """ Call after reading finished """
        self._inReading = False
        if self._lines and \
                len(self._lines) == len(self._textLines):
            self._lines = None

    def clear(self):
        self._lines = None
        self._textLines.clear()
        self._inReading = False
        self._maxWidth = 0
        self._highlightLines.clear()
        self._cursor.clear()
        self._clickOnLink = False
        self._link = None

        self._convertIndex = 0
        if self._convertTimerId is not None:
            self.killTimer(self._convertTimerId)
            self._convertTimerId = None

        self.cancelFind()

        if self._settingsTimer is not None:
            if self._settingsTimer.isActive():
                self.reloadSettings()
            self._settingsTimer.stop()
            self._settingsTimer = None

        self._adjustScrollbars()
        self.viewport().setCursor(Qt.IBeamCursor)
        self.viewport().update()

    def hasTextLines(self):
        return self.textLineCount() > 0

    def textLineCount(self):
        if self._lines:
            return len(self._lines)

        return len(self._textLines)

    def textLineAt(self, n):
        if n < 0:
            return None

        # n already converted
        if n in self._textLines:
            return self._textLines[n]

        # all converted but no match
        if not self._lines:
            return None

        # convert one
        if n >= len(self._lines):
            return None

        textLine = self.toTextLine(self._lines[n])
        self.initTextLine(textLine, n)

        self._textLines[n] = textLine
        # free the memory
        self._lines[n] = None
        if not self._inReading and \
                len(self._lines) == len(self._textLines):
            self._lines = None

        return textLine

    def firstVisibleLine(self):
        return self.verticalScrollBar().value()

    @property
    def currentLineNo(self):
        return self.firstVisibleLine()

    def gotoLine(self, lineNo, centralOnView=True):
        if lineNo < 0 or lineNo >= self.textLineCount():
            return

        self._cursor.moveTo(lineNo, 0)

        # central the lineNo in view
        if centralOnView:
            halfOfPage = self._linesPerPage() // 2
            if lineNo > halfOfPage:
                lineNo -= halfOfPage

        vScrollBar = self.verticalScrollBar()
        if vScrollBar.value() != lineNo:
            vScrollBar.setValue(lineNo)
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

    @property
    def lineHeight(self):
        return self._lineHeight

    def textRowForPos(self, pos):
        if not self.hasTextLines():
            return -1

        y = max(0, pos.y())
        n = int(y / self.lineHeight)
        n += self.firstVisibleLine()

        if n >= self.textLineCount():
            n = self.textLineCount() - 1

        return n

    def textLineForPos(self, pos):
        n = self.textRowForPos(pos)
        if n == -1:
            return None
        return self.textLineAt(n)

    def highlightLines(self, lines):
        self._highlightLines = lines

        self.viewport().update()

    def highlightFindResult(self, result, findPart=FindPart.All):
        if not result:
            self._highlightFind.clear()
        elif findPart in [FindPart.CurrentPage, FindPart.All]:
            self._highlightFind = result[:]
        elif findPart == FindPart.BeforeCurPage:
            low = bisect.bisect_left(self._highlightFind, result[0])
            # FIXME: how to improve performance?
            for i in range(0, len(result)):
                self._highlightFind.insert(low + i, result[i])
        else:
            self._highlightFind.extend(result)

        needUpdate = True
        if result:
            firstVisibleLine = self.firstVisibleLine()
            lastVisibleLine = firstVisibleLine + self._linesPerPage()
            firstLine = result[0].beginLine()
            lastLine = result[-1].endLine()
            if firstLine > lastVisibleLine or lastLine < firstVisibleLine:
                needUpdate = False
        if needUpdate:
            self.viewport().update()

    def selectAll(self):
        if not self.hasTextLines():
            return

        self._cursor.moveTo(0, 0)
        lastLine = self.textLineCount() - 1
        self._cursor.selectTo(lastLine, len(self.textLineAt(lastLine).text()))
        self._invalidateSelection()

    def select(self, cursor):
        if not cursor.isValid():
            return

        self._cursor.moveTo(cursor.beginLine(), cursor.beginPos())
        self._cursor.selectTo(cursor.endLine(), cursor.endPos())
        self.ensureCursorVisible()
        self.viewport().update()

    def ensureCursorVisible(self, lineOnly=False):
        if not self.hasTextLines():
            return
        if not self._cursor.isValid():
            return

        startLine = self.firstVisibleLine()
        endLine = startLine + self._linesPerPage()
        endLine = min(self.textLineCount(), endLine)

        lineNo = self._cursor.beginLine()
        if lineNo < startLine or lineNo >= endLine:
            halfOfPage = self._linesPerPage() // 2
            if lineNo > halfOfPage:
                lineNo -= halfOfPage
            self.verticalScrollBar().setValue(lineNo)

        if lineOnly:
            return

        hbar = self.horizontalScrollBar()

        start = self._cursor.beginPos()
        end = self._cursor.endPos()
        if start > end:
            start, end = end, start

        textLine = self.textLineAt(lineNo)
        x1 = textLine.offsetToX(start)
        x2 = textLine.offsetToX(end)

        viewWidth = self.viewport().width()
        offset = hbar.value()

        if x1 < offset or x2 > (offset + viewWidth):
            hbar.setValue(x1)

    def findAll(self, text, flags=0):
        if not text or not self.hasTextLines():
            return []

        pattern = self._toFindPattern(text, flags)
        return self._findInRange(pattern, 0, self.textLineCount())

    def findAllAsync(self, text, flags=0):
        """ Find text in idle.
        False returned if search done without starting idle
        """

        if not text or not self.hasTextLines():
            return False

        self.cancelFind()

        # Always find current visible page first
        begin = self.firstVisibleLine()
        end = self._linesPerPage() + begin
        if end >= self.textLineCount():
            end = self.textLineCount()

        pattern = self._toFindPattern(text, flags)
        result = self._findInRange(pattern, begin, end)

        if result:
            self.findResultAvailable.emit(result, FindPart.CurrentPage)

        # no more lines
        if begin == 0 and end == self.textLineCount():
            return False

        self._findPattern = pattern
        self._findCurPageRange = (begin, end - 1)
        self._findIndex = end  # search from next page
        self._findTimerId = self.startTimer(0)

        return True

    def cancelFind(self):
        if self._findTimerId is not None:
            self.killTimer(self._findTimerId)
            self._findTimerId = None
            self._findPattern = None
            self.findFinished.emit()

    @property
    def selectedText(self):
        return self._cursor.selectedText()

    def copy(self):
        text = self._cursor.selectedText()
        if not text:
            return

        clipboard = QApplication.clipboard()
        mimeData = QMimeData()
        mimeData.setText(text)
        clipboard.setMimeData(mimeData)

    @property
    def textCursor(self):
        return self._cursor

    def updateLinkData(self, link, lineNo):
        """ Implement in subclass"""
        pass

    def createContextMenu(self):
        menu = QMenu(self)
        self._acCopy = menu.addAction(
            self.tr("&Copy"),
            self.copy,
            QKeySequence("Ctrl+C"))
        self._acCopy.setIcon(QIcon.fromTheme("edit-copy"))
        menu.addSeparator()
        self._acSelectAll = menu.addAction(
            self.tr("Select &All"),
            self.selectAll,
            QKeySequence("Ctrl+A"))
        self._acSelectAll.setIcon(QIcon.fromTheme("edit-select-all"))

        return menu

    @property
    def contextMenu(self):
        if not self._contextMenu:
            self._contextMenu = self.createContextMenu()
        return self._contextMenu

    def updateContextMenu(self, pos):
        self._acCopy.setEnabled(self._cursor.hasSelection())

    def drawLineBackground(self, painter, textLine, lineRect):
        pass

    def textLineFormatRange(self, textLine):
        return None

    def delayUpdateSettings(self):
        if self._settingsTimer:
            # restart
            self._settingsTimer.start(10)
        else:
            self._settingsTimer = QTimer(self)
            self._settingsTimer.timeout.connect(
                self._onUpdateSettings)
            self._settingsTimer.setSingleShot(True)
            self._settingsTimer.start(10)

    def _linesPerPage(self):
        return int(self.viewport().height() / self._lineHeight)

    def _adjustScrollbars(self):
        vScrollBar = self.verticalScrollBar()
        hScrollBar = self.horizontalScrollBar()
        if not self.hasTextLines():
            vScrollBar.setRange(0, 0)
            hScrollBar.setRange(0, 0)
            return

        hScrollBar.setRange(0, self._maxWidth - self.viewport().width())
        hScrollBar.setPageStep(self.viewport().width())

        linesPerPage = self._linesPerPage()
        totalLines = self.textLineCount()

        vScrollBar.setRange(0, totalLines - linesPerPage)
        vScrollBar.setPageStep(linesPerPage)

    def _invalidateSelection(self):
        if not self._cursor.hasSelection():
            return

        begin = self._cursor.beginLine()
        end = self._cursor.endLine()

        x = 0
        y = (begin - self.firstVisibleLine()) * self.lineHeight
        w = self.viewport().width()
        h = (end - begin + 1) * self.lineHeight

        rect = QRect(x, y, w, h)
        # offset for some odd fonts LoL
        offset = int(self.lineHeight / 2)
        rect.adjust(0, -offset, 0, offset)
        self.viewport().update(rect)

    def _selectionFormatRange(self, lineIndex):
        if not self._cursor.within(lineIndex):
            return None

        textLine = self.textLineAt(lineIndex)
        start = 0
        end = len(textLine.text())

        if self._cursor.beginLine() == lineIndex:
            start = self._cursor.beginPos()
        if self._cursor.endLine() == lineIndex:
            end = self._cursor.endPos()

        # select the new line if multiple lines selected
        if lineIndex < self._cursor.endLine():
            end += 1

        fmt = QTextCharFormat()

        def _hasFocus():
            if qApp.applicationState() != Qt.ApplicationActive:
                return False
            if self.hasFocus():
                return True
            fw = qApp.focusWidget()
            return fw and self.isAncestorOf(fw)

        if _hasFocus():
            fmt.setBackground(QBrush(ColorSchema.SelFocus))
        else:
            fmt.setBackground(QBrush(ColorSchema.SelNoFocus))

        return createFormatRange(start, end - start, fmt)

    def _findResultFormatRange(self, lineIndex, endLine):
        if not self._highlightFind:
            return None

        key = TextCursor()
        key.moveTo(lineIndex, 0)
        low = bisect.bisect_left(self._highlightFind, key)
        if low >= len(self._highlightFind):
            return None
        if self._highlightFind[low].beginLine() > lineIndex:
            return None

        result = []
        fmt = QTextCharFormat()
        fmt.setBackground(ColorSchema.FindResult)

        for i in range(low, len(self._highlightFind)):
            r = self._highlightFind[i]
            if r.beginLine() == lineIndex:
                rg = createFormatRange(r.beginPos(), r.endPos() - r.beginPos(), fmt)
                result.append(rg)
            elif r.beginLine() > lineIndex or r.beginLine() > endLine:
                break

        return result

    def _isLetter(self, char):
        if char >= 'a' and char <= 'z':
            return True
        if char >= 'A' and char <= 'Z':
            return True

        if char == '_':
            return True

        if char.isdigit():
            return True

        return False

    def _reloadTextLine(self, textLine):
        if textLine.useBuiltinPatterns:
            pattern = None
            if self._bugPattern:
                pattern = {Link.BugId: self._bugPattern}
            textLine.setCustomLinkPatterns(pattern)

    def _toFindPattern(self, text, flags):
        exp = text
        exp_flags = re.IGNORECASE

        if not (flags & FindFlags.UseRegExp):
            exp = re.escape(text)
        if flags & FindFlags.CaseSenitively:
            exp_flags = 0
        if flags & FindFlags.WholeWords:
            exp = r'\b' + text + r'\b'

        return re.compile(exp, exp_flags)

    def _findInRange(self, pattern, low, high):
        result = []
        for i in range(low, high):
            text = self.textLineAt(i).text()
            if not text:
                continue

            iter = pattern.finditer(text)
            for m in iter:
                tc = TextCursor()
                tc.moveTo(i, m.start())
                tc.selectTo(i, m.end())
                result.append(tc)

        return result

    def _onConvertEvent(self):
        # wait for more text lines
        if self._inReading and self._convertIndex >= self.textLineCount():
            return

        textLine = self.textLineAt(self._convertIndex)
        self._convertIndex += 1

        if not self._inReading and self._convertIndex >= self.textLineCount():
            self.killTimer(self._convertTimerId)
            self._convertTimerId = None
            self._convertIndex = 0

        maximum = self.textLineCount() - self._linesPerPage()
        needAdjust = self.verticalScrollBar().maximum() < maximum
        if textLine:
            width = textLine.boundingRect().width()
            if width > self._maxWidth:
                self._maxWidth = width
                needAdjust = True

        if needAdjust:
            self._adjustScrollbars()
            self.ensureCursorVisible(True)

    def _onUpdateSettings(self):
        self.reloadSettings()

        if self._settingsTimer:
            self._settingsTimer.disconnect(self)
            self._settingsTimer = None

        # TODO: move to background
        for _, line in self._textLines.items():
            self._reloadTextLine(line)

        self._adjustScrollbars()
        self.viewport().update()

    def _onFindEvent(self):
        low, high = self._findCurPageRange
        if self._findIndex > high:
            findPart = FindPart.AfterCurPage
            # Search from beginning
            if self._findIndex == self.textLineCount():
                self._findIndex = 0
                findPart = FindPart.BeforeCurPage
        else:
            findPart = FindPart.BeforeCurPage

        assert(self._findIndex < low or high < self._findIndex)

        begin = self._findIndex
        end = begin + 1000
        pattern = self._findPattern
        if findPart == FindPart.AfterCurPage:
            if end >= self.textLineCount():
                end = self.textLineCount()
        else:
            if end >= low:
                end = low

        self._findIndex = end

        result = self._findInRange(pattern, begin, end)
        if result:
            self.findResultAvailable.emit(result, findPart)

        if findPart == FindPart.AfterCurPage:
            if low == 0 and self._findIndex == self.textLineCount():
                self.cancelFind()
        else:
            if self._findIndex == low:
                self.cancelFind()

    def paintEvent(self, event):
        if not self.hasTextLines():
            return

        painter = QPainter(self.viewport())
        eventRect = event.rect()

        if eventRect.isValid():
            startLine = self.textRowForPos(eventRect.topLeft())
            endLine = self.textRowForPos(eventRect.bottomRight()) + 1
        else:
            startLine = self.firstVisibleLine()
            endLine = startLine + self._linesPerPage() + 1
        endLine = min(self.textLineCount(), endLine)

        offset = self.contentOffset()
        offset.setY(offset.y() + (startLine -
                                  self.firstVisibleLine()) * self.lineHeight)
        viewportRect = self.viewport().rect()

        painter.setClipRect(eventRect)

        for i in range(startLine, endLine):
            textLine = self.textLineAt(i)

            br = textLine.boundingRect()
            r = br.translated(offset)

            def lineRect():
                fr = QRectF(br)
                fr.moveTop(fr.top() + r.top())
                fr.setLeft(0)
                fr.setRight(viewportRect.width() - offset.x())
                return fr

            if i in self._highlightLines:
                painter.fillRect(lineRect(), QColor(192, 237, 197))
            else:
                self.drawLineBackground(painter, textLine, lineRect())

            formats = []

            # find result
            findRg = self._findResultFormatRange(i, endLine)
            if findRg:
                formats.extend(findRg)

            # TextLine format
            textLineRg = self.textLineFormatRange(textLine)
            if textLineRg:
                formats.extend(textLineRg)

            # selection
            selectionRg = self._selectionFormatRange(i)
            if selectionRg:
                formats.append(selectionRg)

            textLine.draw(painter, offset, formats, QRectF(eventRect))

            offset.setY(offset.y() + self._lineHeight)

            if offset.y() > viewportRect.height():
                break

    def resizeEvent(self, event):
        self._adjustScrollbars()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if not self.hasTextLines():
            return

        self._clickOnLink = self._link is not None
        self._invalidateSelection()

        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return

        tripleClick = False
        if self._clickTimer.isValid():
            tripleClick = not self._clickTimer.hasExpired(
                QApplication.doubleClickInterval())
            self._clickTimer.invalidate()

        if tripleClick:
            self._cursor.moveTo(textLine.lineNo(), 0)
            self._cursor.selectTo(textLine.lineNo(), len(textLine.text()))
            self._invalidateSelection()
        else:
            offset = textLine.offsetForPos(self.mapToContents(event.pos()))
            self._cursor.moveTo(textLine.lineNo(), offset)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        if self._link and self._clickOnLink:
            self.linkActivated.emit(self._link)

        self._clickOnLink = False
        if not self.hasTextLines() or \
            self._cursor.hasSelection():
            return

        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return

        self.textLineClicked.emit(textLine)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if not self.hasTextLines():
            return

        self._clickTimer.restart()
        self._invalidateSelection()
        self._cursor.clear()

        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return

        offset = textLine.offsetForPos(self.mapToContents(event.pos()))
        begin = offset
        end = offset

        # find the word
        content = textLine.text()
        if offset < len(content) and self._isLetter(content[offset]):
            for i in range(offset - 1, -1, -1):
                if self._isLetter(content[i]):
                    begin = i
                    continue
                break

            for i in range(offset + 1, len(content)):
                if self._isLetter(content[i]):
                    end = i
                    continue
                break

        end += 1
        word = content[begin:end]
        if word:
            self._cursor.moveTo(textLine.lineNo(), begin)
            self._cursor.selectTo(textLine.lineNo(), end)
            self._invalidateSelection()

    def mouseMoveEvent(self, event):
        if self._clickTimer.isValid():
            self._clickTimer.invalidate()

        self._clickOnLink = False
        self._link = None
        if not self.hasTextLines():
            return

        textLine = self.textLineForPos(event.pos())
        if not textLine:
            return

        offset = textLine.offsetForPos(self.mapToContents(event.pos()))
        if event.buttons() == Qt.LeftButton:
            self._invalidateSelection()

            n = textLine.lineNo()
            self._cursor.selectTo(n, offset)

            self._invalidateSelection()
        elif event.buttons() == Qt.NoButton:
            x = event.pos().x() + self.horizontalScrollBar().value()
            if textLine.boundingRect().right() >= x:
                self._link = textLine.hitTest(offset)
                if self._link:
                    self.updateLinkData(self._link, textLine.lineNo())

        cursorShape = Qt.PointingHandCursor if self._link \
            else Qt.IBeamCursor
        self.viewport().setCursor(cursorShape)

    def contextMenuEvent(self, event):
        menu = self.contextMenu
        self.updateContextMenu(event.pos())
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy()
        elif event.matches(QKeySequence.SelectAll):
            self.selectAll()
        elif event.matches(QKeySequence.MoveToStartOfDocument):
            self.verticalScrollBar().triggerAction(
                QScrollBar.SliderToMinimum)
        elif event.matches(QKeySequence.MoveToEndOfDocument):
            self.verticalScrollBar().triggerAction(
                QScrollBar.SliderToMaximum)
        elif event.matches(QKeySequence.MoveToPreviousPage):
            self.verticalScrollBar().triggerAction(
                QScrollBar.SliderPageStepSub)
        elif event.matches(QKeySequence.MoveToNextPage):
            self.verticalScrollBar().triggerAction(
                QScrollBar.SliderPageStepAdd)
        else:
            super().keyPressEvent(event)

    def timerEvent(self, event):
        id = event.timerId()
        if id == self._convertTimerId:
            self._onConvertEvent()
        elif id == self._findTimerId:
            self._onFindEvent()
