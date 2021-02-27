# -*- coding: utf-8 -*-

from PySide6.QtCore import QEvent


class BlameEvent(QEvent):

    Type = QEvent.User + 1

    def __init__(self, filePath, rev=None, lineNo=0):
        super().__init__(QEvent.Type(BlameEvent.Type))
        self.filePath = filePath
        self.rev = rev
        self.lineNo = lineNo


class ShowCommitEvent(QEvent):

    Type = QEvent.User + 2

    def __init__(self, sha1):
        super().__init__(QEvent.Type(ShowCommitEvent.Type))
        self.sha1 = sha1


class OpenLinkEvent(QEvent):

    Type = QEvent.User + 3

    def __init__(self, link):
        super().__init__(QEvent.Type(OpenLinkEvent.Type))
        self.link = link
