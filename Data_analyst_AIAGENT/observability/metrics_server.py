"""Optional background HTTP server exposing Prometheus `/metrics` -- off by
default (`ENABLE_METRICS_SERVER=false`) so it's HF Spaces-safe (a Space only
exposes the Streamlit app's own port). The Observability tab always reads
`REGISTRY` in-process regardless of whether this server is running; this is
only for a local Prometheus scraper to pull from.
"""

import threading
from wsgiref.simple_server import make_server

from prometheus_client import make_wsgi_app

from config.settings import ENABLE_METRICS_SERVER, METRICS_SERVER_PORT
from observability.metrics import REGISTRY

_started = False
_lock = threading.Lock()


def start_metrics_server_once() -> None:
    global _started
    if not ENABLE_METRICS_SERVER:
        return
    with _lock:
        if _started:
            return
        server = make_server("0.0.0.0", METRICS_SERVER_PORT, make_wsgi_app(REGISTRY))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _started = True
