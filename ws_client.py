"""WebSocket client باستخدام socket مباشرة — بدون مكتبات خارجية."""

import socket
import hashlib
import base64
import struct
import os
import threading


def _handshake_key():
    return base64.b64encode(os.urandom(16)).decode()


class SimpleWS:
    def __init__(self):
        self._sock   = None
        self._lock   = threading.Lock()
        self.connected = False

    def connect(self, url: str, timeout: float = 10):
        # url مثل: ws://localhost:9223/devtools/page/XXX
        url = url.replace("ws://", "")
        host_port, path = url.split("/", 1)
        path = "/" + path
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host, port = host_port, 80

        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._sock.settimeout(timeout)

        key = _handshake_key()
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        self._sock.sendall(req.encode())

        # قراءة الرد HTTP
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self._sock.recv(1024)

        if b"101" not in resp:
            raise ConnectionError(f"WebSocket handshake failed: {resp[:200]}")

        self._sock.settimeout(None)
        self.connected = True

    def send(self, data: str):
        payload = data.encode("utf-8")
        n = len(payload)
        mask = os.urandom(4)

        if n <= 125:
            header = bytes([0x81, 0x80 | n])
        elif n <= 65535:
            header = bytes([0x81, 0xFE]) + struct.pack(">H", n)
        else:
            header = bytes([0x81, 0xFF]) + struct.pack(">Q", n)

        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        frame  = header + mask + masked

        with self._lock:
            self._sock.sendall(frame)

    def recv(self) -> str:
        def _read(n):
            buf = b""
            while len(buf) < n:
                chunk = self._sock.recv(n - len(buf))
                if not chunk:
                    raise ConnectionResetError("WebSocket closed")
                buf += chunk
            return buf

        b0, b1 = _read(2)
        opcode = b0 & 0x0F
        masked = (b1 & 0x80) != 0
        length = b1 & 0x7F

        if opcode == 8:  # close
            raise ConnectionResetError("WebSocket close frame")

        if length == 126:
            length = struct.unpack(">H", _read(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", _read(8))[0]

        mask_key = _read(4) if masked else None
        payload  = _read(length)

        if mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

        return payload.decode("utf-8", errors="replace")

    def close(self):
        self.connected = False
        try:
            if self._sock:
                self._sock.close()
        except Exception:
            pass
