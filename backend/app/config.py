"""Runtime configuration.

Values are constants rather than environment variables: the demo runs
offline with no secrets and no per-environment configuration (NFR-D2,
NFR-D3).
"""

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

#: Seconds between heartbeat events on the M0 stream. The real beat
#: runner replaces this in M2.
HEARTBEAT_INTERVAL = 2.0
