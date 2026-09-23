"""The granted capability set, which PR-060 and PR-061 test against.

"Capability is enumerated, and the enumeration is the grant." This module
is that enumeration. A tool named here may be invoked; a tool not named
here is refused under PR-061 however reasonable the request, because
capability is not acquired at runtime.

The `tool_granted` fact on a request is therefore computed from this set
by the caller, never asserted: a workflow cannot grant itself a tool by
claiming it has one.
"""

GRANTED_TOOLS: frozenset[str] = frozenset(
    {
        # Runs a solution's unit, integration and validation suites
        # inside the analytical workspace.
        "test-runner",
    }
)


#: The tools that built Agent One VW. Closing the seeding phase retires
#: them (D-16): the component generator produced each pipeline, and the
#: test runner is the granted tool above. Neither is needed to run what
#: they built.
BUILD_TOOLS: tuple[str, ...] = ("component-generator", "test-runner")


def granted(tool: str) -> bool:
    return tool in GRANTED_TOOLS
