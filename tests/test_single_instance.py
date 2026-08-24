"""Tests for single-instance process coordination."""

import sys
from uuid import uuid4

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.core.single_instance import SingleInstance


def get_qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication(sys.argv)


def test_second_instance_requests_primary_activation() -> None:
    app = get_qapp()
    server_name = f"stellar-wallpaper-test-{uuid4()}"
    primary = SingleInstance(server_name)
    activations: list[bool] = []
    primary.activation_requested.connect(lambda: activations.append(True))

    secondary = SingleInstance(server_name)
    QTest.qWait(50)
    app.processEvents()

    assert primary.is_primary
    assert not secondary.is_primary
    assert activations == [True]

    secondary.close()
    primary.close()
