import json
import stat

from PyQt6.QtNetwork import QLocalSocket
from PyQt6.QtTest import QTest

from linux_custom_dimmer.local_server import LocalServer


def connect(path):
    client = QLocalSocket()
    client.connectToServer(str(path))
    assert client.waitForConnected(500)
    QTest.qWait(20)
    return client


def exchange(path, data):
    client = connect(path)
    client.write(data)
    client.flush()
    QTest.qWait(30)
    return bytes(client.readAll())


def test_real_socket_accepts_one_valid_frame_and_rejects_bad_input(qt_app, tmp_path):
    calls = []
    path = tmp_path / "control.sock"
    server = LocalServer(path, lambda payload: calls.append(payload) or {"state": "Stopped"})
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        result = json.loads(exchange(path, b'{"action":"status"}\n'))
        assert result == {"ok": True, "status": {"state": "Stopped"}}
        for data in [b'{"action":[]}\n', b'{"action":"select","value":81}\n', b"{}\n{}\n"]:
            assert not json.loads(exchange(path, data))["ok"]
        assert exchange(path, b"x" * 600 + b"\n") == b""
        assert calls == [{"action": "status"}]
    finally:
        server.close()
    assert not path.exists()


def test_partial_client_expires_and_close_releases_clients(qt_app, tmp_path):
    path = tmp_path / "control.sock"
    server = LocalServer(path, lambda _: None)
    try:
        client = connect(path)
        client.write(b'{"action":')
        client.flush()
        QTest.qWait(1150)
        assert client.state() == QLocalSocket.LocalSocketState.UnconnectedState
        assert not server.clients
        client = connect(path)
        server.close()
        QTest.qWait(20)
        assert client.state() == QLocalSocket.LocalSocketState.UnconnectedState
    finally:
        server.close()
