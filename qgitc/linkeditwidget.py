# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QLabel,
    QLineEdit)


class LinkEditWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self.tr("Co&mmit Url:"), self)
        layout.addWidget(label, 0, 0, 1, 1)

        self.leCommitUrl = QLineEdit(self)
        layout.addWidget(self.leCommitUrl, 0, 1, 1, 1)
        label.setBuddy(self.leCommitUrl)

        label = QLabel(self.tr("&Bug Url:"), self)
        layout.addWidget(label, 1, 0, 1, 1)

        self.leBugUrl = QLineEdit(self)
        layout.addWidget(self.leBugUrl, 1, 1, 1, 1)
        label.setBuddy(self.leBugUrl)

        label = QLabel(self.tr("Bug &Pattern:"), self)
        layout.addWidget(label, 2, 0, 1, 1)

        self.leBugPattern = QLineEdit(self)
        layout.addWidget(self.leBugPattern, 2, 1, 1, 1)
        label.setBuddy(self.leBugPattern)

    def commitUrl(self):
        return self.leCommitUrl.text()

    def setCommitUrl(self, url):
        self.leCommitUrl.setText(url)

    def bugUrl(self):
        return self.leBugUrl.text()

    def setBugUrl(self, url):
        self.leBugUrl.setText(url)

    def bugPattern(self):
        return self.leBugPattern.text()

    def setBugPattern(self, pattern):
        self.leBugPattern.setText(pattern)
