import json

import pytest

from linux_custom_dimmer.ipc import decode_request


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "show"},
        {"action": "stop"},
        {"action": "start"},
        {"action": "status"},
        {"action": "quit"},
        {"action": "select", "value": 80},
    ],
)
def test_fixed_protocol_accepts_only_known_requests(payload):
    assert decode_request(json.dumps(payload).encode()) == payload


@pytest.mark.parametrize(
    "raw",
    [
        b'{"action":"exec","command":"whoami"}',
        b'{"action":"kill","pid":1}',
        b'{"action":"start","value":50}',
        b'{"action":"select","value":81}',
        b'{"action":"select","value":NaN}',
        b'{"action":"select","value":true}',
        b'{"action":"select","value":"50"}',
        b'{"action":"select","value":50.0}',
        b'{"action":"stop","action":"start"}',
        b'{"action":[]}',
        b'{"action":{}}',
        b"[]",
        b"null",
        b'"stop"',
        b"bad",
        b"x" * 1025,
    ],
)
def test_invalid_protocol_never_dispatches(raw):
    with pytest.raises(ValueError):
        decode_request(raw)
