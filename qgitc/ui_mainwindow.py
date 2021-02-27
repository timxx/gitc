# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.0.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from .gitview import GitView


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        self.acQuit = QAction(MainWindow)
        self.acQuit.setObjectName(u"acQuit")
        icon = QIcon()
        iconThemeName = u"window-close"
        if QIcon.hasThemeIcon(iconThemeName):
            icon = QIcon.fromTheme(iconThemeName)
        else:
            icon.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)
        
        self.acQuit.setIcon(icon)
#if QT_CONFIG(shortcut)
        self.acQuit.setShortcut(u"Ctrl+W")
#endif // QT_CONFIG(shortcut)
        self.acAbout = QAction(MainWindow)
        self.acAbout.setObjectName(u"acAbout")
        icon1 = QIcon()
        iconThemeName = u"help-about"
        if QIcon.hasThemeIcon(iconThemeName):
            icon1 = QIcon.fromTheme(iconThemeName)
        else:
            icon1.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)
        
        self.acAbout.setIcon(icon1)
        self.acPreferences = QAction(MainWindow)
        self.acPreferences.setObjectName(u"acPreferences")
        icon2 = QIcon()
        iconThemeName = u"preferences-system"
        if QIcon.hasThemeIcon(iconThemeName):
            icon2 = QIcon.fromTheme(iconThemeName)
        else:
            icon2.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)
        
        self.acPreferences.setIcon(icon2)
        self.actionIgnore_whitespace_changes = QAction(MainWindow)
        self.actionIgnore_whitespace_changes.setObjectName(u"actionIgnore_whitespace_changes")
        self.acVisualizeWhitespace = QAction(MainWindow)
        self.acVisualizeWhitespace.setObjectName(u"acVisualizeWhitespace")
        self.acVisualizeWhitespace.setCheckable(True)
        self.acIgnoreEOL = QAction(MainWindow)
        self.acIgnoreEOL.setObjectName(u"acIgnoreEOL")
        self.acIgnoreEOL.setCheckable(True)
        self.acIgnoreAll = QAction(MainWindow)
        self.acIgnoreAll.setObjectName(u"acIgnoreAll")
        self.acIgnoreAll.setCheckable(True)
        self.acIgnoreNone = QAction(MainWindow)
        self.acIgnoreNone.setObjectName(u"acIgnoreNone")
        self.acIgnoreNone.setCheckable(True)
        self.acCopy = QAction(MainWindow)
        self.acCopy.setObjectName(u"acCopy")
        icon3 = QIcon()
        iconThemeName = u"edit-copy"
        if QIcon.hasThemeIcon(iconThemeName):
            icon3 = QIcon.fromTheme(iconThemeName)
        else:
            icon3.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)
        
        self.acCopy.setIcon(icon3)
        self.acSelectAll = QAction(MainWindow)
        self.acSelectAll.setObjectName(u"acSelectAll")
        icon4 = QIcon()
        iconThemeName = u"edit-select-all"
        if QIcon.hasThemeIcon(iconThemeName):
            icon4 = QIcon.fromTheme(iconThemeName)
        else:
            icon4.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)
        
        self.acSelectAll.setIcon(icon4)
        self.acFind = QAction(MainWindow)
        self.acFind.setObjectName(u"acFind")
        icon5 = QIcon()
        iconThemeName = u"edit-find"
        if QIcon.hasThemeIcon(iconThemeName):
            icon5 = QIcon.fromTheme(iconThemeName)
        else:
            icon5.addFile(u".", QSize(), QIcon.Normal, QIcon.Off)
        
        self.acFind.setIcon(icon5)
        self.acCompare = QAction(MainWindow)
        self.acCompare.setObjectName(u"acCompare")
        self.acCompare.setCheckable(True)
        self.acShowGraph = QAction(MainWindow)
        self.acShowGraph.setObjectName(u"acShowGraph")
        self.acShowGraph.setCheckable(True)
        self.acShowGraph.setChecked(True)
        self.acAboutQt = QAction(MainWindow)
        self.acAboutQt.setObjectName(u"acAboutQt")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridFrame = QFrame(self.centralwidget)
        self.gridFrame.setObjectName(u"gridFrame")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gridFrame.sizePolicy().hasHeightForWidth())
        self.gridFrame.setSizePolicy(sizePolicy)
        self.gridFrame.setFrameShape(QFrame.StyledPanel)
        self.gridLayout_2 = QGridLayout(self.gridFrame)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.leRepo = QLineEdit(self.gridFrame)
        self.leRepo.setObjectName(u"leRepo")

        self.gridLayout_2.addWidget(self.leRepo, 0, 2, 1, 1)

        self.leOpts = QLineEdit(self.gridFrame)
        self.leOpts.setObjectName(u"leOpts")

        self.gridLayout_2.addWidget(self.leOpts, 2, 2, 1, 1)

        self.label_2 = QLabel(self.gridFrame)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 2, 0, 1, 1)

        self.btnRepoBrowse = QPushButton(self.gridFrame)
        self.btnRepoBrowse.setObjectName(u"btnRepoBrowse")

        self.gridLayout_2.addWidget(self.btnRepoBrowse, 0, 3, 1, 1)

        self.label = QLabel(self.gridFrame)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.lbSubmodule = QLabel(self.gridFrame)
        self.lbSubmodule.setObjectName(u"lbSubmodule")

        self.gridLayout_2.addWidget(self.lbSubmodule, 1, 0, 1, 1)

        self.cbSubmodule = QComboBox(self.gridFrame)
        self.cbSubmodule.setObjectName(u"cbSubmodule")

        self.gridLayout_2.addWidget(self.cbSubmodule, 1, 2, 1, 1)


        self.verticalLayout.addWidget(self.gridFrame)

        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setFrameShape(QFrame.StyledPanel)
        self.splitter.setFrameShadow(QFrame.Plain)
        self.splitter.setOrientation(Qt.Horizontal)
        self.gitViewA = GitView(self.splitter)
        self.gitViewA.setObjectName(u"gitViewA")
        self.splitter.addWidget(self.gitViewA)

        self.verticalLayout.addWidget(self.splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 22))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setObjectName(u"menuFile")
        self.menu_Help = QMenu(self.menubar)
        self.menu_Help.setObjectName(u"menu_Help")
        self.menu_Settings = QMenu(self.menubar)
        self.menu_Settings.setObjectName(u"menu_Settings")
        self.menu_View = QMenu(self.menubar)
        self.menu_View.setObjectName(u"menu_View")
        self.menuIgnoreWhitespace = QMenu(self.menu_View)
        self.menuIgnoreWhitespace.setObjectName(u"menuIgnoreWhitespace")
        self.menu_Edit = QMenu(self.menubar)
        self.menu_Edit.setObjectName(u"menu_Edit")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        QWidget.setTabOrder(self.leRepo, self.btnRepoBrowse)
        QWidget.setTabOrder(self.btnRepoBrowse, self.leOpts)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menu_Edit.menuAction())
        self.menubar.addAction(self.menu_View.menuAction())
        self.menubar.addAction(self.menu_Settings.menuAction())
        self.menubar.addAction(self.menu_Help.menuAction())
        self.menuFile.addAction(self.acQuit)
        self.menu_Help.addAction(self.acAbout)
        self.menu_Help.addAction(self.acAboutQt)
        self.menu_Settings.addAction(self.acPreferences)
        self.menu_View.addAction(self.acVisualizeWhitespace)
        self.menu_View.addAction(self.menuIgnoreWhitespace.menuAction())
        self.menu_View.addSeparator()
        self.menu_View.addAction(self.acCompare)
        self.menuIgnoreWhitespace.addAction(self.acIgnoreNone)
        self.menuIgnoreWhitespace.addAction(self.acIgnoreEOL)
        self.menuIgnoreWhitespace.addAction(self.acIgnoreAll)
        self.menu_Edit.addAction(self.acCopy)
        self.menu_Edit.addAction(self.acSelectAll)
        self.menu_Edit.addSeparator()
        self.menu_Edit.addAction(self.acFind)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"QGitc", None))
        self.acQuit.setText(QCoreApplication.translate("MainWindow", u"Close &Window", None))
        self.acAbout.setText(QCoreApplication.translate("MainWindow", u"&About QGitc", None))
        self.acPreferences.setText(QCoreApplication.translate("MainWindow", u"&Preferences...", None))
        self.actionIgnore_whitespace_changes.setText(QCoreApplication.translate("MainWindow", u"Ignore whitespace changes", None))
        self.acVisualizeWhitespace.setText(QCoreApplication.translate("MainWindow", u"&Visualize whitespace", None))
        self.acIgnoreEOL.setText(QCoreApplication.translate("MainWindow", u"At &end of line", None))
        self.acIgnoreAll.setText(QCoreApplication.translate("MainWindow", u"&All", None))
        self.acIgnoreNone.setText(QCoreApplication.translate("MainWindow", u"&None", None))
        self.acCopy.setText(QCoreApplication.translate("MainWindow", u"&Copy", None))
