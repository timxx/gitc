# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gitc/mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridFrame = QtWidgets.QFrame(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gridFrame.sizePolicy().hasHeightForWidth())
        self.gridFrame.setSizePolicy(sizePolicy)
        self.gridFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.gridFrame.setObjectName("gridFrame")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.gridFrame)
        self.gridLayout_2.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.leRepo = QtWidgets.QLineEdit(self.gridFrame)
        self.leRepo.setObjectName("leRepo")
        self.gridLayout_2.addWidget(self.leRepo, 0, 2, 1, 1)
        self.leOpts = QtWidgets.QLineEdit(self.gridFrame)
        self.leOpts.setObjectName("leOpts")
        self.gridLayout_2.addWidget(self.leOpts, 2, 2, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.gridFrame)
        self.label_2.setObjectName("label_2")
        self.gridLayout_2.addWidget(self.label_2, 2, 0, 1, 1)
        self.btnRepoBrowse = QtWidgets.QPushButton(self.gridFrame)
        self.btnRepoBrowse.setObjectName("btnRepoBrowse")
        self.gridLayout_2.addWidget(self.btnRepoBrowse, 0, 3, 1, 1)
        self.label = QtWidgets.QLabel(self.gridFrame)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)
        self.lbSubmodule = QtWidgets.QLabel(self.gridFrame)
        self.lbSubmodule.setObjectName("lbSubmodule")
        self.gridLayout_2.addWidget(self.lbSubmodule, 1, 0, 1, 1)
        self.cbSubmodule = QtWidgets.QComboBox(self.gridFrame)
        self.cbSubmodule.setObjectName("cbSubmodule")
        self.gridLayout_2.addWidget(self.cbSubmodule, 1, 2, 1, 1)
        self.verticalLayout.addWidget(self.gridFrame)
        self.splitter = QtWidgets.QSplitter(self.centralwidget)
        self.splitter.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.splitter.setFrameShadow(QtWidgets.QFrame.Plain)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.gitViewA = GitView(self.splitter)
        self.gitViewA.setObjectName("gitViewA")
        self.verticalLayout.addWidget(self.splitter)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menu_Help = QtWidgets.QMenu(self.menubar)
        self.menu_Help.setObjectName("menu_Help")
        self.menu_Settings = QtWidgets.QMenu(self.menubar)
        self.menu_Settings.setObjectName("menu_Settings")
        self.menu_View = QtWidgets.QMenu(self.menubar)
        self.menu_View.setObjectName("menu_View")
        self.menuIgnoreWhitespace = QtWidgets.QMenu(self.menu_View)
        self.menuIgnoreWhitespace.setObjectName("menuIgnoreWhitespace")
        self.menu_Edit = QtWidgets.QMenu(self.menubar)
        self.menu_Edit.setObjectName("menu_Edit")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.acQuit = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("application-exit")
        self.acQuit.setIcon(icon)
        self.acQuit.setObjectName("acQuit")
        self.acAbout = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("help-about")
        self.acAbout.setIcon(icon)
        self.acAbout.setObjectName("acAbout")
        self.acPreferences = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("preferences-system")
        self.acPreferences.setIcon(icon)
        self.acPreferences.setObjectName("acPreferences")
        self.actionIgnore_whitespace_changes = QtWidgets.QAction(MainWindow)
        self.actionIgnore_whitespace_changes.setObjectName("actionIgnore_whitespace_changes")
        self.acVisualizeWhitespace = QtWidgets.QAction(MainWindow)
        self.acVisualizeWhitespace.setCheckable(True)
        self.acVisualizeWhitespace.setObjectName("acVisualizeWhitespace")
        self.acIgnoreEOL = QtWidgets.QAction(MainWindow)
        self.acIgnoreEOL.setCheckable(True)
        self.acIgnoreEOL.setObjectName("acIgnoreEOL")
        self.acIgnoreAll = QtWidgets.QAction(MainWindow)
        self.acIgnoreAll.setCheckable(True)
        self.acIgnoreAll.setObjectName("acIgnoreAll")
        self.acIgnoreNone = QtWidgets.QAction(MainWindow)
        self.acIgnoreNone.setCheckable(True)
        self.acIgnoreNone.setObjectName("acIgnoreNone")
        self.acCopy = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("edit-copy")
        self.acCopy.setIcon(icon)
        self.acCopy.setObjectName("acCopy")
        self.acSelectAll = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("edit-select-all")
        self.acSelectAll.setIcon(icon)
        self.acSelectAll.setObjectName("acSelectAll")
        self.acFind = QtWidgets.QAction(MainWindow)
        icon = QtGui.QIcon.fromTheme("edit-find")
        self.acFind.setIcon(icon)
        self.acFind.setObjectName("acFind")
        self.acCompare = QtWidgets.QAction(MainWindow)
        self.acCompare.setCheckable(True)
        self.acCompare.setObjectName("acCompare")
        self.acShowGraph = QtWidgets.QAction(MainWindow)
        self.acShowGraph.setCheckable(True)
        self.acShowGraph.setChecked(True)
        self.acShowGraph.setObjectName("acShowGraph")
        self.acAboutQt = QtWidgets.QAction(MainWindow)
        self.acAboutQt.setObjectName("acAboutQt")
        self.menuFile.addAction(self.acQuit)
        self.menu_Help.addAction(self.acAbout)
        self.menu_Help.addAction(self.acAboutQt)
        self.menu_Settings.addAction(self.acPreferences)
        self.menuIgnoreWhitespace.addAction(self.acIgnoreNone)
        self.menuIgnoreWhitespace.addAction(self.acIgnoreEOL)
        self.menuIgnoreWhitespace.addAction(self.acIgnoreAll)
        self.menu_View.addAction(self.acVisualizeWhitespace)
        self.menu_View.addAction(self.menuIgnoreWhitespace.menuAction())
        self.menu_View.addSeparator()
        self.menu_View.addAction(self.acCompare)
        self.menu_Edit.addAction(self.acCopy)
        self.menu_Edit.addAction(self.acSelectAll)
        self.menu_Edit.addSeparator()
        self.menu_Edit.addAction(self.acFind)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menu_Edit.menuAction())
        self.menubar.addAction(self.menu_View.menuAction())
        self.menubar.addAction(self.menu_Settings.menuAction())
        self.menubar.addAction(self.menu_Help.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        MainWindow.setTabOrder(self.leRepo, self.btnRepoBrowse)
        MainWindow.setTabOrder(self.btnRepoBrowse, self.leOpts)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "gitc"))
        self.leOpts.setToolTip(_translate("MainWindow", "See the GIT-LOG options for more information."))
        self.leOpts.setPlaceholderText(_translate("MainWindow", "Type the log options here and press Enter to filter"))
        self.label_2.setText(_translate("MainWindow", "Filter:"))
        self.btnRepoBrowse.setText(_translate("MainWindow", "&Browse..."))
        self.label.setText(_translate("MainWindow", "Repository:"))
        self.lbSubmodule.setText(_translate("MainWindow", "Submodule:"))
        self.menuFile.setTitle(_translate("MainWindow", "&File"))
        self.menu_Help.setTitle(_translate("MainWindow", "&Help"))
        self.menu_Settings.setTitle(_translate("MainWindow", "&Settings"))
        self.menu_View.setTitle(_translate("MainWindow", "&View"))
        self.menuIgnoreWhitespace.setTitle(_translate("MainWindow", "&Ignore whitespace"))
        self.menu_Edit.setTitle(_translate("MainWindow", "&Edit"))
        self.acQuit.setText(_translate("MainWindow", "&Quit"))
        self.acQuit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.acAbout.setText(_translate("MainWindow", "&About gitc"))
        self.acPreferences.setText(_translate("MainWindow", "&Preferences..."))
        self.actionIgnore_whitespace_changes.setText(_translate("MainWindow", "Ignore whitespace changes"))
        self.acVisualizeWhitespace.setText(_translate("MainWindow", "&Visualize whitespace"))
        self.acIgnoreEOL.setText(_translate("MainWindow", "At &end of line"))
        self.acIgnoreAll.setText(_translate("MainWindow", "&All"))
        self.acIgnoreNone.setText(_translate("MainWindow", "&None"))
        self.acCopy.setText(_translate("MainWindow", "&Copy"))
        self.acCopy.setShortcut(_translate("MainWindow", "Ctrl+C"))
        self.acSelectAll.setText(_translate("MainWindow", "Select &All"))
        self.acSelectAll.setShortcut(_translate("MainWindow", "Ctrl+A"))
        self.acFind.setText(_translate("MainWindow", "&Find"))
        self.acFind.setShortcut(_translate("MainWindow", "Ctrl+F"))
        self.acCompare.setText(_translate("MainWindow", "&Compare Mode"))
        self.acShowGraph.setText(_translate("MainWindow", "Show &graph"))
        self.acAboutQt.setText(_translate("MainWindow", "About &Qt"))
from .gitview import GitView