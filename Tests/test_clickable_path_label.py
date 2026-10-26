import sys

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from exe_builder.ui.clickable_path_label import ClickablePathLabel


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_clickable_path_label_emits_only_for_a_valid_left_click(qt_app, tmp_path):
    path = tmp_path / "summary-path.txt"
    path.write_text("ok", encoding="utf-8")
    label = ClickablePathLabel()
    label.resize(200, 30)
    label.show()
    activated = []
    label.pathActivated.connect(activated.append)

    label.set_path(str(path))
    assert label.path() == str(path)
    assert label.cursor().shape() == Qt.PointingHandCursor
    QTest.mouseClick(label, Qt.LeftButton)
    assert activated == [str(path)]

    label.set_path(str(tmp_path / "missing.txt"))
    assert label.cursor().shape() == Qt.ArrowCursor
    QTest.mouseClick(label, Qt.LeftButton)
    assert activated == [str(path)]
    label.close()


def test_clickable_path_label_glows_while_a_valid_path_is_hovered(qt_app, tmp_path):
    path = tmp_path / "summary-path.txt"
    path.write_text("ok", encoding="utf-8")
    label = ClickablePathLabel()
    label.resize(200, 30)
    label.show()

    label.set_path(str(path))
    QApplication.sendEvent(label, QEvent(QEvent.Enter))
    assert label.graphicsEffect() is not None

    QApplication.sendEvent(label, QEvent(QEvent.Leave))
    assert label.graphicsEffect() is None
    label.close()
