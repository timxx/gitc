# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QStyle,
    QMessageBox)

from .gitutils import Git
from .excepthandler import ExceptHandler
from .application import Application
from .mainwindow import MainWindow
from .shell import setup_shell_args
from .common import isXfce4

import os
import sys
import argparse
import shutil
import subprocess


def setAppUserId(appId):
    if os.name != "nt":
        return

    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appId)
    except:
        pass


def unsetEnv(varnames):
    if hasattr(os, "unsetenv"):
        for var in varnames:
            os.unsetenv(var)
    else:
        for var in varnames:
            try:
                del os.environ[var]
            except KeyError:
                pass


def _setup_argument(prog):
    parser = argparse.ArgumentParser(
        usage=prog + " [-h] <command> [<args>]")
    subparsers = parser.add_subparsers(
        title="The <command> list",
        dest="cmd", metavar="")
    parser.set_defaults(func=_do_log)

    log_parser = subparsers.add_parser(
        "log",
        help="Show commit logs")
    log_parser.add_argument(
        "-c", "--compare-mode", action="store_true",
        help="Compare mode, show two branches for comparing")
    log_parser.add_argument(
        "file", metavar="<file>", nargs="?",
        help="The file to filter.")
    log_parser.set_defaults(func=_do_log)

    mergetool_parser = subparsers.add_parser(
        "mergetool",
        help="Run mergetool to resolve merge conflicts.")
    log_parser.set_defaults(func=_do_log)

    blame_parser = subparsers.add_parser(
        "blame",
        help="Show what revision and author last modified each line of a file.")
    blame_parser.add_argument(
        "--line-number", "-l",
        metavar="N", type=int,
        default=0,
        help="Goto the specify line number when opening a file.")
    blame_parser.add_argument(
        "--rev", "-r",
        metavar="<rev>",
        help="Blame with <rev>.")
    blame_parser.add_argument(
        "file", metavar="<file>",
        help="The file to blame.")
    blame_parser.set_defaults(func=_do_blame)

    setup_shell_args(subparsers)

    return parser.parse_args()


def _move_center(window):
    window.setGeometry(QStyle.alignedRect(
        Qt.LeftToRight, Qt.AlignCenter,
        window.size(),
        qApp.primaryScreen().availableGeometry()))


def _init_gui():
    setAppUserId("appid.qgitc.xyz")
    app = Application(sys.argv)

    sys.excepthook = ExceptHandler

    return app


def _do_log(args):
    app = _init_gui()

    merge_mode = args.cmd == "mergetool"
    window = app.getWindow(Application.LogWindow)
    if merge_mode:
        window.setMode(MainWindow.MergeMode)
    _move_center(window)

    if args.cmd == "log":
        # merge mode will also change to compare view
        if args.compare_mode:
            window.setMode(MainWindow.CompareMode)

        if args.file:
            filterFile = args.file
            if not os.path.isabs(filterFile):
                filterFile = os.path.abspath(filterFile)

            if Git.REPO_DIR:
                normPath = os.path.normcase(os.path.normpath(filterFile))
                repoDir = os.path.normcase(os.path.normpath(Git.REPO_DIR))
                if normPath.find(repoDir) != -1:
                    filterFile = filterFile[len(repoDir) + 1:]

            window.setFilterFile(filterFile)

    if window.restoreState():
        window.show()
    else:
        window.showMaximized()

    return app.exec_()


def _do_blame(args):
    app = _init_gui()

    window = app.getWindow(Application.BlameWindow)
    _move_center(window)

    if window.restoreState():
        window.show()
    else:
        window.showMaximized()

    window.blame(args.file, args.rev, args.line_number)

    return app.exec_()


def _update_scale_factor():
    if sys.platform != "linux":
        return

    # only xfce4 for the moment
    if not isXfce4():
        return

    xfconf_query = shutil.which("xfconf-query")
    if not xfconf_query:
        return

    def _query_conf(name):
        v = subprocess.check_output(
            [xfconf_query, "-c", "xsettings", "-p", name],
            universal_newlines=True)
        if v:
            v = v.rstrip('\n')
        return v

    try:
        if _query_conf("/Gdk/WindowScalingFactor") == "2" and \
                _query_conf("/Xft/DPI") == "96":
            os.environ["QT_SCALE_FACTOR"] = "2"
    except subprocess.CalledProcessError:
        pass


def main():
    unsetEnv(["QT_SCALE_FACTOR", "QT_AUTO_SCREEN_SCALE_FACTOR"])
    _update_scale_factor()

    args = _setup_argument(os.path.basename(sys.argv[0]))
    return args.func(args)


if __name__ == "__main__":
    main()
