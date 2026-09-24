"""Life: Agent One VW collects and recalibrates (D-17, FR-LF4 to FR-LF11).

When the seeding phase closes, Agent One VW goes on maintaining what it
built. A deterministic clock advances a collection cursor through the
final twelve simulated weeks of each dataset, one week a step, and every
four steps it recalibrates: the baselines are recomputed over what has
been collected, and the findings re-scored. Then it is caught up.

Collection reveals records the generators already produced (FR-LF5), and
every recalibration was computed at startup (FR-AN3), so this workflow
only moves the cursor and reports, from the store's precomputed plan,
what arrived and what moved. The stream labels it as simulated.

The beats carry no narrative weight. Collection happens after the
270-second narrative and does not draw on its budget; each beat has a
floor instead, so at 1x a step lands a few seconds after the last.
Operator speed scales them, skip completes collection, and Reset clears
it (FR-LF10). The sequence is fixed, so two runs from Reset collect and
recalibrate identically (FR-LF11).
"""

import copy
from typing import Any

from app.analytics.generator import CALIBRATIONS, EVERY, STEPS, week_of
from app.analytics.store import STORE, Dataset
from app.domain.events import Category
from app.domain.state import SystemState
from app.simulation.beats import Beat, Workflow

#: Seconds between collection steps at 1x, and the extra pause a
#: recalibration takes. Tuned at M22.
STEP_SECONDS = 3.0
RECALIBRATION_SECONDS = 2.0

NUMBERS = dict(
    enumerate(
        (
            "no",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
        )
    )
)


def _names(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _dates(step: int) -> str:
    week = week_of(step)
    return f"{week['week']} ({week['from']} to {week['to']})"


def _sources(state: SystemState) -> list[Dataset]:
    """The datasets of the Agent Components that are live."""
    ready = {s["id"] for s in state.solutions if s["status"] in ("READY", "RUNNING")}
    return [
        d
        for d in STORE.datasets.values()
        if d.dashboard.collection and d.dashboard.solution_id in ready
    ]


def _snapshot(state: SystemState) -> dict[str, Any]:
    return copy.deepcopy(state.collection)


def life(state: SystemState) -> Workflow:
    datasets = _sources(state)
    state.collection = {
        "step": 0,
        "steps": STEPS,
        "every": EVERY,
        "calibration": 0,
        "calibrations": CALIBRATIONS - 1,
        "week": week_of(0)["week"],
        "caughtUp": False,
        "sources": [d.dashboard.solution_id for d in datasets],
    }
    if not datasets:
        state.collection["caughtUp"] = True
        state.record(
            type="life.caught_up",
            category=Category.SUCCESS,
            message="No Agent Component is live, so Agent One VW has nothing to collect.",
            payload={"collection": _snapshot(state)},
        )
        return

    state.record(
        type="life.collection.started",
        category=Category.ANALYSIS,
        message=(
            f"Agent One VW begins collecting: the final {NUMBERS[STEPS]} weeks from "
            f"{_names([d.dashboard.collection.source for d in datasets])}, one week at a time, "
            f"recalibrating every {NUMBERS[EVERY]} weeks. Simulated collection."
        ),
        payload={"collection": _snapshot(state)},
    )
    yield Beat(weight=0, floor=STEP_SECONDS, label="collection begins")

    for step in range(1, STEPS + 1):
        arrived = [
            {
                "solutionId": d.dashboard.solution_id,
                "source": d.dashboard.collection.source,
                "noun": d.dashboard.collection.noun,
                "count": d.arrivals[step],
            }
            for d in datasets
            if d.arrivals[step]
        ]
        state.collection.update(step=step, week=week_of(step)["week"])
        parts = [f"{a['count']:,} {a['noun']} from {a['source']}" for a in arrived]
        state.record(
            type="life.collection.step",
            category=Category.ANALYSIS,
            message=f"Collected {_names(parts)}, {_dates(step)}. Simulated collection.",
            payload={"collection": _snapshot(state), "arrived": arrived},
        )
        yield Beat(weight=0, floor=STEP_SECONDS, label=f"collected step {step}")

        if step % EVERY == 0:
            c = step // EVERY
            state.collection["calibration"] = c
            moves = []
            for d in datasets:
                move = d.recalibrations[c - 1]
                if move["baseline"] or move["confirmed"] or move["withdrawn"]:
                    moves.append({"solutionId": d.dashboard.solution_id, **move})
            state.record(
                type="life.recalibrated",
                category=Category.VALIDATION,
                message=_recalibration(c, step, moves),
                payload={"collection": _snapshot(state), "moves": moves},
            )
            yield Beat(weight=0, floor=RECALIBRATION_SECONDS, label=f"recalibration {c}")

    state.collection["caughtUp"] = True
    state.record(
        type="life.caught_up",
        category=Category.SUCCESS,
        message=(
            f"Agent One VW is caught up: {NUMBERS[STEPS]} weeks collected, recalibrated "
            f"{NUMBERS[CALIBRATIONS - 1]} times. Every figure is now the full dataset's."
        ),
        payload={"collection": _snapshot(state)},
    )


def _recalibration(c: int, step: int, moves: list[dict[str, Any]]) -> str:
    """What a recalibration moved, in a sentence or two (FR-LF6)."""
    week = week_of(step)["week"]
    parts: list[str] = []
    confirmed: list[str] = []
    withdrawn: list[str] = []
    for move in moves:
        baseline = move["baseline"]
        if baseline:
            parts.append(
                f"{baseline['finding']} baseline for {baseline['metric'].lower()} moved from "
                f"{baseline['from']:,} to {baseline['to']:,}"
            )
        confirmed += move["confirmed"]
        withdrawn += move["withdrawn"]
    message = f"Recalibration {c}, {week}: baselines recomputed over what has been collected."
    if parts:
        message += " " + "; ".join(parts) + "."
    if confirmed:
        message += f" {_names(confirmed)} confirmed."
    if withdrawn:
        message += f" {_names(withdrawn)} withdrawn."
    if not (parts or confirmed or withdrawn):
        message += " Nothing moved."
    return message
