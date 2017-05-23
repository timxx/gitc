# -*- coding: utf-8 -*-

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from common import *
from git import *

import re
import bisect

# for refs
TAG_COLORS = [Qt.yellow,
              Qt.green,
              QColor(255, 221, 170)]

# for circles
GRAPH_COLORS = [Qt.black,
                Qt.red,
                Qt.green,
                Qt.blue,
                Qt.darkGray,
                QColor(150, 75, 0),  # brown
                Qt.magenta,
                QColor(255, 160, 50)  # orange
                ]


class CommitFetcher():

    def __init__(self):
        self.items = []
        self.source = None
        self.loadedCount = 0

    def __len__(self):
        return self.count()

    def __getitem__(self, index):
        return self.data(index)

    def __ensureCommit(self, index):
        if not self.source or self.items[index]:
            return

        commit = Commit()
        commit.parseRawString(self.source[index])
        self.items[index] = commit
        self.loadedCount += 1

        # no need the source
        if self.loadedCount == len(self.source):
            self.source = None

    def count(self):
        return len(self.items)

    def data(self, index):
        if index < 0 or index >= self.count():
            return None

        self.__ensureCommit(index)
        return self.items[index]

    def setSource(self, source):
        self.source = source
        self.items.clear()
        self.loadedCount = 0
        if source:
            self.items = [None for i in range(len(source))]

    def findCommitIndex(self, sha1, begin=0, findNext=True):
        index = -1

        findRange = range(begin, len(self.items)) \
            if findNext else range(begin, -1, -1)
        for i in findRange:
            self.__ensureCommit(i)
            item = self.items[i]
            if item.sha1.startswith(sha1):
                index = i
                break

        return index


class Marker():
    CHAR_MARK = chr(0x2713)

    def __init__(self):
        self._begin = -1
        self._end = -1

    def mark(self, begin, end):
        self._begin = min(begin, end)
        self._end = max(begin, end)

    def clear(self):
        self._begin = -1
        self._end = -1

    def hasMark(self):
        return self._begin != -1 and \
            self._end != -1

    def begin(self):
        return self._begin

    def end(self):
        return self._end

    def isMarked(self, index):
        return self.hasMark() and \
            self._begin <= index and \
            self._end >= index

    def draw(self, index, painter, rect):
        if not self.isMarked(index):
            return

        painter.save()

        painter.setPen(Qt.red)
        br = painter.drawText(rect, Qt.AlignVCenter, Marker.CHAR_MARK)
        rect.adjust(br.width(), 0, 0, 0)

        painter.restore()


# reference to QGit source code
class Lane():
    EMPTY = 0
    ACTIVE = 1
    NOT_ACTIVE = 2
    MERGE_FORK = 3
    MERGE_FORK_R = 4
    MERGE_FORK_L = 5
    JOIN = 6
    JOIN_R = 7
    JOIN_L = 8
    HEAD = 9
    HEAD_R = 10
    HEAD_L = 11
    TAIL = 12
    TAIL_R = 13
    TAIL_L = 14
    CROSS = 15
    CROSS_EMPTY = 16
    INITIAL = 17
    BRANCH = 18
    BOUNDARY = 19
    BOUNDARY_C = 20
    BOUNDARY_R = 21
    BOUNDARY_L = 22
    UNAPPLIED = 23
    APPLIED = 24

    @staticmethod
    def isHead(t):
        return t >= Lane.HEAD and \
            t <= Lane.HEAD_L

    @staticmethod
    def isTail(t):
        return t >= Lane.TAIL and \
            t <= Lane.TAIL_L

    @staticmethod
    def isJoin(t):
        return t >= Lane.JOIN and \
            t <= Lane.JOIN_L

    @staticmethod
    def isFreeLane(t):
        return t == Lane.NOT_ACTIVE or \
            t == Lane.CROSS or \
            Lane.isJoin(t)

    @staticmethod
    def isBoundary(t):
        return t >= Lane.BOUNDARY and \
            t <= Lane.BOUNDARY_L

    @staticmethod
    def isMerge(t):
        return (t >= Lane.MERGE_FORK and
                t <= Lane.MERGE_FORK_L) or \
            Lane.isBoundary(t)

    @staticmethod
    def isActive(t):
        return t == Lane.ACTIVE or \
            t == Lane.INITIAL or \
            t == Lane.BRANCH or \
            Lane.isMerge(t)


