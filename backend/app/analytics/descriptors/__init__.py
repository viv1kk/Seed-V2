"""Every dashboard, with the generator that feeds it.

A methodology's analytics is an entry here: a descriptor and a generator
(FR-EV4). Nothing else in the query engine, the API or the renderer names
a methodology.
"""

from collections.abc import Callable
from dataclasses import dataclass

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


def _pair(primary_and_secondary: Callable[[], tuple[pd.DataFrame, pd.DataFrame]], frame: str):
    def generate() -> dict[str, pd.DataFrame]:
        primary, secondary = primary_and_secondary()
        return {"primary": primary, frame: secondary}

    return generate


SOURCES: tuple[Source, ...] = (
    Source(TICKETS, lambda: {"primary": tickets.generate()}),
    Source(LICENSES, _pair(licenses.generate, "activity")),
    Source(APPLICATIONS, _pair(applications.generate, "usage")),
)
