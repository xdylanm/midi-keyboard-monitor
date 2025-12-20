"""
Minimal HTTP server with Server-Sent Events (SSE) endpoint for streaming MIDI events.

The scaffold exposes a `WebServer` class with `start()` and `broadcast(event_obj)`.
It serves static files from the `www/` directory next to this file and provides an
`/events` SSE endpoint which browsers can connect to via `EventSource`.

Note: This is intentionally lightweight and avoids full WebSocket complexity. If
uwebsockets is available on the target, this module can be extended to support WS.
"""
import uasyncio as asyncio
import ujson as json
import uos as os
import uhashlib as hashlib
import ubinascii as binascii

WWW_ROOT = "www"
WS_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class WebServer:
    def __init__(self, port=80):
        self.port = port
        self._ws_clients = []
        self._server = None

    async def start(self):
        loop = asyncio.get_event_loop()
        self._server = await asyncio.start_server(self._handle_client, "0.0.0.0", self.port)
        print('WebServer listening on port', self.port)

    async def _handle_client(self, reader, writer):
        print("New client connected")
        try:
            req = await reader.readline()
            if not req:
                await writer.aclose()
                return
            req_line = req.decode().strip()
            print(f'HTTP request: {req_line}')
            # simple parsing: GET /path HTTP/1.1
            parts = req_line.split()
            if len(parts) < 2:
                await writer.aclose()
                return
            method, path = parts[0], parts[1]

            # read headers into dict
            headers = {}
            while True:
                h = await reader.readline()
                if not h or h == b"\r\n":
                    break
                try:
                    line = h.decode().strip()
                    if ':' in line:
                        k, v = line.split(':', 1)
                        headers[k.strip().lower()] = v.strip()
                except Exception:
                    continue

            # no SSE endpoint; only websocket (/ws) and static files

            if path == "/ws":
                await self._handle_ws(reader, writer, headers)
                return

            if path == "/" or path == "":
                path = "/index.html"

            # serve static file
            filepath = WWW_ROOT + path

            # read file
            try: 
                with open(filepath, "rb") as f:
                    data = f.read()
                mime = self._guess_mime(path)
                await self._send_response(writer, b"200 OK", data, content_type=mime)
            except Exception:
                await self._send_response(writer, b"404 Not Found", b"Not found")
                return
            
        except Exception as e:
            try:
                print('Exception in _handle_client:', e)
            except Exception:
                pass
            try:
                await writer.aclose()
            except Exception:
                pass

    async def _handle_ws(self, reader, writer, headers):
        # Perform WebSocket handshake
        key = headers.get('sec-websocket-key')
        if not key:
            await writer.aclose()
            return
        accept = binascii.b2a_base64(hashlib.sha1(key.encode() + WS_GUID).digest()).strip().decode()
        resp = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            'Sec-WebSocket-Accept: ' + accept + '\r\n\r\n'
        )
        try:
            await writer.awrite(resp.encode())
        except Exception as e:
            try:
                print('WS handshake write error:', e)
            except Exception:
                pass
            try:
                await writer.aclose()
            except Exception:
                pass
            return

        # register ws client
        self._ws_clients.append(writer)
        try:
            print('WebSocket client connected (clients=', len(self._ws_clients), ')')
        except Exception:
            pass

        try:
            # keep connection alive; consume incoming frames minimally
            while True:
                await asyncio.sleep(60)
        finally:
            try:
                self._ws_clients.remove(writer)
            except Exception:
                pass
            try:
                await writer.aclose()
            except Exception:
                pass

    # SSE removed: server only supports WebSocket and static files

    async def _send_response(self, writer, status, data, content_type=b"text/plain"):
        try:
            hdr = b"HTTP/1.1 " + status + b"\r\nContent-Type: " + content_type + b"\r\nContent-Length: " + str(len(data)).encode() + b"\r\n\r\n"
            await writer.awrite(hdr)
            await writer.awrite(data)
        finally:
            try:
                await writer.aclose()
            except Exception:
                pass

    def _guess_mime(self, path):
        if path.endswith('.html'):
            return b'text/html'
        if path.endswith('.js'):
            return b'text/javascript'
        if path.endswith('.css'):
            return b'text/css'
        if path.endswith('.json'):
            return b'application/json'
        return b'application/octet-stream'

    def _send_ws_text(self, text):
        # build a single-frame unmasked text message
        payload = text.encode()
        l = len(payload)
        if l < 126:
            header = bytes([0x81, l])
        elif l < 65536:
            header = bytes([0x81, 126, (l >> 8) & 0xFF, l & 0xFF])
        else:
            # 64-bit length
            header = bytes([0x81, 127]) + b'\x00\x00\x00\x00' + bytes([
                (l >> 24) & 0xFF, (l >> 16) & 0xFF, (l >> 8) & 0xFF, l & 0xFF
            ])
        return header + payload

    async def _safe_write(self, writer, data):
        try:
            await writer.awrite(data)
        except Exception as e:
            try:
                print('Client write error:', e)
            except Exception:
                pass
            # remove writer from ws clients
            try:
                self._ws_clients.remove(writer)
            except Exception:
                pass
            try:
                await writer.aclose()
            except Exception:
                pass

    def broadcast(self, obj):
        # Convert to text and send to WS + SSE clients
        s = json.dumps(obj)
        try:
            print('Broadcasting event to', len(self._ws_clients), 'WS clients')
        except Exception:
            pass

        # WebSocket payload
        data = self._send_ws_text(s)
        for w in list(self._ws_clients):
            try:
                if data:
                    asyncio.create_task(self._safe_write(w, data))
            except Exception:
                try:
                    self._ws_clients.remove(w)
                except Exception:
                    pass
