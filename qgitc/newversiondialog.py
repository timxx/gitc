# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QMessageBox,
    QCheckBox)


class NewVersionDialog(QMessageBox):

    def __init__(self, version, parent=None):
        super().__init__(parent)

        self._version = version

        self.setIcon(QMessageBox.Information)
        self.setWindowTitle(self.tr("New version available"))
        # TODO: for source version?
        self.setText(self.tr(
            "A new version ({0}) was available.\n"
            "Run `{1}` for getting the latest version.".format(
                version, "pip install qgitc --upgrade")))

        cb = QCheckBox(self.tr("Ignore this version"), self)
        self.setCheckBox(cb)

        cb.toggled.connect(self._onCbIgnoreToggled)

    def _onCbIgnoreToggled(self, checked):
        qApp.settings().setIgnoredVersion(self._version)
