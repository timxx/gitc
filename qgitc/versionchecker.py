# -*- coding: utf-8 -*-

from PySide6.QtCore import (
    QObject,
    Signal,
    QJsonDocument)
from PySide6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkRequest,
    QNetworkReply)

from .version import (
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH)


class VersionChecker(QObject):

    newVersionAvailable = Signal(str)
    finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def startCheck(self):
        request = QNetworkRequest()
        request.setUrl("https://pypi.org/pypi/qgitc/json")

        self._manager = QNetworkAccessManager(self)
        reply = self._manager.get(request)
        if not reply:
            return

        reply.finished.connect(self._onFinished)

    def _onFinished(self):
        reply = self.sender()
        reply.deleteLater()

        try:
            if reply.error() != QNetworkReply.NoError:
                return

            data = reply.readAll()
            if not data:
                return

            version = self._getVersion(data)
            if not version:
                return

            v = [int(s) for s in version.split(".")]
            if len(v) != 3:
                return

            newVersion = False
            if v[0] < VERSION_MAJOR:
                pass
            elif v[0] > VERSION_MAJOR:
                newVersion = True
            else:
                if v[1] < VERSION_MINOR:
                    pass
                if v[1] > VERSION_MINOR:
                    newVersion = True
                elif v[2] > VERSION_PATCH:
                    newVersion = True

            if newVersion:
                self.newVersionAvailable.emit(version)
        finally:
            self.finished.emit()

    def _getVersion(self, data):
        doc = QJsonDocument.fromJson(data)
        if doc.isNull():
            return ""

        root = doc.object()
        if "info" not in root:
            return ""

        infoObj = root["info"]
        if "version" not in infoObj:
            return ""

        version = infoObj["version"]
        if not isinstance(version, str):
            return ""

        return version
