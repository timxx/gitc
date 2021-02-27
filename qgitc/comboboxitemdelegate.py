# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QStyledItemDelegate, QComboBox
from PySide6.QtCore import Qt


class ComboBoxItemDelegate(QStyledItemDelegate):

    def __init__(self, items, parent=None):
        super(ComboBoxItemDelegate, self).__init__(parent)
        self._items = items

    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        for item in self._items:
            cb.addItem(item)
        return cb

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            idx = editor.findText(index.data())
            if idx >= 0:
                editor.setCurrentIndex(idx)
        else:
            super(ComboBoxItemDelegate, self).setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText(), Qt.EditRole)
        else:
            super(ComboBoxItemDelegate, self).setModelData(
                editor, model, index)
