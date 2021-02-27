# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'aboutdialog.ui'
##
## Created by: Qt User Interface Compiler version 6.0.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class Ui_AboutDialog(object):
    def setupUi(self, AboutDialog):
        if not AboutDialog.objectName():
            AboutDialog.setObjectName(u"AboutDialog")
        AboutDialog.resize(465, 470)
        self.verticalLayout = QVBoxLayout(AboutDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(AboutDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabAbout = QWidget()
        self.tabAbout.setObjectName(u"tabAbout")
        self.verticalLayout_3 = QVBoxLayout(self.tabAbout)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.appIcon = QLabel(self.tabAbout)
        self.appIcon.setObjectName(u"appIcon")
        self.appIcon.setAlignment(Qt.AlignCenter)

        self.verticalLayout_3.addWidget(self.appIcon)

        self.tbAbout = QTextBrowser(self.tabAbout)
        self.tbAbout.setObjectName(u"tbAbout")

        self.verticalLayout_3.addWidget(self.tbAbout)

        self.tabWidget.addTab(self.tabAbout, "")
        self.tabLicense = QWidget()
        self.tabLicense.setObjectName(u"tabLicense")
        self.verticalLayout_2 = QVBoxLayout(self.tabLicense)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tbLicense = QTextBrowser(self.tabLicense)
        self.tbLicense.setObjectName(u"tbLicense")

        self.verticalLayout_2.addWidget(self.tbLicense)

        self.tabWidget.addTab(self.tabLicense, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.buttonBox = QDialogButtonBox(AboutDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)
        self.buttonBox.setCenterButtons(True)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(AboutDialog)
        self.buttonBox.accepted.connect(AboutDialog.accept)
        self.buttonBox.rejected.connect(AboutDialog.reject)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(AboutDialog)
    # setupUi

    def retranslateUi(self, AboutDialog):
        AboutDialog.setWindowTitle(QCoreApplication.translate("AboutDialog", u"About QGitc", None))
        self.appIcon.setText("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabAbout), QCoreApplication.translate("AboutDialog", u"&About", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabLicense), QCoreApplication.translate("AboutDialog", u"&License", None))
    # retranslateUi

