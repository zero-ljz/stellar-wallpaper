"""Single-instance coordination for the desktop application."""

from __future__ import annotations

import hashlib
import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    """Prevents duplicate processes and forwards activation to the primary one."""

    activation_requested = Signal()

    def __init__(self, server_name: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # Unix domain sockets have a strict 104-byte sun_path limit on macOS.
        # Ensure the server name does not overflow when combined with the temp directory path.
        if sys.platform != "win32" and len(server_name) > 24:
            self._server_name = f"sw_{hashlib.sha256(server_name.encode()).hexdigest()[:16]}"
        else:
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
        if not self._notify_existing(timeout_ms=1000):
            # No process is responding to the existing socket; it is a stale socket from a previous crash.
            QLocalServer.removeServer(self._server_name)
            if self._server.listen(self._server_name):
                self.is_primary = True
                self._server.newConnection.connect(self._on_new_connection)

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
