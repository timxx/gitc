# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QLabel,
    QLineEdit)

from PySide6.QtGui import (
    QIntValidator)


__all__ = ["GotoDialog"]


class GotoDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Go To Line"))

        layout = QVBoxLayout(self)
        self._lbDesc = QLabel(self.tr("Line number:"), self)
        layout.addWidget(self._lbDesc)

        self._lineEdit = QLineEdit(self)
        self._validator = QIntValidator(self)
        self._lineEdit.setValidator(self._validator)
        layout.addWidget(self._lineEdit)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        self._lineEdit.setText("1")
        self._lineEdit.selectAll()

    def setRange(self, minLine, maxLine, curLine):
        if maxLine < minLine:
            minLine = maxLine

        self._validator.setRange(minLine, maxLine)
        self._lineEdit.setText(str(curLine))
        self._lbDesc.setText(
            self.tr("Line number (%d - %d):") % (minLine, maxLine))
        self._lineEdit.selectAll()

    @property
    def lineNo(self):
       return int(self._lineEdit.text())