#if QT_CONFIG(shortcut)
        self.acCopy.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+C", None))
#endif // QT_CONFIG(shortcut)
        self.acSelectAll.setText(QCoreApplication.translate("MainWindow", u"Select &All", None))
#if QT_CONFIG(shortcut)
        self.acSelectAll.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+A", None))
#endif // QT_CONFIG(shortcut)
        self.acFind.setText(QCoreApplication.translate("MainWindow", u"&Find", None))
#if QT_CONFIG(shortcut)
        self.acFind.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+F", None))
#endif // QT_CONFIG(shortcut)
        self.acCompare.setText(QCoreApplication.translate("MainWindow", u"&Compare Mode", None))
        self.acShowGraph.setText(QCoreApplication.translate("MainWindow", u"Show &graph", None))
        self.acAboutQt.setText(QCoreApplication.translate("MainWindow", u"About &Qt", None))
#if QT_CONFIG(tooltip)
        self.leOpts.setToolTip(QCoreApplication.translate("MainWindow", u"See the GIT-LOG options for more information.", None))
#endif // QT_CONFIG(tooltip)
        self.leOpts.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Type the log options here and press Enter to filter", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Filter:", None))
        self.btnRepoBrowse.setText(QCoreApplication.translate("MainWindow", u"&Browse...", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Repository:", None))
        self.lbSubmodule.setText(QCoreApplication.translate("MainWindow", u"Submodule:", None))
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"&File", None))
        self.menu_Help.setTitle(QCoreApplication.translate("MainWindow", u"&Help", None))
        self.menu_Settings.setTitle(QCoreApplication.translate("MainWindow", u"&Settings", None))
        self.menu_View.setTitle(QCoreApplication.translate("MainWindow", u"&View", None))
        self.menuIgnoreWhitespace.setTitle(QCoreApplication.translate("MainWindow", u"&Ignore whitespace", None))
        self.menu_Edit.setTitle(QCoreApplication.translate("MainWindow", u"&Edit", None))
    # retranslateUi

