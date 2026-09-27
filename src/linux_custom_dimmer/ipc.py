"""Small owner-only Unix socket protocol. No Qt import in the CLI client."""

import json
import socket

LIMIT = 512


def decode_request(raw):
    if len(raw) > LIMIT:
        raise ValueError("Request too large")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate key")
            result[key] = value
        return result

    try:
        request = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Invalid request") from error
    if not isinstance(request, dict):
        raise ValueError("Expected one action")
    action = request.get("action")
    if not isinstance(action, str):
        raise ValueError("Action must be a string")
    if action == "select":
        value = request.get("value")
        if set(request) != {"action", "value"} or type(value) is not int or not 0 <= value <= 80:
            raise ValueError("Opacity must be an integer from 0 to 80")
    elif action not in {"show", "start", "stop", "quit", "status"} or set(request) != {"action"}:
        raise ValueError("Unknown action")
    return request


def request(path, payload, timeout=1):
    data = json.dumps(payload).encode()
    decode_request(data)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout)
        connection.connect(str(path))
        connection.sendall(data + b"\n")
        response = b""
        while b"\n" not in response:
            chunk = connection.recv(1024)
            if not chunk or len(response) + len(chunk) > 8192:
                raise RuntimeError("Invalid application response")
            response += chunk
    result = json.loads(response)
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Application request failed"))
    return result