class Lanes():

    def __init__(self):
        self.activeLane = 0
        self.types = []
        self.nextSha = []
        self.isBoundary = False
        self.node = 0
        self.node_l = 0
        self.node_r = 0

    def isEmpty(self):
        return not self.types

    def isFork(self, sha1):
        pos = self.findNextSha1(sha1, 0)
        isDiscontinuity = self.activeLane != pos
        if pos == -1:  # new branch case
            return False, isDiscontinuity

        isFork = self.findNextSha1(sha1, pos + 1) != -1
        return isFork, isDiscontinuity

    def isBranch(self):
        return self.types[self.activeLane] == Lane.BRANCH

    def isNode(self, t):
        return t == self.node or \
            t == self.node_r or \
            t == self.node_l

    def findNextSha1(self, next, pos):
        for i in range(pos, len(self.nextSha)):
            if self.nextSha[i] == next:
                return i

        return -1

    def init(self, sha1):
        self.clear()
        self.activeLane = 0
        self.setBoundary(False)
        self.add(Lane.BRANCH, sha1, self.activeLane)

    def clear(self):
        self.types.clear()
        self.nextSha.clear()

    def setBoundary(self, b):
        if b:
            self.node = Lane.BOUNDARY_C
            self.node_r = Lane.BOUNDARY_R
            self.node_l = Lane.BOUNDARY_L
            self.types[self.activeLane] = Lane.BOUNDARY
        else:
            self.node = Lane.MERGE_FORK
            self.node_r = Lane.MERGE_FORK_R
            self.node_l = Lane.MERGE_FORK_L

        self.isBoundary = b

    def findType(self, type, pos):
        for i in range(pos, len(self.types)):
            if self.types[i] == type:
                return i
        return -1

    def add(self, type, next, pos):
        if pos < len(self.types):
            pos = self.findType(Lane.EMPTY, pos)
            if pos != -1:
                self.types[pos] = type
                self.nextSha[pos] = next
                return pos

        self.types.append(type)
        self.nextSha.append(next)

        return len(self.types) - 1

    def changeActiveLane(self, sha1):
        t = self.types[self.activeLane]
        if t == Lane.INITIAL or Lane.isBoundary(t):
            self.types[self.activeLane] = Lane.EMPTY
        else:
            self.types[self.activeLane] = Lane.NOT_ACTIVE

        idx = self.findNextSha1(sha1, 0)
        if idx != -1:
            self.types[idx] = Lane.ACTIVE
        else:
            idx = self.add(Lane.BRANCH, sha1, self.activeLane)

        self.activeLane = idx

    def setFork(self, sha1):
        s = e = idx = self.findNextSha1(sha1, 0)
        while idx != -1:
            e = idx
            self.types[idx] = Lane.TAIL
            idx = self.findNextSha1(sha1, idx + 1)

        self.types[self.activeLane] = self.node
        if self.types[s] == self.node:
            self.types[s] = self.node_l

        if self.types[e] == self.node:
            self.types[e] = self.node_r

        if self.types[s] == Lane.TAIL:
            self.types[s] == Lane.TAIL_L

        if self.types[e] == Lane.TAIL:
            self.types[e] = Lane.TAIL_R

        for i in range(s + 1, e):
            if self.types[i] == Lane.NOT_ACTIVE:
                self.types[i] = Lane.CROSS
            elif self.types[i] == Lane.EMPTY:
                self.types[i] = Lane.CROSS_EMPTY

    def setMerge(self, parents):
        if self.isBoundary:
            return

        t = self.types[self.activeLane]
        wasFork = t == self.node
        wasForkL = t == self.node_l
        wasForkR = t == self.node_r

        self.types[self.activeLane] = self.node

        s = e = self.activeLane
        startJoinWasACross = False
        endJoinWasACross = False
        # skip first parent
        for i in range(1, len(parents)):
            idx = self.findNextSha1(parents[i], 0)
            if idx != -1:
                if idx > e:
                    e = idx
                    endJoinWasACross = self.types[idx] == Lane.CROSS
                if idx < s:
                    s = idx
                    startJoinWasACross = self.types[idx] == Lane.CROSS

                self.types[idx] = Lane.JOIN
            else:
                e = self.add(Lane.HEAD, parents[i], e + 1)

        if self.types[s] == self.node and not wasFork and not wasForkR:
            self.types[s] = self.node_l
        if self.types[e] == self.node and not wasFork and not wasForkL:
            self.types[e] = self.node_r

        if self.types[s] == Lane.JOIN and not startJoinWasACross:
            self.types[s] = Lane.JOIN_L
        if self.types[e] == Lane.JOIN and not endJoinWasACross:
            self.types[e] = Lane.JOIN_R

        if self.types[s] == Lane.HEAD:
            self.types[s] = Lane.HEAD_L
        if self.types[e] == Lane.HEAD:
            self.types[e] = Lane.HEAD_R

        for i in range(s + 1, e):
            if self.types[i] == Lane.NOT_ACTIVE:
                self.types[i] = Lane.CROSS
            elif self.types[i] == Lane.EMPTY:
                self.types[i] = Lane.CROSS_EMPTY
            elif self.types[i] == Lane.TAIL_R or \
                    self.types[i] == Lane.TAIL_L:
                self.types[i] = Lane.TAIL

    def setInitial(self):
        t = self.types[self.activeLane]
        # TODO: applied
        if not self.isNode(t):
            if self.isBoundary:
                self.types[self.activeLane] = Lane.BOUNDARY
            else:
                self.types[self.activeLane] = Lane.INITIAL

    def getLanes(self):
        return list(self.types)

    def nextParent(self, sha1):
        if self.isBoundary:
            self.nextSha[self.activeLane] = ""
        else:
            self.nextSha[self.activeLane] = sha1

    def afterMerge(self):
        if self.isBoundary:
            return

        for i in range(len(self.types)):
            t = self.types[i]
            if Lane.isHead(t) or Lane.isJoin(t) or t == Lane.CROSS:
                self.types[i] = Lane.NOT_ACTIVE
            elif t == Lane.CROSS_EMPTY:
                self.types[i] = Lane.EMPTY
            elif self.isNode(t):
                self.types[i] = Lane.ACTIVE

    def afterFork(self):
        for i in range(len(self.types)):
            t = self.types[i]
            if t == Lane.CROSS:
                self.types[i] = Lane.NOT_ACTIVE
            elif Lane.isTail(t) or t == Lane.CROSS_EMPTY:
                self.types[i] = Lane.EMPTY

            if not self.isBoundary and self.isNode(t):
                self.types[i] = Lane.ACTIVE

        while self.types[-1] == Lane.EMPTY:
            self.types.pop()
            self.nextSha.pop()

    def afterBranch(self):
        self.types[self.activeLane] = Lane.ACTIVE


