"""Small IRQ-friendly ring buffer for bytes.

Simple implementation used by UART ingest code. Not heavily optimized.
"""
class RingBuf:
    def __init__(self, size=256):
        self._size = size
        self._buf = bytearray(size)
        self._head = 0
        self._tail = 0

    def put(self, b):
        nxt = (self._head + 1) % self._size
        if nxt == self._tail:
            # full
            return False
        self._buf[self._head] = b
        self._head = nxt
        return True

    def get(self):
        if self._head == self._tail:
            return None
        v = self._buf[self._tail]
        self._tail = (self._tail + 1) % self._size
        return v

    def available(self):
        if self._head >= self._tail:
            return self._head - self._tail
        return self._size - (self._tail - self._head)

    def clear(self):
        self._head = self._tail = 0
