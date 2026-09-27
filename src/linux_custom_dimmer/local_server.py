"""Qt side of the bounded local protocol."""

import json
import os
import stat

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtNetwork import QLocalServer

from .ipc import LIMIT, decode_request


class LocalServer(QObject):
    def __init__(self, path, dispatch):
        super().__init__()
        self.path = path
        self.dispatch = dispatch
        self.clients = set()
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if path.exists():
            info = path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise RuntimeError("Refusing unexpected control socket path")
            # App verifies it is the new owned service MainPID before getting here.
            QLocalServer.removeServer(str(path))
        if not self.server.listen(str(path)):
            raise RuntimeError(
                f"Could not create local control socket: {self.server.errorString()}"
            )
        os.chmod(path, 0o600)
        self.server.newConnection.connect(self.accept)

    def accept(self):
        while self.server.hasPendingConnections():
            client = self.server.nextPendingConnection()
            if len(self.clients) >= 8:
                client.abort()
                client.deleteLater()
                continue
            self.clients.add(client)
            client.setReadBufferSize(LIMIT + 1)
            timer = QTimer(client)
            timer.setSingleShot(True)
            timer.timeout.connect(client.abort)
            timer.start(1000)
            client.readyRead.connect(lambda c=client: self.read(c))
            client.disconnected.connect(lambda c=client: self.release(c))

    def read(self, client):
        if client.bytesAvailable() > LIMIT:
            client.abort()
            return
        if not client.canReadLine():
            return
        raw = bytes(client.readAll())
        try:
            result = self.dispatch(decode_request(raw))
            response = {"ok": True, "status": result}
        except (ValueError, RuntimeError, OSError) as error:
            response = {"ok": False, "error": str(error)}
        client.write(json.dumps(response).encode() + b"\n")
        client.disconnectFromServer()

    def release(self, client):
        self.clients.discard(client)
        client.deleteLater()

    def close(self):
        for client in tuple(self.clients):
            client.abort()
        self.server.close()