class FindData():

    def __init__(self):
        self.reset()

    def reset(self):
        self.param = None
        self.filterPath = None
        self.needUpdate = True
        self.result = []
        self.dataFragment = None
        self.sha1IndexMap = {}

    def parseData(self, data):
        if self.dataFragment:
            fullData = self.dataFragment
            fullData += data
            self.dataFragment = None
        else:
            fullData = data

        # full sha1 length + newline
        if len(fullData) < 41:
            self.dataFragment = fullData
            return False

        parts = fullData.rstrip(b'\n').split(b'\n')
        if len(parts[-1]) < 40:
            self.dataFragment = parts[-1]
            parts.pop()

        for sha1 in parts:
            index = self.sha1IndexMap[sha1.decode("utf-8")]
            bisect.insort(self.result, index)

        return True

    def nextResult(self):
        if not self.param.range or not self.result:
            return FIND_NOTFOUND

        x = self.param.range.start
        if self.param.range.start > self.param.range.stop:
            index = bisect.bisect_left(self.result, x)
            if index < len(self.result) and self.result[index] <= x:
                return self.result[index]
            if index - 1 >= 0 and self.result[index - 1] <= x:
                return self.result[index - 1]
        else:
            index = bisect.bisect_right(self.result, x)
            if index - 1 >= 0 and self.result[index - 1] >= x:
                return self.result[index - 1]
            if index < len(self.result):
                return self.result[index]

        return FIND_NOTFOUND


