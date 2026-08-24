"""Single-instance coordination for the desktop application."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    """Prevents duplicate processes and forwards activation to the primary one."""

    activation_requested = Signal()

    def __init__(self, server_name: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server_name = server_name
        self._server = QLocalServer(self)
        self._pending_activation = False
        self.is_primary = False

        if self._notify_existing(timeout_ms=200):
            return

        if self._server.listen(self._server_name):
            self.is_primary = True
            self._server.newConnection.connect(self._on_new_connection)
            return

        # Another process may have started listening between the first probe and listen().
        self._notify_existing(timeout_ms=1000)

    def _notify_existing(self, timeout_ms: int) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._server_name)
        if not socket.waitForConnected(timeout_ms):
            return False

        socket.write(b"activate")
        socket.waitForBytesWritten(timeout_ms)
        socket.disconnectFromServer()
        return True

    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is not None:
                socket.disconnectFromServer()
                socket.deleteLater()
        self._pending_activation = True
        self.activation_requested.emit()

    def take_pending_activation(self) -> bool:
        pending = self._pending_activation
        self._pending_activation = False
        return pending

    def close(self) -> None:
        if self.is_primary:
            self._server.close()
