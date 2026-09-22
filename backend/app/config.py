"""Runtime configuration.

Values are constants rather than environment variables: the demo runs
offline with no secrets and no per-environment configuration (NFR-D2,
NFR-D3).
"""

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

#: Seconds of silence before the stream emits an SSE comment, so an idle
#: connection is not closed during the quiet stretches of the narrative.
KEEPALIVE_INTERVAL = 15.0

#: Seconds between steps of the throwaway M1 workflow. The beat runner
#: replaces this with weighted beats in M2 (D-8).
DEMO_STEP_INTERVAL = 0.6
