"""Every dashboard, with the generator that feeds it.

A methodology's analytics is an entry here: a descriptor and a generator
(FR-EV4). Nothing else in the query engine, the API or the renderer names
a methodology.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.analytics.descriptors.applications import APPLICATIONS
from app.analytics.descriptors.licenses import LICENSES
from app.analytics.descriptors.tickets import TICKETS
from app.analytics.generator import applications, licenses, tickets
from app.analytics.schema import Dashboard


@dataclass(frozen=True)
class Source:
    dashboard: Dashboard
    #: Returns the primary frame and any secondary frames, by frame id.
    generate: Callable[[], dict[str, pd.DataFrame]]
    #: Life's recalibrations (D-17): for each calibration, the columns that
    #: differ from the generated frames, by frame. None if nothing
    #: recalibrates.
    calibrate: (
        Callable[[dict[str, pd.DataFrame]], list[dict[str, dict[str, np.ndarray]]]] | None
    ) = None


def _pair(primary_and_secondary: Callable[[], tuple[pd.DataFrame, pd.DataFrame]], frame: str):
    def generate() -> dict[str, pd.DataFrame]:
        primary, secondary = primary_and_secondary()
        return {"primary": primary, frame: secondary}

    return generate


SOURCES: tuple[Source, ...] = (
    Source(TICKETS, lambda: {"primary": tickets.generate()}, tickets.calibrate),
    Source(LICENSES, _pair(licenses.generate, "activity")),
    Source(APPLICATIONS, _pair(applications.generate, "usage"), applications.calibrate),
)
