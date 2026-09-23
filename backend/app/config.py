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

#: Target length of the whole narrative at 1x, in seconds. The single
#: number that retimes everything (D-8), set for the four-to-five minute
#: target of OQ-7. M13 calibrates it against a rehearsal.
TOTAL_DURATION_SECONDS = 270.0

#: The sum of every beat weight in the narrative. Declared rather than
#: derived, because generators are lazy and cannot be measured without
#: being run. The calibration test asserts that a full run consumes
#: exactly this, so drift shows up as a test failure.
#:
#: Shares since M18: discovery 54, assessment 25, implementation 20,
#: closing 6. Closing's six units are about 15 seconds at 1x, D-16's
#: allowance; the total duration is unchanged, so the rest runs slightly
#: faster until M22 recalibrates. It
#: describes the scripted narrative, in which every solution is approved
#: (§83.6); a run that approves fewer is shorter by the builds it skips.
#: Time a person spends deciding is not narrative time and is not in it.
NARRATIVE_WEIGHT = 105.0
