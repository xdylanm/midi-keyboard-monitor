"""Firmware configuration and safe defaults.

Stored settings are intentionally small and can be extended later.
"""
DEFAULTS = {
    "device_name": "MK Monitor",
    "advertise": True,
    "channel_filter": [0],
    "sequence_timeout_ms": 4000,
    "max_ringbuf_bytes": 256,
    "max_tx_queue_events": 64,
}

CONFIG_FILE = "config.json"

def load(ujson, storage_open=None):
    try:
        with open(CONFIG_FILE, 'r') as f:
            return ujson.load(f)
    except Exception:
        return DEFAULTS.copy()

def save(cfg, ujson):
    try:
        with open(CONFIG_FILE, 'w') as f:
            ujson.dump(cfg, f)
            return True
    except Exception:
        return False
