# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import *
import sys


is_mac = (sys.platform == "darwin")


def defaultDpiX():
    screen = qApp.primaryScreen()
    if screen:
        return round(screen.logicalDotsPerInchX())

    return 96.0


def defaultDpiY():
    screen = qApp.primaryScreen()
    if screen:
        return round(screen.logicalDotsPerInchY())

    return 96.0


def dpiScaled(value):
    if isinstance(value, int) or isinstance(value, float):
        # from Qt, on mac the DPI is always 72
        if is_mac:
            return value
        return value * defaultDpiX() / 96.0
    elif isinstance(value, QSize):
        w = dpiScaled(value.width())
        h = dpiScaled(value.height())
        return QSize(w, h)
    elif isinstance(value, QSizeF):
        w = dpiScaled(value.width())
        h = dpiScaled(value.height())
        return QSizeF(w, h)
    elif isinstance(value, QPoint):
        x = dpiScaled(value.x())
        y = dpiScaled(value.y())
        return QPoint(x, y)
    elif isinstance(value, QPointF):
        x = dpiScaled(value.x())
        y = dpiScaled(value.y())
        return QPointF(x, y)
    elif isinstance(value, QMargins):
        l = dpiScaled(value.left())
        t = dpiScaled(value.top())
        r = dpiScaled(value.right())
        b = dpiScaled(value.bottom())
        return QMargins(l, t, r, b)
    elif isinstance(value, QMarginsF):
        l = dpiScaled(value.left())
        t = dpiScaled(value.top())
        r = dpiScaled(value.right())
        b = dpiScaled(value.bottom())
        return QMarginsF(l, t, r, b)
    elif isinstance(value, QRect):
        l = dpiScaled(value.left())
        t = dpiScaled(value.top())
        r = dpiScaled(value.right())
        b = dpiScaled(value.bottom())
        return QRect(l, t, r, b)
    elif isinstance(value, QRectF):
        l = dpiScaled(value.left())
        t = dpiScaled(value.top())
        r = dpiScaled(value.right())
        b = dpiScaled(value.bottom())
        return QRectF(l, t, r, b)
    elif isinstance(value, tuple):
        return dpiScaled(value[0]), dpiScaled(value[1])
    else:
        print("Unspported type")
        return value
