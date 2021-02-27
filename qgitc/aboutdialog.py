# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QDialog, QApplication
from PySide6.QtCore import QSize
from .ui_aboutdialog import Ui_AboutDialog
from .common import dataDirPath
from .version import VERSION
from .stylehelper import dpiScaled


class AboutDialog(QDialog, Ui_AboutDialog):

    def __init__(self, parent=None):
        super(AboutDialog, self).__init__(parent)

        self.setupUi(self)

        icon = qApp.windowIcon()
        self.appIcon.setPixmap(icon.pixmap(dpiScaled(64), dpiScaled(64)))

        self.tbAbout.setOpenExternalLinks(True)
        self.tbLicense.setOpenExternalLinks(True)

        self.__initTabs()

        self.resize(dpiScaled(QSize(465, 470)))

    def __initTabs(self):
        about = "<center><h3>QGitc " + VERSION + "</h3></center>"
        about += "<center>"
        about += self.tr("Git file conflicts and logs viewer")
        about += "</center>"
        about += "<center><a href=https://github.com/timxx/qgitc>"
        about += self.tr("Visit project host")
        about += "</a></center><br/>"
        about += "<center>Copyright © 2016-2021 Weitian Leung</center>"

        self.tbAbout.setHtml(about)

        licenseFile = dataDirPath() + "/licenses/Apache-2.0.html"
        with open(licenseFile) as f:
            self.tbLicense.setHtml(f.read())
