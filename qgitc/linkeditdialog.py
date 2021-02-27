# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QDialogButtonBox)

from PySide6.QtCore import QSize

from .linkeditwidget import LinkEditWidget
from .stylehelper import dpiScaled


class LinkEditDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Edit Links"))

        layout = QVBoxLayout(self)

        self.linkEdit = LinkEditWidget(self)
        layout.addWidget(self.linkEdit)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def sizeHint(self):
        return QSize(dpiScaled(400), 0)