class LogView(QAbstractScrollArea):
    currentIndexChanged = pyqtSignal(int)
    findFinished = pyqtSignal(int)
    findProgress = pyqtSignal(int)

    def __init__(self, parent=None):
        super(LogView, self).__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)

        self.data = CommitFetcher()
        self.curIdx = -1
        self.branchA = True

        self.lineSpace = 5
        self.marginX = 3
        self.marginY = 3

        # commit history graphs
        self.graphs = {}
        self.lanes = Lanes()
        self.firstFreeLane = 0

        self.color = "#FF0000"
        self.sha1Url = None
        self.bugUrl = None
        self.bugRe = None

        self.authorRe = re.compile("(.*) <.*>$")

        self.findProc = None
        self.isFindFinished = False
        self.findData = FindData()

        self.highlightPattern = None
        self.marker = Marker()

        self.filterPath = None

        self.__setupMenu()

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        # never show the horizontalScrollBar
        # since we can view the long content in diff view
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.updateSettings()

    def __del__(self):
        self.cancelFindCommit()

    def __setupMenu(self):
        self.menu = QMenu()
        self.menu.addAction(self.tr("&Copy commit summary"),
                            self.__onCopyCommitSummary)
        self.menu.addSeparator()

        self.menu.addAction(self.tr("&Mark this commit"),
                            self.__onMarkCommit)
        self.acMarkTo = self.menu.addAction(self.tr("Mark &to this commit"),
                                            self.__onMarkToCommit)
        self.acClearMarks = self.menu.addAction(self.tr("Clea&r Marks"),
                                                self.__onClearMarks)

    def setBranchB(self):
        self.branchA = False
        settings = QApplication.instance().settings()
        self.setColor(settings.commitColorB().name())

    def setColor(self, color):
        self.color = color

    def setSha1Url(self, url):
        self.sha1Url = url

    def setBugUrl(self, url):
        self.bugUrl = url

    def setBugPattern(self, pattern):
        self.bugRe = re.compile(pattern)

    def setLogs(self, commits):
        self.data.setSource(commits)
        if self.data:
            self.setCurrentIndex(0)

        self.updateGeometries()
        self.viewport().update()

    def clear(self):
        self.data.setSource(None)
        self.curIdx = -1
        self.graphs.clear()
        self.lanes = Lanes()
        self.firstFreeLane = 0
        self.marker.clear()
        self.clearFindData()
        self.viewport().update()
        self.currentIndexChanged.emit(self.curIdx)
        self.cancelFindCommit()

    def getCommit(self, index):
        return self.data[index]

    def getCount(self):
        return len(self.data)

    def currentIndex(self):
        return self.curIdx

    def ensureVisible(self):
        if self.curIdx == -1:
            return

        startLine = self.verticalScrollBar().value()
        endLine = startLine + self.__linesPerPage()

        if self.curIdx < startLine or self.curIdx >= endLine:
            self.verticalScrollBar().setValue(self.curIdx)

    def setCurrentIndex(self, index):
        if index >= 0 and index < len(self.data):
            self.curIdx = index
            self.ensureVisible()
            self.viewport().update()
            self.currentIndexChanged.emit(index)

    def switchToCommit(self, sha1):
        # ignore if sha1 same as current's
        if self.curIdx != -1 and self.curIdx < len(self.data):
            commit = self.data[self.curIdx]
            if commit and commit.sha1.startswith(sha1):
                self.ensureVisible()
                return True

        index = self.data.findCommitIndex(sha1)
        if index != -1:
            self.setCurrentIndex(index)

        return index != -1

    def switchToNearCommit(self, sha1, goNext=True):
        curIdx = self.curIdx if self.curIdx >= 0 else 0
        index = self.data.findCommitIndex(sha1, self.curIdx, goNext)
        if index != -1:
            self.setCurrentIndex(index)
        return index != -1

    def showContextMenu(self, pos):
        if self.curIdx == -1:
            return

        hasMark = self.marker.hasMark()
        self.acMarkTo.setVisible(hasMark)
        self.acClearMarks.setVisible(hasMark)

        globalPos = self.mapToGlobal(pos)
        self.menu.exec(globalPos)

    def updateSettings(self):
        settings = QApplication.instance().settings()
        self.font = settings.logViewFont()

        self.lineHeight = QFontMetrics(self.font).height() + self.lineSpace

        if self.branchA:
            self.setColor(settings.commitColorA().name())
        else:
            self.setColor(settings.commitColorB().name())
        self.setSha1Url(settings.commitUrl())
        self.setBugUrl(settings.bugUrl())
        self.setBugPattern(settings.bugPattern())

        self.updateGeometries()

    def __onCopyCommitSummary(self):
        if self.curIdx == -1:
            return
        commit = self.data[self.curIdx]
        if not commit:
            return

        commit = Git.commitSummary(commit.sha1)
        if not commit:
            return

        clipboard = QApplication.clipboard()

        htmlText = '<html>\n'
        htmlText += '<head>\n'
        htmlText += '<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n'
        htmlText += '</head>\n'
        htmlText += '<body>\n'
        htmlText += '<div>\n'
        htmlText += '<p style="margin:0pt">\n'
        htmlText += '<span style="font-size:10pt;color:{0}">'.format(
            self.color)
        htmlText += self.__sha1Url(commit["sha1"])
        htmlText += ' (&quot;'
        htmlText += self.__filterBug(commit["subject"])
        htmlText += '&quot;, ' + \
            self.__mailTo(commit["author"], commit["email"])
        htmlText += ', ' + commit["date"]
        htmlText += ')</span>'
        htmlText += '</p>\n'
        htmlText += '</div>\n'
        htmlText += '</body>\n'
        htmlText += '</html>\n'

        mimeData = QMimeData()
        mimeData.setHtml(htmlText)
        mimeData.setText('{0} ("{1}"), {2}, {3}'.format(
            commit["sha1"],
            commit["subject"],
            commit["author"],
            commit["date"]))

        clipboard.setMimeData(mimeData)

    def __onMarkCommit(self):
        assert self.curIdx >= 0

        begin = self.curIdx
        end = self.curIdx
        self.marker.mark(begin, end)
        # TODO: update marked lines only
        self.viewport().update()

    def __onMarkToCommit(self):
        assert self.curIdx >= 0

        begin = self.marker.begin()
        end = self.curIdx
        self.marker.mark(begin, end)
        # TODO: update marked lines only
        self.viewport().update()

    def __onClearMarks(self):
        self.marker.clear()
        # TODO: update marked lines only
        self.viewport().update()

    def __onFindDataAvailable(self):
        data = self.findProc.readAllStandardOutput()
        if self.findData.parseData(data.data()):
            if self.findData.needUpdate:
                index = self.findData.nextResult()
                self.findFinished.emit(index)

            self.viewport().update()

    def __onFindFinished(self, exitCode, exitStatus):
        self.findProc = None
        self.isFindFinished = True

        if exitCode != 0 and exitStatus != QProcess.NormalExit:
            self.findFinished.emit(FIND_CANCELED)
        elif not self.findData.result:
            self.findFinished.emit(FIND_NOTFOUND)

    def __sha1Url(self, sha1):
        if not self.sha1Url:
            return sha1

        return '<a href="{0}{1}">{1}</a>'.format(self.sha1Url, sha1)

    def __filterBug(self, subject):
        text = htmlEscape(subject)
        if not self.bugUrl or not self.bugRe:
            return text

        return self.bugRe.sub('<a href="{0}\\1">\\1</a>'.format(self.bugUrl), text)

    def __mailTo(self, author, email):
        return '<a href="mailto:{0}">{1}</a>'.format(email, htmlEscape(author))

    def __linesPerPage(self):
        h = self.viewport().height() - self.marginY
        return int(h / self.lineHeight)

    def __itemRect(self, index):
        """@index the index of data"""

        # the row number in viewport
        row = (index - self.verticalScrollBar().value())

        offsetX = self.horizontalScrollBar().value()
        x = self.marginX - offsetX
        y = self.marginY + row * self.lineHeight
        w = self.viewport().width() - x - self.marginX
        h = self.lineHeight

        rect = QRect(x, y, w, h)

        return rect

    def __drawTag(self, painter, rect, color, text, bold=False):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        if bold:
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)

        flags = Qt.AlignLeft | Qt.AlignVCenter
        br = painter.boundingRect(rect, flags, text)
        br.adjust(0, -1, 4, 1)

        painter.fillRect(br, color)
        painter.setPen(Qt.black)
        painter.drawRect(br)

        painter.drawText(br, Qt.AlignCenter, text)

        painter.restore()
        rect.adjust(br.width(), 0, 0, 0)

    def __drawTriangleTag(self, painter, rect, color, text):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)

        flags = Qt.AlignLeft | Qt.AlignVCenter
        br = painter.boundingRect(rect, flags, text)
        br.adjust(0, -1, 4, 1)

        h = br.height()
        w = int(h / 2)

        path = QPainterPath()
        path.moveTo(QPoint(br.x(), br.y() + int(h / 2)))

        # move rect to right
        br.adjust(w, 0, w, 0)

        path.lineTo(br.topLeft())
        path.lineTo(br.topRight())
        path.lineTo(br.bottomRight())
        path.lineTo(br.bottomLeft())
        path.closeSubpath()

        painter.setPen(Qt.black)
        painter.fillPath(path, color)
        painter.drawPath(path)

        painter.drawText(br, flags, text)

        painter.restore()
        rect.adjust(path.boundingRect().width(), 0, 0, 0)

    def __laneWidth(self):
        return int(self.lineHeight * 3 / 4)

    def __drawGraph(self, painter, rect, cid):
        commit = self.data[cid]
        if not commit.sha1 in self.graphs:
            self.__updateGraph(cid)

        lanes = self.graphs[commit.sha1]
        activeLane = 0
        for i in range(len(lanes)):
            if Lane.isActive(lanes[i]):
                activeLane = i
                break

        totalColor = len(GRAPH_COLORS)
        activeColor = GRAPH_COLORS[activeLane % totalColor]
        w = self.__laneWidth()
        x1 = 0
        x2 = 0
        isHead = (commit.sha1 == Git.REV_HEAD)
        firstCommit = (cid == 0)

        painter.save()
        painter.translate(rect.topLeft())
        painter.setRenderHints(QPainter.Antialiasing)

        for i in range(len(lanes)):
            x1 = x2
            x2 += w

            lane = lanes[i]
            if lane == Lane.EMPTY:
                continue

            if i == activeLane:
                color = activeColor
            else:
                color = GRAPH_COLORS[i % totalColor]
            self.__drawGraphLane(painter, lane, x1, x2,
                                 color, activeColor, isHead, firstCommit)

        # refs
        rc = QRect(rect)
        rc.moveTo(0, 0)
        preL = rc.left()
        self.__drawGraphRef(painter, rc, lanes, activeLane, commit)

        painter.restore()
        offset = rc.left() - preL
        if offset == 0:  # no refs
            m = int(w / 2)
            r = int(w / 3)
            # same as spaces between ref tags
            offset = (x2 - (w - (m + r))) + 2 * r
        else:
            # spaces after refs
            offset += int(w / 3)
        rect.adjust(offset, 0, 0, 0)

    def __drawGraphLane(self, painter, lane, x1, x2, color, activeColor, isHead, firstCommit):
        h = int(self.lineHeight / 2)
        m = int((x1 + x2) / 2)
        r = int((x2 - x1) * 1 / 3)
        d = int(2 * r)

        # points
        # TL(m-r, h-r), TR(m+r, h-r)
        ###########
        #         #
        #    #    #  center (m, h)
        #         #
        ###########
        # BL(m, h+r), BR(m+r, h+r)

        painter.save()
        lanePen = QPen(Qt.black, 2)

        # arc
        if lane == Lane.JOIN or \
           lane == Lane.JOIN_R or \
           lane == Lane.HEAD or \
           lane == Lane.HEAD_R:
            gradient = QConicalGradient(x1, 2 * h, 225)
            gradient.setColorAt(0.375, color)
            gradient.setColorAt(0.625, activeColor)

            lanePen.setBrush(gradient)
            painter.setPen(lanePen)
            painter.drawArc(m, h, 2 * (x1 - m), 2 * h, 0 * 16, 90 * 16)

        elif lane == Lane.JOIN_L:
            gradient = QConicalGradient(x2, 2 * h, 315)
            gradient.setColorAt(0.375, activeColor)
            gradient.setColorAt(0.625, color)

            lanePen.setBrush(gradient)
            painter.setPen(lanePen)
            painter.drawArc(m, h, 2 * (x2 - m), 2 * h, 90 * 16, 90 * 16)

        elif lane == Lane.TAIL or \
                lane == Lane.TAIL_R:
            gradient = QConicalGradient(x1, 0, 135)
            gradient.setColorAt(0.375, activeColor)
            gradient.setColorAt(0.625, color)

            lanePen.setBrush(gradient)
            painter.setPen(lanePen)
            painter.drawArc(m, h, 2 * (x1 - m), 2 * -h, 270 * 16, 90 * 16)

        lanePen.setColor(color)
        painter.setPen(lanePen)

        # vertical line
        if lane == Lane.ACTIVE or \
                lane == Lane.NOT_ACTIVE or \
                lane == Lane.MERGE_FORK or \
                lane == Lane.MERGE_FORK_R or \
                lane == Lane.MERGE_FORK_L or \
                lane == Lane.CROSS or \
                Lane.isJoin(lane):
            if firstCommit:
                painter.drawLine(m, h, m, 2 * h)
            else:
                painter.drawLine(m, 0, m, 2 * h)

        elif lane == Lane.HEAD_L or \
                lane == Lane.BRANCH:
            painter.drawLine(m, h, m, 2 * h)

        elif lane == Lane.TAIL_L or \
                lane == Lane.INITIAL or \
                Lane.isBoundary(lane):
            painter.drawLine(m, 0, m, h)

        lanePen.setColor(activeColor)
        painter.setPen(lanePen)

        # horizontal line
        if lane == Lane.MERGE_FORK or \
                lane == Lane.JOIN or \
                lane == Lane.HEAD or \
                lane == Lane.TAIL or \
                lane == Lane.CROSS or \
                lane == Lane.CROSS_EMPTY or \
                lane == Lane.BOUNDARY_C:
            painter.drawLine(x1, h, x2, h)

        elif lane == Lane.MERGE_FORK_R or \
                lane == Lane.BOUNDARY_R:
            painter.drawLine(x1, h, m, h)

        elif lane == Lane.MERGE_FORK_L or \
                lane == Lane.HEAD_L or \
                lane == Lane.TAIL_L or \
                lane == Lane.BOUNDARY_L:
            painter.drawLine(m, h, x2, h)

        # circle
        if isHead:
            color = Qt.yellow
        if lane == Lane.ACTIVE or \
                lane == Lane.INITIAL or \
                lane == Lane.BRANCH:
            painter.setPen(Qt.black)
            painter.setBrush(color)
            painter.drawEllipse(m - r, h - r, d, d)

        elif lane == Lane.MERGE_FORK or \
                lane == Lane.MERGE_FORK_R or \
                lane == Lane.MERGE_FORK_L:
            painter.setPen(Qt.black)
            painter.setBrush(color)
            painter.drawRect(m - r, h - r, d, d)

        elif lane == Lane.UNAPPLIED:
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.red)
            painter.drawRect(m - r, h - 1, d, 2)

        elif lane == Lane.APPLIED:
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.darkGreen)
            painter.drawRect(m - r, h - 1, d, 2)
            painter.drawRect(m - 1, h - r, 2, d)

        elif lane == Lane.BOUNDARY:
            painter.setPen(Qt.black)
            painter.setBrush(painter.background())
            painter.drawEllipse(m - r, h - r, d, d)

        elif lane == Lane.BOUNDARY_C or \
                lane == Lane.BOUNDARY_R or \
                lane == Lane.BOUNDARY_L:
            painter.setPen(Qt.black)
            painter.setBrush(painter.background())
            painter.drawRect(m - r, h - r, d, d)

        painter.restore()

    def __drawGraphRef(self, painter, rc, lanes, activeLane, commit):
        if not commit.sha1 in Git.REF_MAP:
            return

        w = self.__laneWidth()
        h = int(self.lineHeight / 2)
        m = int(w / 2)
        r = int(w / 3)
        d = int(2 * r)

        refs = Git.REF_MAP[commit.sha1]
        painter.save()

        # first draw the line from circle right outline
        # to the right most lane
        painter.setPen(QPen(Qt.black, 2))
        x1 = activeLane * w + m + r
        x2 = x1 + (len(lanes) - activeLane - 1) * w
        if x1 != x2:
            painter.drawLine(x1, h, x2, h)
        rc.adjust(x2, 0, 0, 0)

        isHead = commit.sha1 == Git.REV_HEAD
        for ref in refs:
            # connector
            painter.setPen(QPen(Qt.black, 2))
            painter.drawLine(x2, h, x2 + d, h)
            rc.adjust(d, 0, 0, 0)

            # tag
            painter.setPen(QPen(Qt.black))
            color = TAG_COLORS[ref.type]

            preL = rc.left()
            if ref.type == Ref.TAG:
                self.__drawTriangleTag(painter, rc, color, ref.name)
            else:
                bold = (ref.type == Ref.HEAD and isHead)
                self.__drawTag(painter, rc, color, ref.name, bold)
            x2 = rc.left() + 1

        painter.restore()

    def __updateGraph(self, cid):
        for i in range(self.firstFreeLane, len(self.data)):
            commit = self.data[i]
            if not commit.sha1 in self.graphs:
                self.__updateLanes(commit, self.lanes)

            if i == cid:
                break
        self.firstFreeLane = i + 1

    def __updateLanes(self, commit, lanes):
        if lanes.isEmpty():
            lanes.init(commit.sha1)

        isFork, isDiscontinuity = lanes.isFork(commit.sha1)
        isMerge = (len(commit.parents) > 1)
        isInitial = (not commit.parents)

        if isDiscontinuity:
            lanes.changeActiveLane(commit.sha1)

        lanes.setBoundary(False)  # TODO
        if isFork:
            lanes.setFork(commit.sha1)
        if isMerge:
            lanes.setMerge(commit.parents)
        if isInitial:
            lanes.setInitial()

        l = lanes.getLanes()
        self.graphs[commit.sha1] = l

        if isInitial:
            nextSha1 = ""
        else:
            nextSha1 = commit.parents[0]

        lanes.nextParent(nextSha1)

        # TODO: applied
        if isMerge:
            lanes.afterMerge()
        if isFork:
            lanes.afterFork()
        if lanes.isBranch():
            lanes.afterBranch()

    def invalidateItem(self, index):
        rect = self.__itemRect(index)
        # update if visible in the viewport
        if rect.y() >= 0:
            self.viewport().update(rect)

    def updateGeometries(self):
        hScrollBar = self.horizontalScrollBar()
        vScrollBar = self.verticalScrollBar()

        if not self.data:
            hScrollBar.setRange(0, 0)
            vScrollBar.setRange(0, 0)
            return

        linesPerPage = self.__linesPerPage()
        totalLines = len(self.data)

        vScrollBar.setRange(0, totalLines - linesPerPage)
        vScrollBar.setPageStep(linesPerPage)

    def findCommitAsync(self, findParam):
        # cancel the previous one if find changed
        if self.findData.param != findParam or \
                self.findData.filterPath != self.filterPath:
            self.findData.reset()
            self.cancelFindCommit()

        self.findData.param = findParam
        self.findData.filterPath = self.filterPath
        if not findParam.pattern:
            return False

        result = self.findData.nextResult()
        if result != FIND_NOTFOUND or self.isFindFinished:
            self.findFinished.emit(result)
            return False

        self.findData.needUpdate = True
        if not self.findProc:
            args = ["diff-tree", "-r", "-s", "-m", "--stdin"]
            if findParam.field == FindField.AddOrDel:
                args.append("-S" + findParam.pattern)
                if findParam.flag == FIND_REGEXP:
                    args.append("--pickaxe-regex")
            else:
                assert findParam.field == FindField.Changes
                args.append("-G" + findParam.pattern)

            if self.filterPath:
                args.append("--")
                args.append(self.filterPath)

            process = QProcess()
            process.setWorkingDirectory(Git.REPO_DIR)
            process.readyReadStandardOutput.connect(self.__onFindDataAvailable)
            process.finished.connect(self.__onFindFinished)
            self.findProc = process
            self.isFindFinished = False

            tempFile = QTemporaryFile()
            tempFile.open()

            # find the target range first
            for i in findParam.range:
                sha1 = self.data[i].sha1
                tempFile.write(sha1 + "\n")
                self.findData.sha1IndexMap[sha1] = i

            if findParam.range.start > findParam.range.stop:
                begin = findParam.range.start + 1
                end = len(self.data)
            else:
                begin = 0
                end = findParam.range.start

            # then the rest
            for i in range(begin, end):
                sha1 = self.data[i].sha1
                tempFile.write(sha1 + "\n")
                self.findData.sha1IndexMap[sha1] = i

            tempFile.close()
            process.setStandardInputFile(tempFile.fileName())
            process.start("git", args)

        return True

    def findCommitSync(self, findPattern, findRange, findField):
        # only use for finding in comments, as it should pretty fast
        assert findField == FindField.Comments

        def findInCommit(commit):
            if findPattern.search(commit.comments):
                return True

            if findPattern.search(commit.author):
                return True

            if findPattern.search(commit.commiter):
                return True

            if findPattern.search(commit.sha1):
                return True

            if findPattern.search(commit.authorDate):
                return True

            if findPattern.search(commit.commiterDate):
                return True

            for p in commit.parents:
                if findPattern.search(p):
                    return True

            return False

        result = -1
        total = abs(findRange.stop - findRange.start)
        progress = 0
        percentage = -1

        for i in findRange:
            progress += 1
            new_percentage = int(progress * 100 / total)
            # avoid too many updates on main thread
            if percentage != new_percentage:
                percentage = new_percentage
                self.findProgress.emit(percentage)
                qApp.processEvents(QEventLoop.ExcludeUserInputEvents, 50)

            if findInCommit(self.data[i]):
                result = i
                break

        return result

    def cancelFindCommit(self, forced=True):
        self.isFindFinished = False
        self.findData.needUpdate = False

        needEmit = self.findProc is not None

        # only terminate when forced
        # otherwise still load at background
        if self.findProc and forced:
            # disconnect signals in case invalid state changes
            self.findProc.readyReadStandardOutput.disconnect()
            self.findProc.finished.disconnect()
            self.findProc.close()
            self.findProc = None
            return True

        if needEmit:
            self.findFinished.emit(FIND_CANCELED)

        return False

    def highlightKeyword(self, pattern):
        self.highlightPattern = pattern
        self.viewport().update()

    def clearFindData(self):
        self.findData.reset()

    def setFilterPath(self, path):
        self.filterPath = path

    def resizeEvent(self, event):
        super(LogView, self).resizeEvent(event)

        self.updateGeometries()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self.viewport())
        painter.setClipRect(event.rect())

        startLine = self.verticalScrollBar().value()
        endLine = startLine + self.__linesPerPage() + 1
        endLine = min(len(self.data), endLine)

        palette = self.palette()

        for i in range(startLine, endLine):
            painter.setFont(self.font)
            rect = self.__itemRect(i)
            rect.adjust(2, 0, 0, 0)

            self.__drawGraph(painter, rect, i)

            commit = self.data[i]
            # author
            text = self.authorRe.sub("\\1", commit.author)
            color = Qt.gray
            self.__drawTag(painter, rect, color, text)

            # date
            text = commit.authorDate.split(' ')[0]
            color = QColor(140, 208, 80)
            self.__drawTag(painter, rect, color, text)
            rect.adjust(4, 0, 0, 0)

            # marker
            self.marker.draw(i, painter, rect)

            # subject
            painter.save()
            if i == self.curIdx:
                painter.fillRect(rect, palette.highlight())
                if self.hasFocus():
                    painter.setPen(QPen(Qt.DotLine))
                    painter.drawRect(rect.adjusted(0, 0, -1, -1))
                painter.setPen(palette.color(QPalette.HighlightedText))
            else:
                painter.setPen(palette.color(QPalette.WindowText))

            content = commit.comments.split('\n')[0]
            textLayout = QTextLayout(content, self.font)

            textOption = QTextOption()
            textOption.setWrapMode(QTextOption.NoWrap)
            textOption.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            textLayout.setTextOption(textOption)

            formats = []
            if self.highlightPattern:
                matchs = self.highlightPattern.finditer(content)
                fmt = QTextCharFormat()
                if i == self.curIdx:
                    fmt.setForeground(QBrush(Qt.yellow))
                else:
                    fmt.setBackground(QBrush(Qt.yellow))
                for m in matchs:
                    rg = QTextLayout.FormatRange()
                    rg.start = m.start()
                    rg.length = m.end() - rg.start
                    rg.format = fmt
                    formats.append(rg)

            # bold find result
            # it seems that *in* already fast, so no bsearch
            if i in self.findData.result:
                fmt = QTextCharFormat()
                fmt.setFontWeight(QFont.Bold)
                rg = QTextLayout.FormatRange()
                rg.start = 0
                rg.length = len(content)
                rg.format = fmt
                formats.append(rg)

            textLayout.setAdditionalFormats(formats)

            textLayout.beginLayout()
            line = textLayout.createLine()
            line.setPosition(QPointF(0, 0))
            textLayout.endLayout()

            # setAlignment doesn't works at all!
            # we have to vcenter by self LoL
            rect.adjust(2, 0, 0, 0)
            offsetY = (rect.height() - painter.fontMetrics().lineSpacing()) / 2
            pos = QPointF(rect.left(), rect.top() + offsetY)
            textLayout.draw(painter, pos)

            painter.restore()

    def mousePressEvent(self, event):
        if not self.data:
            return

        y = event.pos().y()
        index = int(y / self.lineHeight)
        index += self.verticalScrollBar().value()

        if index >= len(self.data):
            return

        mod = qApp.keyboardModifiers()
        # no OR combination
        if mod == Qt.ShiftModifier:
            self.marker.mark(self.curIdx, index)
            self.viewport().update()
        else:
            self.setCurrentIndex(index)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            if self.curIdx > 0:
                startLine = self.verticalScrollBar().value()
                self.curIdx -= 1
                if self.curIdx >= startLine:
                    self.invalidateItem(self.curIdx + 1)
                    self.invalidateItem(self.curIdx)
                else:
                    self.verticalScrollBar().setValue(self.curIdx)

                self.currentIndexChanged.emit(self.curIdx)
        elif event.key() == Qt.Key_Down:
            if self.curIdx + 1 < len(self.data):
                endLine = self.verticalScrollBar().value() + self.__linesPerPage()
                self.curIdx += 1
                if self.curIdx < endLine:
                    self.invalidateItem(self.curIdx - 1)
                    self.invalidateItem(self.curIdx)
                else:
                    v = self.verticalScrollBar().value()
                    self.verticalScrollBar().setValue(v + 1)

                self.currentIndexChanged.emit(self.curIdx)

        super(LogView, self).keyPressEvent(event)

    def focusInEvent(self, event):
        self.invalidateItem(self.curIdx)

    def focusOutEvent(self, event):
        self.invalidateItem(self.curIdx)
